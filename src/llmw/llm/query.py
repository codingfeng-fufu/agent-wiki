from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from llmw.core.fs import ensure_parent, slugify, today_iso, utc_now_iso
from llmw.core.markdown import dump_frontmatter
from llmw.core.models import SearchResult
from llmw.core.paths import WikiPaths
from llmw.core.config import load_config
from llmw.llm.client import OpenAICompatibleClient
from llmw.llm.config import ProviderConfig, load_system_prompt
from llmw.search.providers import SearchService, build_search_service
from llmw.wiki.index import rebuild_index
from llmw.wiki.log import append_log
from llmw.wiki.pages import WikiPage, load_page


@dataclass(frozen=True)
class QueryEvidencePage:
    path: str
    title: str
    page_type: str
    sources: list[str]
    summary: str
    content: str
    score: float | None = None


@dataclass(frozen=True)
class QueryRunResult:
    question: str
    answer: str
    pages: list[QueryEvidencePage]
    model: str
    usage: dict | None = None
    warning: str | None = None
    saved_page: str | None = None


ClientFactory = Callable[[ProviderConfig], OpenAICompatibleClient]


def run_query(
    paths: WikiPaths,
    question: str,
    *,
    provider: ProviderConfig,
    limit: int = 5,
    deep: bool = False,
    save: bool = False,
    max_page_chars: int = 4000,
    client_factory: ClientFactory = OpenAICompatibleClient,
    search_service: SearchService | None = None,
) -> QueryRunResult:
    clean_question = question.strip()
    if not clean_question:
        raise ValueError("Query must not be empty")

    usage = provider.usage.get("query")
    if usage is None:
        raise KeyError("Provider config does not define usage.query")

    service = search_service or build_search_service(paths, load_config(paths).qmd_collection, use_qmd=deep)
    evidence_pages, warning = search_evidence_pages(
        paths,
        service,
        clean_question,
        limit=limit,
        deep=deep,
        max_page_chars=max_page_chars,
    )
    if not evidence_pages:
        raise ValueError("No relevant wiki pages found for query")

    system_prompt = load_system_prompt(paths, usage)
    prompt = build_query_prompt(clean_question, evidence_pages)
    response = client_factory(provider).chat(
        system_prompt=system_prompt,
        user_prompt=prompt,
        temperature=usage.temperature,
        top_p=usage.top_p,
        max_tokens=usage.max_tokens,
    )
    saved_page = save_query_output(paths, clean_question, response.content, evidence_pages) if save else None

    return QueryRunResult(
        question=clean_question,
        answer=response.content.strip(),
        pages=evidence_pages,
        model=response.model,
        usage=response.usage,
        warning=warning,
        saved_page=saved_page,
    )


def search_evidence_pages(
    paths: WikiPaths,
    service: SearchService,
    question: str,
    *,
    limit: int,
    deep: bool,
    max_page_chars: int,
) -> tuple[list[QueryEvidencePage], str | None]:
    search_limit = max(limit * 3, limit)
    results, warning = service.search(question, limit=search_limit, deep=deep)
    pages: list[QueryEvidencePage] = []
    seen: set[Path] = set()
    special = {paths.index_path.resolve(), paths.log_path.resolve()}
    for result in results:
        page_path = (paths.root / result.path).resolve()
        if page_path in special or page_path in seen:
            continue
        if not page_path.exists() or not page_path.is_file():
            continue
        try:
            page_path.relative_to(paths.wiki.resolve())
        except ValueError:
            continue
        page = load_page(paths, page_path)
        pages.append(_evidence_page(page, result, max_page_chars=max_page_chars))
        seen.add(page_path)
        if len(pages) >= limit:
            break
    return pages, warning


def build_query_prompt(question: str, pages: list[QueryEvidencePage]) -> str:
    evidence = "\n\n".join(_format_evidence_page(index, page) for index, page in enumerate(pages, start=1))
    return f"""Answer the question using only the maintained wiki evidence below.

Rules:
- If the evidence is insufficient, say so explicitly.
- Cite page titles or source_id values for factual claims.
- Do not use facts that are not supported by the evidence.
- Keep the answer concise, but include enough detail to be useful.

Question:
{question}

Evidence pages:
{evidence}
"""


def save_query_output(
    paths: WikiPaths,
    question: str,
    answer: str,
    pages: list[QueryEvidencePage],
) -> str:
    source_ids = _source_ids(pages)
    title = question.strip().rstrip("?？") or "Query Output"
    rel_path = _unique_output_path(paths, title)
    body = _saved_output_body(question, answer, pages)
    content = dump_frontmatter(
        {
            "title": title,
            "type": "output",
            "status": "draft",
            "created": utc_now_iso(),
            "updated": utc_now_iso(),
            "sources": source_ids,
            "tags": ["query"],
        },
        body,
    )
    destination = paths.root / rel_path
    ensure_parent(destination)
    destination.write_text(content.rstrip() + "\n", encoding="utf-8")
    append_log(paths, "Query", title, f"Answered query and saved output page `{rel_path}`.")
    rebuild_index(paths)
    return rel_path.as_posix()


def _evidence_page(page: WikiPage, result: SearchResult, *, max_page_chars: int) -> QueryEvidencePage:
    sources = page.metadata.get("sources") or []
    if not isinstance(sources, list):
        sources = []
    return QueryEvidencePage(
        path=page.rel_path,
        title=page.title,
        page_type=page.page_type,
        sources=[str(source) for source in sources],
        summary=page.summary,
        content=page.body.strip()[:max_page_chars],
        score=result.score,
    )


def _format_evidence_page(index: int, page: QueryEvidencePage) -> str:
    source_note = ", ".join(page.sources) if page.sources else "none"
    return f"""[{index}] {page.title}
- path: {page.path}
- type: {page.page_type}
- sources: {source_note}
- summary: {page.summary}

```markdown
{page.content}
```"""


def _saved_output_body(question: str, answer: str, pages: list[QueryEvidencePage]) -> str:
    page_links = "\n".join(f"- [[{page.title}]] (`{page.path}`)" for page in pages)
    return f"""# {question}

## Answer

{answer.strip()}

## Evidence Pages

{page_links}
"""


def _source_ids(pages: list[QueryEvidencePage]) -> list[str]:
    ids: list[str] = []
    for page in pages:
        for source_id in page.sources:
            if source_id not in ids:
                ids.append(source_id)
    return ids


def _unique_output_path(paths: WikiPaths, title: str) -> Path:
    base = f"{slugify(title, fallback='query')}-{today_iso()}"
    candidate = Path("wiki") / "outputs" / f"{base}.md"
    index = 2
    while (paths.root / candidate).exists():
        candidate = Path("wiki") / "outputs" / f"{base}-{index}.md"
        index += 1
    return candidate
