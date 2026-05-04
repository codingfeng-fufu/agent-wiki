from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from llmw.core.config import ensure_project_dirs, load_config
from llmw.core.fs import relative_to_root
from llmw.core.models import HealthIssue, SearchResult, SourceRecord
from llmw.core.paths import WikiPaths
from llmw.health.checks import HealthChecker
from llmw.llm.config import load_provider_registry
from llmw.llm.ingest import IngestRunResult, run_ingest
from llmw.search.providers import build_search_service
from llmw.sources.registry import add_source, load_registry
from llmw.wiki.index import index_is_current


@dataclass(frozen=True)
class InboxCandidate:
    rel_path: str
    size_bytes: int

    @property
    def label(self) -> str:
        return f"{self.rel_path} ({self.size_bytes} bytes)"


@dataclass(frozen=True)
class HealthSummary:
    issues: list[HealthIssue]

    @property
    def errors(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "error")

    @property
    def warnings(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "warning")

    @property
    def infos(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "info")


IngestRunner = Callable[..., IngestRunResult]


class WizardController:
    def __init__(
        self,
        paths: WikiPaths,
        *,
        provider: str | None = None,
        provider_config: Path | None = None,
        max_chars: int = 12000,
        ingest_runner: IngestRunner = run_ingest,
    ):
        self.paths = paths
        self.provider = provider
        self.provider_config = provider_config
        self.max_chars = max_chars
        self.ingest_runner = ingest_runner

    def scan_unregistered_sources(self) -> list[InboxCandidate]:
        ensure_project_dirs(self.paths)
        config = load_config(self.paths)
        allowed = {extension.lower() for extension in config.source_extensions}
        registered = self._registered_source_paths()
        candidates: list[InboxCandidate] = []
        if not self.paths.raw_inbox.exists():
            return candidates

        for path in sorted(self.paths.raw_inbox.rglob("*")):
            if not path.is_file() or path.name == ".gitkeep":
                continue
            if path.suffix.lower() not in allowed:
                continue
            rel = relative_to_root(path, self.paths.root)
            if rel in registered:
                continue
            candidates.append(InboxCandidate(rel_path=rel, size_bytes=path.stat().st_size))
        return candidates

    def registered_sources(self) -> list[SourceRecord]:
        registry = load_registry(self.paths)
        return sorted(registry.sources.values(), key=lambda record: (record.status, record.title, record.source_id))

    def pending_ingest_sources(self) -> list[SourceRecord]:
        return [record for record in self.registered_sources() if record.status != "ingested"]

    def register_sources(self, rel_paths: list[str]) -> list[SourceRecord]:
        ensure_project_dirs(self.paths)
        config = load_config(self.paths)
        records: list[SourceRecord] = []
        for rel_path in rel_paths:
            records.append(add_source(self.paths, self.paths.root / rel_path, config.source_extensions))
        return records

    def ingest_source(self, source_id: str) -> IngestRunResult:
        registry = load_provider_registry(self.paths, self.provider_config)
        provider_config = registry.get(self.provider)
        return self.ingest_runner(
            self.paths,
            source_id,
            provider=provider_config,
            dry_run=False,
            max_chars=self.max_chars,
        )

    def health_summary(self) -> HealthSummary:
        return HealthSummary(HealthChecker(self.paths).run())

    def index_current(self) -> bool:
        return index_is_current(self.paths)

    def search(self, query: str, *, limit: int = 5) -> tuple[list[SearchResult], str | None]:
        config = load_config(self.paths)
        service = build_search_service(self.paths, config.qmd_collection)
        return service.search(query, limit=limit)

    def _registered_source_paths(self) -> set[str]:
        registry = load_registry(self.paths)
        return {
            path
            for record in registry.sources.values()
            for path in [record.path, record.original_path]
            if path
        }
