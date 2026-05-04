from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WikiPaths:
    root: Path
    raw: Path
    raw_inbox: Path
    raw_processed: Path
    raw_assets: Path
    wiki: Path
    wiki_sources: Path
    wiki_entities: Path
    wiki_concepts: Path
    wiki_analyses: Path
    wiki_outputs: Path
    index_path: Path
    log_path: Path
    system: Path
    templates: Path
    state: Path
    config_path: Path
    source_registry_path: Path
    qmd_config_dir: Path
    qmd_data_dir: Path
    qmd_db_path: Path
    qmd_manifest_path: Path

    @classmethod
    def from_root(cls, root: str | Path = ".") -> "WikiPaths":
        base = Path(root).resolve()
        raw = base / "raw"
        wiki = base / "wiki"
        system = base / "system"
        state = base / ".llmw"
        return cls(
            root=base,
            raw=raw,
            raw_inbox=raw / "inbox",
            raw_processed=raw / "processed",
            raw_assets=raw / "assets",
            wiki=wiki,
            wiki_sources=wiki / "sources",
            wiki_entities=wiki / "entities",
            wiki_concepts=wiki / "concepts",
            wiki_analyses=wiki / "analyses",
            wiki_outputs=wiki / "outputs",
            index_path=wiki / "index.md",
            log_path=wiki / "log.md",
            system=system,
            templates=system / "templates",
            state=state,
            config_path=state / "config.json",
            source_registry_path=state / "sources.json",
            qmd_config_dir=state / "qmd" / "config",
            qmd_data_dir=state / "qmd" / "data",
            qmd_db_path=state / "qmd" / "qmd.sqlite",
            qmd_manifest_path=state / "qmd" / "manifest.json",
        )

    def required_dirs(self) -> list[Path]:
        return [
            self.raw_inbox,
            self.raw_processed,
            self.raw_assets,
            self.wiki_sources,
            self.wiki_entities,
            self.wiki_concepts,
            self.wiki_analyses,
            self.wiki_outputs,
            self.templates,
            self.state,
        ]
