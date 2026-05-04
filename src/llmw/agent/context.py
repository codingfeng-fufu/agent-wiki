from __future__ import annotations

import json
import os
import re
from collections import Counter
from typing import Any

from llmw.core.config import load_config
from llmw.core.fs import relative_to_root
from llmw.core.paths import WikiPaths
from llmw.health.checks import HealthChecker
from llmw.sources.registry import SourceRegistry, load_registry
from llmw.wiki.pages import load_pages


ENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def build_context(paths: WikiPaths) -> dict[str, Any]:
    config = load_config(paths)
    registry = load_registry(paths)
    all_pages = load_pages(paths, include_special=True)
    special_paths = {paths.index_path, paths.log_path}
    pages = [page for page in all_pages if page.path not in special_paths]
    health = HealthChecker(paths, pages=all_pages, registry=registry).run()
    source_statuses = Counter(record.status for record in registry.sources.values())
    page_types = Counter(page.page_type for page in pages)
    provider = _provider_status(paths)
    context = {
        "root": paths.root.as_posix(),
        "project_name": config.project_name,
        "wiki": {
            "pages": len(pages),
            "page_types": dict(sorted(page_types.items())),
            "index_current": not any(issue.code == "index-stale" for issue in health),
        },
        "sources": {
            "total": len(registry.sources),
            "statuses": dict(sorted(source_statuses.items())),
            "pending_ingest": [
                record.source_id for record in registry.sources.values() if record.status != "ingested"
            ],
        },
        "health": _health_summary(health),
        "provider": provider,
        "recommended_commands": _recommended_commands(paths, registry=registry, source_extensions=config.source_extensions),
    }
    return context


def find_unregistered_sources(
    paths: WikiPaths,
    *,
    registry: SourceRegistry | None = None,
    source_extensions: list[str] | None = None,
) -> list[str]:
    if source_extensions is None:
        source_extensions = load_config(paths).source_extensions
    allowed = {extension.lower() for extension in source_extensions}
    registry = registry or load_registry(paths)
    registered = {
        source_path
        for record in registry.sources.values()
        for source_path in [record.path, record.original_path]
        if source_path
    }
    sources: list[str] = []
    for path in sorted(paths.raw_inbox.rglob("*")) if paths.raw_inbox.exists() else []:
        if not path.is_file() or path.name == ".gitkeep":
            continue
        rel = relative_to_root(path, paths.root)
        if path.suffix.lower() in allowed and rel not in registered:
            sources.append(rel)
    return sources


def _health_summary(issues: list) -> dict[str, Any]:
    counts = Counter(issue.severity for issue in issues)
    return {
        "errors": counts.get("error", 0),
        "warnings": counts.get("warning", 0),
        "infos": counts.get("info", 0),
        "issues": [issue.model_dump() for issue in issues[:20]],
    }


def _provider_status(paths: WikiPaths) -> dict[str, Any]:
    _load_env_files(paths)
    provider_path = paths.system / "providers" / "qwen-plus.json"
    if not provider_path.exists():
        return {"config_exists": False}
    try:
        data = json.loads(provider_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"config_exists": True, "valid": False, "error": str(exc)}
    providers = data.get("providers") or {}
    default = data.get("default_provider")
    default_config = providers.get(default, {}) if isinstance(providers, dict) else {}
    api_key_env = default_config.get("api_key_env")
    return {
        "config_exists": True,
        "valid": True,
        "default_provider": default,
        "providers": sorted(providers.keys()) if isinstance(providers, dict) else [],
        "api_key_env": api_key_env,
        "api_key_present": bool(api_key_env and os.environ.get(str(api_key_env))),
    }


def _recommended_commands(
    paths: WikiPaths,
    *,
    registry: SourceRegistry,
    source_extensions: list[str],
) -> list[str]:
    commands = ["llmw mcp --root .", "llmw_context", "llmw_next", "llmw_health_check"]
    if find_unregistered_sources(paths, registry=registry, source_extensions=source_extensions):
        commands.append("llmw_plan goal='register all sources'")
    if any(record.status != "ingested" for record in registry.sources.values()):
        commands.append("llmw ingest packet <source_id>")
    commands.extend(
        [
            "llmw_search query='<query>'",
            "llmw search-daemon start --deep",
            "llmw_query question='<question>'",
        ]
    )
    return commands


def _load_env_files(paths: WikiPaths) -> None:
    for env_path in [paths.root / ".env", paths.state / ".env"]:
        if not env_path.exists():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            key = key.strip()
            if not ENV_NAME_RE.match(key):
                continue
            os.environ.setdefault(key, _clean_env_value(value.strip()))


def _clean_env_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value
