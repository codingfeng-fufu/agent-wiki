from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from llmw.agent.context import build_context
from llmw.agent.tools import build_next_tasks
from llmw.core.fs import utc_now_iso
from llmw.core.paths import WikiPaths
from llmw.integrations.codex import DEFAULT_SERVER_NAME, codex_status, expected_codex_command, probe_mcp_command
from llmw.search.providers import QmdSearchProvider, RgSearchProvider


def run_doctor(
    paths: WikiPaths,
    *,
    include_codex: bool = True,
    probe_mcp: bool = False,
    strict: bool = False,
    codex_server_name: str = DEFAULT_SERVER_NAME,
    mcp_timeout: float = 10,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    context: dict[str, Any] | None = None
    next_tasks: list[dict[str, Any]] = []

    missing_dirs = [_rel(path, paths.root) for path in paths.required_dirs() if not path.exists()]
    _add_check(
        checks,
        "project.dirs",
        "Required project directories",
        "fail" if missing_dirs else "pass",
        "Missing required directories." if missing_dirs else "Required directories exist.",
        details={"missing": missing_dirs},
        action="llmw init" if missing_dirs else None,
    )

    _add_check(
        checks,
        "project.config",
        "Project config",
        "pass" if paths.config_path.exists() else "warn",
        ".llmw/config.json exists." if paths.config_path.exists() else ".llmw/config.json is missing; defaults can run, but init is recommended.",
        details={"path": _rel(paths.config_path, paths.root)},
        action="llmw init" if not paths.config_path.exists() else None,
    )

    try:
        context = build_context(paths)
        next_tasks = build_next_tasks(paths)
    except Exception as exc:
        _add_check(
            checks,
            "project.context",
            "Project context",
            "fail",
            f"Could not build project context: {exc}",
            action="llmw context --json",
        )
    else:
        _add_check(
            checks,
            "project.context",
            "Project context",
            "pass",
            f"Context loaded: {context['wiki']['pages']} wiki page(s), {context['sources']['total']} source(s).",
        )
        _add_context_checks(checks, context)

    _add_search_checks(checks, paths)

    if include_codex:
        _add_codex_check(checks, paths, server_name=codex_server_name)

    if probe_mcp:
        _add_mcp_probe_check(checks, paths, timeout=mcp_timeout)

    counts = Counter(check["status"] for check in checks)
    failed = counts.get("fail", 0)
    warned = counts.get("warn", 0)
    strict_failed = bool(strict and warned)
    ok = failed == 0 and not strict_failed
    return {
        "ok": ok,
        "readiness": _readiness(ok=ok, warnings=warned),
        "strict": strict,
        "checked_at": utc_now_iso(),
        "root": paths.root.as_posix(),
        "summary": {
            "pass": counts.get("pass", 0),
            "warn": warned,
            "fail": failed,
            "skip": counts.get("skip", 0),
        },
        "checks": checks,
        "next_actions": _next_actions(checks, next_tasks),
        "context": context,
    }


def format_doctor(result: dict[str, Any]) -> str:
    lines = [
        "LLM Wiki Doctor",
        f"Root: {result['root']}",
        f"Readiness: {result['readiness']}",
        f"Checks: {result['summary']['pass']} pass, {result['summary']['warn']} warn, {result['summary']['fail']} fail, {result['summary']['skip']} skip",
        "",
    ]
    for check in result["checks"]:
        marker = {"pass": "PASS", "warn": "WARN", "fail": "FAIL", "skip": "SKIP"}.get(check["status"], check["status"].upper())
        lines.append(f"[{marker}] {check['title']}: {check['message']}")
        if check.get("action"):
            lines.append(f"  next: {check['action']}")
    if result["next_actions"]:
        lines.append("")
        lines.append("Next actions:")
        for action in result["next_actions"]:
            lines.append(f"- {action}")
    return "\n".join(lines)


def _add_context_checks(checks: list[dict[str, Any]], context: dict[str, Any]) -> None:
    health = context["health"]
    if health["errors"]:
        health_status = "fail"
        health_message = f"{health['errors']} error(s), {health['warnings']} warning(s), {health['infos']} info issue(s)."
        health_action = "llmw health check --json"
    elif health["warnings"]:
        health_status = "warn"
        health_message = f"{health['warnings']} warning(s), {health['infos']} info issue(s)."
        health_action = "llmw health check"
    else:
        health_status = "pass"
        health_message = "No structural health issues."
        health_action = None
    _add_check(checks, "wiki.health", "Wiki health", health_status, health_message, details=health, action=health_action)

    index_current = bool(context["wiki"]["index_current"])
    _add_check(
        checks,
        "wiki.index",
        "Wiki index",
        "pass" if index_current else "warn",
        "wiki/index.md is current." if index_current else "wiki/index.md is stale or missing.",
        action=None if index_current else "llmw index rebuild",
    )

    pending = context["sources"]["pending_ingest"]
    _add_check(
        checks,
        "sources.ingest",
        "Source ingestion",
        "pass" if not pending else "warn",
        "All registered sources are ingested." if not pending else f"{len(pending)} source(s) still need ingest.",
        details={"pending": pending},
        action=None if not pending else "llmw ingest packet <source_id>",
    )

    provider = context["provider"]
    if not provider.get("config_exists"):
        status = "warn"
        message = "No provider config found; offline commands still work."
        action = "add system/providers/qwen-plus.json or run llmw init"
    elif provider.get("valid") is False:
        status = "fail"
        message = f"Provider config is invalid: {provider.get('error')}"
        action = "fix system/providers/qwen-plus.json"
    elif not provider.get("api_key_present"):
        status = "warn"
        message = f"Provider config exists, but {provider.get('api_key_env') or 'API key env'} is not set."
        action = f"set {provider.get('api_key_env')}" if provider.get("api_key_env") else None
    else:
        status = "pass"
        message = f"Provider {provider.get('default_provider')} is configured and API key is present."
        action = None
    _add_check(checks, "llm.provider", "LLM provider", status, message, details=provider, action=action)


def _add_search_checks(checks: list[dict[str, Any]], paths: WikiPaths) -> None:
    fast_provider = RgSearchProvider(paths)
    _add_check(
        checks,
        "search.fast",
        "Fast search",
        "pass" if fast_provider.available() else "fail",
        "Fast rg/Python search is available." if fast_provider.available() else "Fast search is unavailable.",
        action=None if fast_provider.available() else "llmw init",
    )

    qmd_provider = QmdSearchProvider(paths, "llmwiki")
    qmd_available = qmd_provider.available()
    _add_check(
        checks,
        "search.deep",
        "Deep qmd search",
        "pass" if qmd_available else "skip",
        "qmd deep search is available." if qmd_available else "qmd is not available; deep search is optional.",
        details={"optional": True},
        action=None if qmd_available else "uv sync --extra search",
    )


def _add_codex_check(checks: list[dict[str, Any]], paths: WikiPaths, *, server_name: str) -> None:
    status = codex_status(paths, server_name=server_name)
    if status["ready"]:
        check_status = "pass"
        message = f"Codex MCP server `{server_name}` is configured."
        action = None
    elif not status["codex_found"]:
        check_status = "warn"
        message = "Codex executable was not found; CLI remains usable."
        action = None
    else:
        check_status = "warn"
        message = f"Codex MCP server `{server_name}` is not ready."
        action = status["install_command"]
    _add_check(checks, "integration.codex", "Codex integration", check_status, message, details=status, action=action)


def _add_mcp_probe_check(checks: list[dict[str, Any]], paths: WikiPaths, *, timeout: float) -> None:
    command, args = expected_codex_command(paths)
    probe = probe_mcp_command([command, *args], cwd=paths.root, timeout=timeout)
    _add_check(
        checks,
        "mcp.probe",
        "MCP probe",
        "pass" if probe.get("ok") else "fail",
        f"MCP handshake passed with {probe.get('tools_count')} tool(s)." if probe.get("ok") else f"MCP probe failed: {probe.get('error')}",
        details=probe,
        action=None if probe.get("ok") else "llmw mcp --root .",
    )


def _add_check(
    checks: list[dict[str, Any]],
    check_id: str,
    title: str,
    status: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
    action: str | None = None,
) -> None:
    checks.append(
        {
            "id": check_id,
            "title": title,
            "status": status,
            "message": message,
            "details": details or {},
            "action": action,
        }
    )


def _next_actions(checks: list[dict[str, Any]], next_tasks: list[dict[str, Any]]) -> list[str]:
    actions: list[str] = []
    for check in checks:
        action = check.get("action")
        if action and action not in actions:
            actions.append(action)
    for task in next_tasks:
        command = task.get("command")
        if command and command not in actions:
            actions.append(command)
    return actions[:8]


def _readiness(*, ok: bool, warnings: int) -> str:
    if not ok:
        return "blocked"
    if warnings:
        return "usable-with-warnings"
    return "ready"


def _rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()
