from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Callable

from llmw.core.fs import ensure_parent, today_iso, utc_now_iso
from llmw.core.markdown import dump_frontmatter
from llmw.core.paths import WikiPaths
from llmw.llm.client import OpenAICompatibleClient
from llmw.llm.config import ProviderConfig, load_system_prompt
from llmw.wiki.index import rebuild_index
from llmw.wiki.log import append_log
from llmw.wiki.pages import WikiPage, load_pages


@dataclass(frozen=True)
class HealthAuditPage:
    path: str
    title: str
    page_type: str
    sources: list[str]
    summary: str
    content: str


@dataclass(frozen=True)
class HealthAuditResult:
    report: str
    pages: list[HealthAuditPage]
    model: str
    usage: dict | None = None
    saved_page: str | None = None
    issues: list[dict] = field(default_factory=list)


ClientFactory = Callable[[ProviderConfig], OpenAICompatibleClient]


def run_health_audit(
    paths: WikiPaths,
    *,
    provider: ProviderConfig,
    save: bool = False,
    max_page_chars: int = 2500,
    max_pages: int = 40,
    client_factory: ClientFactory = OpenAICompatibleClient,
) -> HealthAuditResult:
    usage = provider.usage.get("health")
    if usage is None:
        raise KeyError("Provider config does not define usage.health")

    pages = collect_audit_pages(paths, max_pages=max_pages, max_page_chars=max_page_chars)
    system_prompt = load_system_prompt(paths, usage)
    prompt = build_health_audit_prompt(paths, pages)
    response = client_factory(provider).chat(
        system_prompt=system_prompt,
        user_prompt=prompt,
        temperature=usage.temperature,
        top_p=usage.top_p,
        max_tokens=usage.max_tokens,
    )
    saved_page = save_health_audit(paths, response.content, pages) if save else None
    return HealthAuditResult(
        report=response.content.strip(),
        pages=pages,
        model=response.model,
        usage=response.usage,
        saved_page=saved_page,
        issues=extract_audit_issues(response.content),
    )


def extract_audit_issues(report: str, *, limit: int = 20) -> list[dict]:
    issues: list[dict] = []
    section = ""
    for raw_line in report.splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            section = line.removeprefix("## ").strip()
            continue
        if not line.startswith(("-", "*")):
            continue
        text = line.lstrip("-* ").strip()
        if not text:
            continue
        normalized = section.lower()
        if normalized not in {"findings", "recommended edits", "follow-up sources"}:
            continue
        issues.append(
            {
                "section": section or "Audit",
                "title": text[:160],
                "detail": text,
                "severity": "medium" if normalized != "follow-up sources" else "low",
            }
        )
        if len(issues) >= limit:
            break
    return issues


def collect_audit_pages(
    paths: WikiPaths,
    *,
    max_pages: int = 40,
    max_page_chars: int = 2500,
) -> list[HealthAuditPage]:
    pages = sorted(
        load_pages(paths),
        key=lambda page: (_page_type_rank(page.page_type), page.title.lower(), page.rel_path),
    )
    return [_audit_page(page, max_page_chars=max_page_chars) for page in pages[:max_pages]]


def build_health_audit_prompt(paths: WikiPaths, pages: list[HealthAuditPage]) -> str:
    index = _read_optional(paths.index_path, fallback="# Index\n\nNo index found.")
    log = _recent_log(paths.log_path)
    page_count_note = f"{len(pages)} page(s) included"
    if not pages:
        evidence = "No maintained wiki pages were found."
    else:
        evidence = "\n\n".join(_format_audit_page(index, page) for index, page in enumerate(pages, start=1))

    return f"""Review the maintained wiki for semantic maintenance issues.

Use only the wiki context below. Do not use outside facts.

Look for:
- contradictions between pages
- stale claims replaced by newer source-backed pages
- missing cross-links between related pages
- orphan pages that should be linked
- important mentioned concepts without pages
- pages with weak or missing source traceability
- follow-up source gaps that would improve the wiki

Return Markdown with:
1. `## Summary`
2. `## Findings`
3. `## Recommended Edits`
4. `## Follow-up Sources`

Keep each finding concrete. Cite page titles, paths, or source_id values.

Included evidence: {page_count_note}

Current index:
```markdown
{index}
```

Recent log:
```markdown
{log}
```

Wiki pages:
{evidence}
"""


def save_health_audit(paths: WikiPaths, report: str, pages: list[HealthAuditPage]) -> str:
    title = f"Health Audit {today_iso()}"
    rel_path = _unique_health_audit_path(paths)
    source_ids = _source_ids(pages)
    body = _saved_audit_body(title, report, pages)
    content = dump_frontmatter(
        {
            "title": title,
            "type": "output",
            "status": "draft",
            "created": utc_now_iso(),
            "updated": utc_now_iso(),
            "sources": source_ids,
            "tags": ["health", "audit"],
        },
        body,
    )
    destination = paths.root / rel_path
    ensure_parent(destination)
    destination.write_text(content.rstrip() + "\n", encoding="utf-8")
    append_log(paths, "Health", title, f"Saved semantic health audit page `{rel_path}`.")
    rebuild_index(paths)
    return rel_path.as_posix()


def _audit_page(page: WikiPage, *, max_page_chars: int) -> HealthAuditPage:
    sources = page.metadata.get("sources") or []
    if not isinstance(sources, list):
        sources = []
    return HealthAuditPage(
        path=page.rel_path,
        title=page.title,
        page_type=page.page_type,
        sources=[str(source) for source in sources],
        summary=page.summary,
        content=page.body.strip()[:max_page_chars],
    )


def _format_audit_page(index: int, page: HealthAuditPage) -> str:
    source_note = ", ".join(page.sources) if page.sources else "none"
    return f"""[{index}] {page.title}
- path: {page.path}
- type: {page.page_type}
- sources: {source_note}
- summary: {page.summary}

```markdown
{page.content}
```"""


def _saved_audit_body(title: str, report: str, pages: list[HealthAuditPage]) -> str:
    page_links = "\n".join(f"- [[{page.title}]] (`{page.path}`)" for page in pages) or "- No wiki pages included."
    return f"""# {title}

## Report

{report.strip()}

## Reviewed Pages

{page_links}
"""


def _source_ids(pages: list[HealthAuditPage]) -> list[str]:
    ids: list[str] = []
    for page in pages:
        for source_id in page.sources:
            if source_id not in ids:
                ids.append(source_id)
    return ids


def _unique_health_audit_path(paths: WikiPaths) -> Path:
    base = f"health-audit-{today_iso()}"
    candidate = Path("wiki") / "outputs" / f"{base}.md"
    index = 2
    while (paths.root / candidate).exists():
        candidate = Path("wiki") / "outputs" / f"{base}-{index}.md"
        index += 1
    return candidate


def _read_optional(path: Path, *, fallback: str) -> str:
    if not path.exists():
        return fallback
    return path.read_text(encoding="utf-8", errors="replace").strip()


def _recent_log(path: Path, *, max_chars: int = 6000) -> str:
    content = _read_optional(path, fallback="# Log\n\nNo log found.")
    return content[-max_chars:]


def _page_type_rank(page_type: str) -> int:
    order = {"source": 0, "entity": 1, "concept": 2, "analysis": 3, "output": 4}
    return order.get(page_type, 5)
