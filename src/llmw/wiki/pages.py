from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from llmw.core.fs import relative_to_root
from llmw.core.markdown import extract_summary, extract_title, read_markdown
from llmw.core.models import WikiPageMeta
from llmw.core.paths import WikiPaths


@dataclass(frozen=True)
class WikiPage:
    path: Path
    rel_path: str
    metadata: dict
    body: str
    title: str
    page_type: str
    summary: str


def iter_markdown_pages(paths: WikiPaths, *, include_special: bool = False) -> list[Path]:
    if not paths.wiki.exists():
        return []
    pages = sorted(paths.wiki.rglob("*.md"))
    if include_special:
        return pages
    special = {paths.index_path, paths.log_path}
    return [page for page in pages if page not in special]


def load_page(paths: WikiPaths, path: Path) -> WikiPage:
    metadata, body = read_markdown(path)
    title = extract_title(path, body, metadata)
    page_type = str(metadata.get("type") or infer_page_type(paths, path))
    return WikiPage(
        path=path,
        rel_path=relative_to_root(path, paths.root),
        metadata=metadata,
        body=body,
        title=title,
        page_type=page_type,
        summary=extract_summary(body),
    )


def load_pages(paths: WikiPaths, *, include_special: bool = False) -> list[WikiPage]:
    return [load_page(paths, page) for page in iter_markdown_pages(paths, include_special=include_special)]


def infer_page_type(paths: WikiPaths, path: Path) -> str:
    try:
        rel = path.relative_to(paths.wiki)
    except ValueError:
        try:
            rel = path.resolve().relative_to(paths.wiki.resolve())
        except ValueError:
            return "other"
    first = rel.parts[0] if rel.parts else ""
    return {
        "sources": "source",
        "entities": "entity",
        "concepts": "concept",
        "analyses": "analysis",
        "outputs": "output",
    }.get(first, "other")


def page_meta(page: WikiPage) -> WikiPageMeta:
    data = dict(page.metadata)
    data.setdefault("title", page.title)
    data.setdefault("type", page.page_type)
    data.setdefault("path", page.rel_path)
    return WikiPageMeta.model_validate(data)
