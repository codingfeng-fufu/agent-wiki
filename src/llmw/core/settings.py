from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class LLMWConfig:
    project_name: str = "LLM Wiki"
    qmd_collection: str = "llmwiki"
    obsidian_links: bool = True
    source_extensions: list[str] = field(
        default_factory=lambda: [".md", ".markdown", ".txt", ".text", ".pdf"]
    )

    @classmethod
    def model_validate(cls, data: Any) -> "LLMWConfig":
        if not isinstance(data, dict):
            return cls()
        defaults = cls()
        source_extensions = data.get("source_extensions", defaults.source_extensions)
        if not isinstance(source_extensions, list):
            source_extensions = defaults.source_extensions
        return cls(
            project_name=str(data.get("project_name", defaults.project_name)),
            qmd_collection=str(data.get("qmd_collection", defaults.qmd_collection)),
            obsidian_links=bool(data.get("obsidian_links", defaults.obsidian_links)),
            source_extensions=[str(extension) for extension in source_extensions],
        )

    def model_dump(self) -> dict[str, object]:
        return asdict(self)
