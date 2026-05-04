from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from pydantic import BaseModel, Field

from llmw.core.fs import ensure_parent, utc_now_iso
from llmw.core.markdown import extract_title, split_frontmatter
from llmw.core.paths import WikiPaths
from llmw.health.checks import HealthChecker
from llmw.llm.client import OpenAICompatibleClient
from llmw.llm.config import ProviderConfig, load_system_prompt
from llmw.sources.ingest import build_ingest_packet
from llmw.sources.registry import get_source, update_source
from llmw.wiki.identity import canonical_page_key, wiki_slugify
from llmw.wiki.index import rebuild_index
from llmw.wiki.log import append_log
from llmw.wiki.pages import WikiPage, load_pages


class GeneratedPage(BaseModel):
    path: str
    content: str


class IngestGeneration(BaseModel):
    pages: list[GeneratedPage] = Field(default_factory=list)
    log_note: str = ""


@dataclass(frozen=True)
class IngestRunResult:
    source_id: str
    pages: list[str]
    log_note: str
    health_errors: int
    health_warnings: int
    dry_run: bool = False


ClientFactory = Callable[[ProviderConfig], OpenAICompatibleClient]


def build_ingest_prompt(paths: WikiPaths, source_id: str, *, max_chars: int = 12000) -> str:
    packet = build_ingest_packet(paths, source_id, max_chars=max_chars)
    index = paths.index_path.read_text(encoding="utf-8", errors="replace") if paths.index_path.exists() else "# Index\n\n"
    source = get_source(paths, source_id)
    source_page = f"wiki/sources/{source.source_id}.md"
    return f"""Return JSON only. Do not wrap it in Markdown fences.

Schema:
{{
  "pages": [
    {{"path": "wiki/sources/example.md", "content": "---\\ntitle: Example\\ntype: source\\nstatus: draft\\nsources: [\\"source_id\\"]\\ntags: []\\n---\\n\\n# Example\\n..."}}
  ],
  "log_note": "Short note for wiki/log.md"
}}

Rules:
- Generate complete Markdown file content for every page you create or update.
- Always include `{source_page}` as one of the pages.
- Page paths must stay under `wiki/` and end in `.md`.
- Use YAML frontmatter with at least: title, type, status, sources, tags.
- Prefer the source language for page titles and concept names. For Chinese
  sources, use Chinese titles unless an established existing wiki page already
  uses an English term.
- Prefer updating existing pages from the current index when a generated page
  describes the same concept, even if capitalization, spaces, hyphens, or
  underscores differ.
- Use Obsidian links such as [[Concept Name]] for relationships.
- Only use `[[wiki links]]` for pages that exist in the current index or that
  you are returning in this JSON. Use plain text for generic phrases such as
  source page, concept page, index, and log.
- Do not attach plural suffixes to links, such as `[[source page]]s`.
- Do not modify files outside `wiki/`.
- Keep unsupported uncertainty explicit; do not invent facts.

Current wiki index:
```markdown
{index}
```

Ingest packet:
```markdown
{packet}
```
"""


def run_ingest(
    paths: WikiPaths,
    source_id: str,
    *,
    provider: ProviderConfig,
    dry_run: bool = False,
    max_chars: int = 12000,
    client_factory: ClientFactory = OpenAICompatibleClient,
) -> IngestRunResult:
    usage = provider.usage.get("ingest")
    if usage is None:
        raise KeyError("Provider config does not define usage.ingest")
    system_prompt = load_system_prompt(paths, usage)
    prompt = build_ingest_prompt(paths, source_id, max_chars=max_chars)
    client = client_factory(provider)
    response = client.chat(
        system_prompt=system_prompt,
        user_prompt=prompt,
        temperature=usage.temperature,
        top_p=usage.top_p,
        max_tokens=usage.max_tokens,
    )
    generation = parse_ingest_generation_with_repair(
        paths,
        source_id,
        response.content,
        client=client,
        system_prompt=system_prompt,
        temperature=usage.temperature,
        top_p=usage.top_p,
        max_tokens=usage.max_tokens,
    )
    generation = normalize_generated_pages(paths, generation, source_id=source_id)
    generation = sanitize_generated_links(paths, generation)
    validate_generated_pages(paths, generation.pages, source_id=source_id)
    page_paths = [page.path for page in generation.pages]

    if not dry_run:
        for page in generation.pages:
            destination = paths.root / page.path
            ensure_parent(destination)
            destination.write_text(page.content.rstrip() + "\n", encoding="utf-8")

        record = get_source(paths, source_id)
        record.status = "ingested"
        record.pages = page_paths
        update_source(paths, record)
        append_log(paths, "Ingest", record.title, generation.log_note or f"Auto-ingested `{source_id}` with LLM provider.")
        rebuild_index(paths)

    issues = HealthChecker(paths).run() if not dry_run else []
    errors = sum(1 for issue in issues if issue.severity == "error")
    warnings = sum(1 for issue in issues if issue.severity == "warning")
    return IngestRunResult(
        source_id=source_id,
        pages=page_paths,
        log_note=generation.log_note,
        health_errors=errors,
        health_warnings=warnings,
        dry_run=dry_run,
    )


def parse_ingest_generation(content: str) -> IngestGeneration:
    raw = _extract_json(content)
    data = json.loads(raw)
    return IngestGeneration.model_validate(data)


def parse_ingest_generation_with_repair(
    paths: WikiPaths,
    source_id: str,
    content: str,
    *,
    client: OpenAICompatibleClient,
    system_prompt: str,
    temperature: float | None,
    top_p: float | None,
    max_tokens: int | None,
) -> IngestGeneration:
    try:
        return parse_ingest_generation(content)
    except Exception as first_error:
        repair_prompt = _build_json_repair_prompt(content, first_error)
        repaired_content = ""
        try:
            repaired = client.chat(
                system_prompt=system_prompt,
                user_prompt=repair_prompt,
                temperature=0.0,
                top_p=top_p,
                max_tokens=max_tokens,
            )
            repaired_content = repaired.content
            return parse_ingest_generation(repaired.content)
        except Exception as repair_error:
            artifact = _write_ingest_error_artifact(
                paths,
                source_id,
                content,
                first_error,
                repair_error,
                repaired_content=repaired_content,
            )
            raise ValueError(
                "Failed to parse ingest LLM JSON for "
                f"{source_id}: {first_error}; repair also failed: {repair_error}. "
                f"Raw response saved to {artifact}"
            ) from repair_error


def normalize_generated_pages(paths: WikiPaths, generation: IngestGeneration, *, source_id: str) -> IngestGeneration:
    existing = _existing_page_targets(paths)
    normalized: list[GeneratedPage] = []
    used_targets: dict[str, str] = {}
    source_page = f"wiki/sources/{source_id}.md"

    for page in generation.pages:
        metadata, body = read_markdown_content(page.content)
        title = extract_title(Path(page.path), body, metadata)
        target_path = _normalized_generated_path(paths, page.path, title, metadata, existing, source_page)
        target_key = canonical_page_key(Path(target_path).with_suffix("").as_posix())
        previous = used_targets.get(target_key)
        if previous and previous != target_path:
            raise ValueError(f"Duplicate canonical generated page target: {previous} and {target_path}")
        used_targets[target_key] = target_path
        normalized.append(GeneratedPage(path=target_path, content=page.content))

    return IngestGeneration(pages=normalized, log_note=generation.log_note)


def validate_generated_pages(paths: WikiPaths, pages: list[GeneratedPage], *, source_id: str | None = None) -> None:
    if not pages:
        raise ValueError("LLM did not return any pages")
    seen_paths: set[str] = set()
    seen_canonical_paths: dict[str, str] = {}
    required_source_page = f"wiki/sources/{source_id}.md" if source_id else None
    root = paths.root.resolve()
    wiki_root = paths.wiki.resolve()
    for page in pages:
        rel = Path(page.path)
        normalized = rel.as_posix()
        if normalized in seen_paths:
            raise ValueError(f"Duplicate generated page path: {page.path}")
        seen_paths.add(normalized)
        canonical_path = canonical_page_key(Path(normalized).with_suffix("").as_posix())
        previous = seen_canonical_paths.get(canonical_path)
        if previous and previous != normalized:
            raise ValueError(f"Duplicate canonical generated page path: {previous} and {page.path}")
        seen_canonical_paths[canonical_path] = normalized
        if rel.is_absolute():
            raise ValueError(f"Generated path must be relative: {page.path}")
        destination = (paths.root / rel).resolve()
        if not destination.is_relative_to(wiki_root):
            raise ValueError(f"Generated path must stay under wiki/: {page.path}")
        if destination.suffix.lower() != ".md":
            raise ValueError(f"Generated path must end in .md: {page.path}")
        if root not in destination.parents and destination != root:
            raise ValueError(f"Generated path escaped project root: {page.path}")
        metadata, _ = read_markdown_content(page.content)
        if metadata.get("_frontmatter_error"):
            raise ValueError(f"Generated page has invalid frontmatter: {page.path}")
        missing = [key for key in ["title", "type", "status", "sources", "tags"] if key not in metadata]
        if missing:
            raise ValueError(f"Generated page missing frontmatter keys in {page.path}: {', '.join(missing)}")
    if required_source_page and required_source_page not in seen_paths:
        raise ValueError(f"Generated pages must include source page: {required_source_page}")


def sanitize_generated_links(paths: WikiPaths, generation: IngestGeneration) -> IngestGeneration:
    allowed = _allowed_link_targets(paths, generation.pages)
    sanitized_pages = [
        GeneratedPage(path=page.path, content=_delink_unresolved(page.content, allowed))
        for page in generation.pages
    ]
    return IngestGeneration(pages=sanitized_pages, log_note=generation.log_note)


def _allowed_link_targets(paths: WikiPaths, pages: list[GeneratedPage]) -> set[str]:
    targets: set[str] = set()
    for page in load_pages(paths, include_special=True):
        targets.add(page.title)
        targets.add(page.path.stem)
        targets.add(canonical_page_key(page.title))
        targets.add(canonical_page_key(page.path.stem))
    for page in pages:
        path = Path(page.path)
        metadata, body = read_markdown_content(page.content)
        title = extract_title(path, body, metadata)
        targets.add(title)
        targets.add(path.stem)
        targets.add(canonical_page_key(title))
        targets.add(canonical_page_key(path.stem))
    return {target for target in targets if target}


def read_markdown_content(content: str) -> tuple[dict, str]:
    return split_frontmatter(content)


def _delink_unresolved(content: str, allowed: set[str]) -> str:
    pattern = re.compile(r"(?<!!)\[\[([^\]\n]+)\]\]")

    def replace(match: re.Match[str]) -> str:
        raw = match.group(1)
        target = raw.split("|", 1)[0].split("#", 1)[0].strip()
        label = raw.split("|", 1)[1].strip() if "|" in raw else target
        return match.group(0) if target in allowed or canonical_page_key(target) in allowed else label

    return pattern.sub(replace, content)


def _existing_page_targets(paths: WikiPaths) -> dict[tuple[str, str], WikiPage]:
    targets: dict[tuple[str, str], WikiPage] = {}
    for page in load_pages(paths, include_special=False):
        for value in [page.title, page.path.stem]:
            key = canonical_page_key(value)
            if key:
                targets.setdefault((page.page_type, key), page)
    return targets


def _normalized_generated_path(
    paths: WikiPaths,
    page_path: str,
    title: str,
    metadata: dict,
    existing: dict[tuple[str, str], WikiPage],
    source_page: str,
) -> str:
    normalized = Path(page_path).as_posix()
    page_type = str(metadata.get("type") or "").strip()
    if normalized == source_page or page_type == "source":
        return source_page

    for value in [title, Path(page_path).stem]:
        key = canonical_page_key(value)
        if key and (page_type, key) in existing:
            return existing[(page_type, key)].rel_path

    parent = _directory_for_page_type(paths, page_type, page_path)
    slug = wiki_slugify(title or Path(page_path).stem)
    return (parent / f"{slug}.md").relative_to(paths.root).as_posix()


def _directory_for_page_type(paths: WikiPaths, page_type: str, page_path: str) -> Path:
    page_type_dirs = {
        "source": paths.wiki_sources,
        "entity": paths.wiki_entities,
        "concept": paths.wiki_concepts,
        "analysis": paths.wiki_analyses,
        "output": paths.wiki_outputs,
    }
    if page_type in page_type_dirs:
        return page_type_dirs[page_type]

    destination = paths.root / page_path
    try:
        destination.resolve().relative_to(paths.wiki.resolve())
    except ValueError:
        return paths.wiki
    return destination.parent


def _build_json_repair_prompt(content: str, error: Exception) -> str:
    return f"""The previous ingest response could not be parsed as valid JSON.

Return only a valid JSON object matching this schema, with no Markdown fences,
comments, or explanation:
{{
  "pages": [
    {{"path": "wiki/sources/example.md", "content": "---\\ntitle: Example\\ntype: source\\nstatus: draft\\nsources: [\\"source_id\\"]\\ntags: []\\n---\\n\\n# Example\\n..."}}
  ],
  "log_note": "Short note for wiki/log.md"
}}

Parse error:
{error}

Previous response:
```text
{content}
```
"""


def _write_ingest_error_artifact(
    paths: WikiPaths,
    source_id: str,
    content: str,
    first_error: Exception,
    repair_error: Exception,
    repaired_content: str = "",
) -> str:
    timestamp = utc_now_iso().replace(":", "").replace("-", "")
    directory = paths.state / "errors"
    directory.mkdir(parents=True, exist_ok=True)
    artifact = directory / f"ingest-{source_id}-{timestamp}.txt"
    artifact.write_text(
        "\n".join(
            [
                f"source_id: {source_id}",
                f"first_error: {first_error}",
                f"repair_error: {repair_error}",
                "",
                "raw_response:",
                content,
                "",
                "repair_response:",
                repaired_content,
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return artifact.relative_to(paths.root).as_posix()


def _extract_json(content: str) -> str:
    text = content.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1).strip()
    if text.startswith("{"):
        return text
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start : end + 1]
    raise ValueError("LLM response did not contain a JSON object")
