from __future__ import annotations

from collections import defaultdict

from llmw.core.paths import WikiPaths
from llmw.wiki.pages import WikiPage, load_pages


TYPE_ORDER = ["source", "entity", "concept", "analysis", "output", "other"]


def _link_for(page: WikiPage) -> str:
    return f"[[{page.title}]]"


def build_index_content(paths: WikiPaths, *, pages: list[WikiPage] | None = None) -> str:
    pages = pages if pages is not None else load_pages(paths)
    grouped: dict[str, list[WikiPage]] = defaultdict(list)
    for page in pages:
        grouped[page.page_type].append(page)

    lines = [
        "---",
        "title: Index",
        "type: index",
        "---",
        "",
        "# Index",
        "",
        f"Generated from `{len(pages)}` wiki pages.",
        "",
    ]

    for page_type in TYPE_ORDER:
        entries = sorted(grouped.get(page_type, []), key=lambda page: page.title.lower())
        if not entries:
            continue
        lines.extend([f"## {page_type.title()} Pages", ""])
        for page in entries:
            summary = f" - {page.summary}" if page.summary else ""
            sources = page.metadata.get("sources") or []
            source_note = f" `sources:{len(sources)}`" if isinstance(sources, list) and sources else ""
            lines.append(f"- {_link_for(page)}{source_note}{summary}".rstrip())
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def rebuild_index(paths: WikiPaths) -> str:
    content = build_index_content(paths)
    paths.index_path.parent.mkdir(parents=True, exist_ok=True)
    paths.index_path.write_text(content, encoding="utf-8")
    return content


def index_is_current(paths: WikiPaths, *, pages: list[WikiPage] | None = None) -> bool:
    expected = build_index_content(paths, pages=pages)
    if not paths.index_path.exists():
        return False
    return paths.index_path.read_text(encoding="utf-8", errors="replace") == expected
