from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from llmw.core.markdown import extract_wiki_links, read_text
from llmw.core.paths import WikiPaths
from llmw.wiki.pages import WikiPage, load_pages


@dataclass(frozen=True)
class LinkAnalysis:
    bad_links: list[tuple[Path, str]]
    inbound_counts: dict[Path, int]


def title_map(paths: WikiPaths, pages: list[WikiPage] | None = None) -> dict[str, WikiPage]:
    mapping: dict[str, WikiPage] = {}
    for page in pages if pages is not None else load_pages(paths, include_special=True):
        mapping[page.title] = page
        mapping[page.path.stem] = page
    return mapping


def outbound_links(page_path: Path) -> list[str]:
    return extract_wiki_links(read_text(page_path))


def analyze_links(paths: WikiPaths, *, pages: list[WikiPage] | None = None) -> LinkAnalysis:
    all_pages = pages or load_pages(paths, include_special=True)
    special_paths = {paths.index_path, paths.log_path}
    content_pages = [page for page in all_pages if page.path not in special_paths]
    mapping = title_map(paths, all_pages)
    counts: dict[Path, int] = defaultdict(int)
    issues: list[tuple[Path, str]] = []
    for page in content_pages:
        counts.setdefault(page.path, 0)
        for link in extract_wiki_links(page.body):
            target = mapping.get(link)
            if not target:
                issues.append((page.path, link))
            elif target.path != page.path:
                counts[target.path] += 1
    return LinkAnalysis(bad_links=issues, inbound_counts=counts)


def bad_links(paths: WikiPaths) -> list[tuple[Path, str]]:
    return analyze_links(paths).bad_links


def inbound_counts(paths: WikiPaths) -> dict[Path, int]:
    return analyze_links(paths).inbound_counts
