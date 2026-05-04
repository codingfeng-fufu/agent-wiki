from __future__ import annotations

import json
from pathlib import Path

from llmw.core.fs import ensure_parent
from llmw.core.paths import WikiPaths
from llmw.core.settings import LLMWConfig


def load_config(paths: WikiPaths) -> LLMWConfig:
    if not paths.config_path.exists():
        return LLMWConfig()
    data = json.loads(paths.config_path.read_text(encoding="utf-8"))
    return LLMWConfig.model_validate(data)


def write_config(paths: WikiPaths, config: LLMWConfig | None = None, *, overwrite: bool = False) -> None:
    if paths.config_path.exists() and not overwrite:
        return
    ensure_parent(paths.config_path)
    value = config or LLMWConfig()
    paths.config_path.write_text(
        json.dumps(value.model_dump(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def ensure_project_dirs(paths: WikiPaths) -> None:
    for directory in paths.required_dirs():
        directory.mkdir(parents=True, exist_ok=True)

    for directory in [paths.raw_inbox, paths.raw_processed, paths.raw_assets]:
        keep = directory / ".gitkeep"
        if not keep.exists():
            keep.write_text("", encoding="utf-8")
