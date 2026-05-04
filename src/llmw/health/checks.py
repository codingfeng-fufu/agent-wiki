from __future__ import annotations

from llmw.core.fs import relative_to_root
from llmw.core.models import HealthIssue
from llmw.core.paths import WikiPaths
from llmw.core.models import SourceRegistry
from llmw.sources.registry import load_registry
from llmw.wiki.index import index_is_current
from llmw.wiki.links import analyze_links
from llmw.wiki.log import malformed_log_headings
from llmw.wiki.identity import canonical_page_key
from llmw.wiki.pages import WikiPage, load_pages


class HealthChecker:
    def __init__(
        self,
        paths: WikiPaths,
        *,
        pages: list[WikiPage] | None = None,
        registry: SourceRegistry | None = None,
    ):
        self.paths = paths
        self.pages = pages
        self.registry = registry

    def run(self) -> list[HealthIssue]:
        all_pages = self.pages if self.pages is not None else load_pages(self.paths, include_special=True)
        special_paths = {self.paths.index_path, self.paths.log_path}
        pages = [page for page in all_pages if page.path not in special_paths]
        link_analysis = analyze_links(self.paths, pages=all_pages)
        issues: list[HealthIssue] = []
        issues.extend(self._metadata_issues(pages))
        issues.extend(self._duplicate_page_issues(pages))
        issues.extend(self._link_issues(link_analysis.bad_links))
        issues.extend(self._orphan_issues(link_analysis.inbound_counts))
        issues.extend(self._source_issues())
        issues.extend(self._index_issues(pages))
        issues.extend(self._log_issues())
        return issues

    def _duplicate_page_issues(self, pages: list[WikiPage]) -> list[HealthIssue]:
        grouped: dict[str, dict[str, str]] = {}
        for page in pages:
            rel = relative_to_root(page.path, self.paths.root)
            for value in [page.title, page.path.stem]:
                key = canonical_page_key(value)
                if key:
                    grouped.setdefault(key, {})[rel] = value

        issues: list[HealthIssue] = []
        reported: set[tuple[str, ...]] = set()
        for key, paths_by_rel in sorted(grouped.items()):
            rel_paths = tuple(sorted(paths_by_rel))
            if len(rel_paths) < 2 or rel_paths in reported:
                continue
            reported.add(rel_paths)
            issues.append(
                HealthIssue(
                    severity="warning",
                    code="duplicate-canonical-page",
                    message=f"Pages share canonical identity `{key}`: {', '.join(rel_paths)}",
                    path=rel_paths[0],
                )
            )
        return issues

    def _metadata_issues(self, pages: list[WikiPage]) -> list[HealthIssue]:
        issues: list[HealthIssue] = []
        for page in pages:
            metadata = page.metadata
            if metadata.get("_frontmatter_error"):
                issues.append(
                    HealthIssue(
                        severity="error",
                        code="invalid-frontmatter",
                        message=f"Invalid YAML frontmatter: {metadata['_frontmatter_error']}",
                        path=relative_to_root(page.path, self.paths.root),
                    )
                )
            missing = [key for key in ["title", "type"] if not metadata.get(key)]
            if missing:
                issues.append(
                    HealthIssue(
                        severity="warning",
                        code="missing-frontmatter",
                        message=f"Missing frontmatter keys: {', '.join(missing)}",
                        path=relative_to_root(page.path, self.paths.root),
                    )
                )
        return issues

    def _link_issues(self, bad_link_items: list[tuple]) -> list[HealthIssue]:
        return [
            HealthIssue(
                severity="error",
                code="bad-link",
                message=f"Unresolved wiki link: [[{target}]]",
                path=relative_to_root(path, self.paths.root),
            )
            for path, target in bad_link_items
        ]

    def _orphan_issues(self, counts: dict) -> list[HealthIssue]:
        issues: list[HealthIssue] = []
        for path, count in counts.items():
            if count == 0:
                rel = relative_to_root(path, self.paths.root)
                issues.append(
                    HealthIssue(
                        severity="info",
                        code="orphan-page",
                        message="No inbound wiki links found.",
                        path=rel,
                    )
                )
        return issues

    def _source_issues(self) -> list[HealthIssue]:
        issues: list[HealthIssue] = []
        registry = self.registry or load_registry(self.paths)
        registered_paths = {
            registered_path
            for record in registry.sources.values()
            for registered_path in [record.path, record.original_path]
            if registered_path
        }
        for record in registry.sources.values():
            if not (self.paths.root / record.path).exists():
                issues.append(
                    HealthIssue(
                        severity="error",
                        code="missing-source-file",
                        message=f"Registered source file is missing: {record.source_id}",
                        path=record.path,
                    )
                )
        if self.paths.raw_inbox.exists():
            for source in sorted(self.paths.raw_inbox.rglob("*")):
                if source.is_file() and source.name != ".gitkeep":
                    rel = relative_to_root(source, self.paths.root)
                    if rel not in registered_paths:
                        issues.append(
                            HealthIssue(
                                severity="warning",
                                code="unregistered-inbox-source",
                                message="File in raw/inbox has not been registered.",
                                path=rel,
                            )
                        )
        return issues

    def _index_issues(self, pages: list[WikiPage]) -> list[HealthIssue]:
        if index_is_current(self.paths, pages=pages):
            return []
        return [
            HealthIssue(
                severity="warning",
                code="index-stale",
                message="wiki/index.md is missing or out of date; run `llmw index rebuild`.",
                path=relative_to_root(self.paths.index_path, self.paths.root),
            )
        ]

    def _log_issues(self) -> list[HealthIssue]:
        issues: list[HealthIssue] = []
        if not self.paths.log_path.exists():
            return [
                HealthIssue(
                    severity="warning",
                    code="log-missing",
                    message="wiki/log.md is missing.",
                    path=relative_to_root(self.paths.log_path, self.paths.root),
                )
            ]
        for line in malformed_log_headings(self.paths.log_path):
            issues.append(
                HealthIssue(
                    severity="warning",
                    code="malformed-log-heading",
                    message=f"Log heading at line {line} does not match `## [YYYY-MM-DD] Type | Title`.",
                    path=relative_to_root(self.paths.log_path, self.paths.root),
                )
            )
        return issues
