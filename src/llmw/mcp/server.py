from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, BinaryIO
from urllib.parse import quote, unquote

from llmw import __version__
from llmw.agent.maintain import run_maintain
from llmw.agent.context import build_context
from llmw.agent.tools import apply_plan, build_next_tasks, create_plan, load_plan, save_plan
from llmw.core.fs import relative_to_root
from llmw.core.markdown import read_text
from llmw.core.config import load_config
from llmw.core.paths import WikiPaths
from llmw.health.checks import HealthChecker
from llmw.llm.config import load_provider_registry
from llmw.llm.query import run_query
from llmw.search.benchmark import run_search_benchmark
from llmw.search.providers import build_search_service, recommend_search_strategy
from llmw.wiki.pages import load_pages


PROTOCOL_VERSION = "2024-11-05"
MCP_FRAMING_HEADERS = "headers"
MCP_FRAMING_JSONL = "jsonl"

STATIC_RESOURCES: tuple[tuple[str, str, str, str, str], ...] = (
    ("llmw://context", "Project context", "Current project state as JSON.", "application/json", ""),
    ("llmw://project/agents", "Agent operating protocol", "Repository AGENTS.md instructions.", "text/markdown", "AGENTS.md"),
    ("llmw://project/readme", "Project README", "Human and agent usage guide.", "text/markdown", "README.md"),
    (
        "llmw://system/target-state",
        "Target state",
        "Final product target and success criteria.",
        "text/markdown",
        "system/target-state.md",
    ),
    (
        "llmw://system/architecture",
        "Architecture",
        "Module boundaries and operating rules.",
        "text/markdown",
        "system/architecture.md",
    ),
    ("llmw://wiki/index", "Wiki index", "Navigable maintained wiki index.", "text/markdown", "wiki/index.md"),
    ("llmw://wiki/log", "Wiki log", "Chronological maintenance log.", "text/markdown", "wiki/log.md"),
)

PROMPT_FILES: dict[str, tuple[str, str, str]] = {
    "llmw_agent_router": (
        "Route a natural-language request to one safe LLM Wiki action.",
        "system/prompts/agent.md",
        "Use when an agent receives an ambiguous user request inside this workspace.",
    ),
    "llmw_ingest": (
        "Maintain source-backed wiki pages from an ingest packet.",
        "system/prompts/ingest.md",
        "Use after `llmw ingest packet <source_id>` before editing wiki pages.",
    ),
    "llmw_query": (
        "Answer questions using maintained wiki evidence first.",
        "system/prompts/query.md",
        "Use before answering user questions from the wiki.",
    ),
    "llmw_health_audit": (
        "Review wiki pages for semantic maintenance issues.",
        "system/prompts/health.md",
        "Use when running deeper maintenance review.",
    ),
}


def tool_definitions() -> list[dict[str, Any]]:
    return [
        _tool("llmw_context", "Return project state and recommended commands.", {}),
        _tool("llmw_next", "Return lightweight maintenance tasks.", {}),
        _tool(
            "llmw_search",
            "Search maintained wiki pages.",
            {
                "query": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 5},
                "deep": {"type": "boolean", "default": False},
            },
            required=["query"],
        ),
        _tool(
            "llmw_query",
            "Answer a question from wiki evidence using the configured LLM provider.",
            {
                "question": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5},
                "deep": {"type": "boolean", "default": False},
                "save": {"type": "boolean", "default": False},
                "max_page_chars": {"type": "integer", "minimum": 500, "default": 4000},
            },
            required=["question"],
        ),
        _tool(
            "llmw_maintain",
            "Run maintenance planning and optionally semantic audit.",
            {
                "audit": {"type": "boolean", "default": True},
                "save_plan": {"type": "boolean", "default": True},
            },
        ),
        _tool(
            "llmw_benchmark_search",
            "Run the built-in retrieval benchmark.",
            {
                "provider": {"type": "string", "default": "python"},
                "top_k": {"type": "integer", "minimum": 1, "maximum": 50, "default": 5},
            },
        ),
        _tool("llmw_health_check", "Run offline structural health checks.", {}),
        _tool(
            "llmw_plan",
            "Create a safe tool plan.",
            {
                "goal": {"type": "string"},
                "save": {"type": "boolean", "default": False},
                "preview": {"type": "boolean", "default": False},
            },
            required=["goal"],
        ),
        _tool(
            "llmw_apply",
            "Apply or dry-run a saved plan.",
            {
                "plan_file": {"type": "string"},
                "dry_run": {"type": "boolean", "default": True},
            },
            required=["plan_file"],
        ),
    ]


def resource_definitions(paths: WikiPaths) -> list[dict[str, Any]]:
    resources = [
        {"uri": uri, "name": name, "description": description, "mimeType": mime_type}
        for uri, name, description, mime_type, rel_path in STATIC_RESOURCES
        if not rel_path or (paths.root / rel_path).exists()
    ]
    for page in load_pages(paths, include_special=True):
        uri = f"llmw://wiki/page/{quote(page.rel_path, safe='/')}"
        resources.append(
            {
                "uri": uri,
                "name": page.title,
                "description": f"{page.page_type}: {page.rel_path}",
                "mimeType": "text/markdown",
            }
        )
    return resources


def resource_template_definitions() -> list[dict[str, Any]]:
    return [
        {
            "uriTemplate": "llmw://wiki/page/{path}",
            "name": "Wiki page by repository-relative path",
            "description": "Read a maintained wiki page such as wiki/concepts/agent-guardrails.md.",
            "mimeType": "text/markdown",
        }
    ]


def prompt_definitions() -> list[dict[str, Any]]:
    prompts = [
        {
            "name": name,
            "description": description,
            "arguments": [],
        }
        for name, (description, _path, _guidance) in PROMPT_FILES.items()
    ]
    prompts.append(
        {
            "name": "llmw_maintain_runbook",
            "description": "Run the standard agent maintenance loop safely.",
            "arguments": [
                {
                    "name": "goal",
                    "description": "Optional maintenance goal or user request.",
                    "required": False,
                }
            ],
        }
    )
    return prompts


def call_mcp_tool(name: str, arguments: dict[str, Any] | None, *, root: Path | str = ".") -> dict[str, Any]:
    args = arguments or {}
    paths = WikiPaths.from_root(root)
    if name == "llmw_context":
        return {"context": build_context(paths)}
    if name == "llmw_next":
        return {"tasks": build_next_tasks(paths)}
    if name == "llmw_search":
        query = _required_str(args, "query")
        deep = bool(args.get("deep", False))
        return _mcp_search_payload(paths, query, limit=int(args.get("limit", 5)), deep=deep)
    if name == "llmw_query":
        registry = load_provider_registry(paths, None)
        provider = registry.get(None)
        deep = bool(args.get("deep", False))
        config = load_config(paths)
        service = build_search_service(paths, config.qmd_collection, use_qmd=deep)
        result = run_query(
            paths,
            _required_str(args, "question"),
            provider=provider,
            limit=int(args.get("limit", 5)),
            deep=deep,
            save=bool(args.get("save", False)),
            max_page_chars=int(args.get("max_page_chars", 4000)),
            search_service=service,
        )
        return asdict(result)
    if name == "llmw_maintain":
        provider_config = None
        audit_warning = None
        if bool(args.get("audit", True)):
            try:
                provider_config = load_provider_registry(paths, None).get(None)
            except Exception as exc:
                audit_warning = str(exc)
        return {
            "maintenance": run_maintain(
                paths,
                provider=provider_config,
                audit=bool(args.get("audit", True)),
                save_plan_file=bool(args.get("save_plan", True)),
                audit_warning=audit_warning,
            )
        }
    if name == "llmw_benchmark_search":
        return {
            "benchmark": run_search_benchmark(
                paths,
                provider=str(args.get("provider") or "python"),
                top_k=int(args.get("top_k") or 5),
            )
        }
    if name == "llmw_health_check":
        return {"issues": [issue.model_dump() for issue in HealthChecker(paths).run()]}
    if name == "llmw_plan":
        plan = create_plan(paths, _required_str(args, "goal"))
        payload: dict[str, Any] = {"plan": plan.model_dump(), "saved_plan": None}
        if bool(args.get("save", False)):
            payload["saved_plan"] = save_plan(paths, plan)
        if bool(args.get("preview", False)):
            payload["preview"] = apply_plan(paths, plan, dry_run=True)
        return payload
    if name == "llmw_apply":
        plan_file = _resolve_mcp_plan_file(paths, _required_str(args, "plan_file"))
        plan = load_plan(plan_file)
        dry_run = bool(args.get("dry_run", True))
        provider = None
        if not dry_run and any(step.action in {"query_save", "health_audit_save"} for step in plan.steps):
            provider = load_provider_registry(paths, None).get(None)
        return apply_plan(paths, plan, provider=provider, dry_run=dry_run)
    raise ValueError(f"Unknown MCP tool: {name}")


def serve_mcp_stdio(
    paths: WikiPaths,
    *,
    input_stream: BinaryIO | None = None,
    output_stream: BinaryIO | None = None,
) -> None:
    input_stream = input_stream or sys.stdin.buffer
    output_stream = output_stream or sys.stdout.buffer
    while True:
        envelope = _read_message(input_stream)
        if envelope is None:
            break
        message, framing = envelope
        response = _handle_message(message, paths)
        if response is not None:
            _write_message(output_stream, response, framing=framing)


def _handle_message(message: dict[str, Any], paths: WikiPaths) -> dict[str, Any] | None:
    request_id = message.get("id")
    method = message.get("method")
    if request_id is None:
        return None
    try:
        if method == "initialize":
            return _result(
                request_id,
                {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
                    "serverInfo": {"name": "llm-wiki", "version": __version__},
                },
            )
        if method == "ping":
            return _result(request_id, {})
        if method == "resources/list":
            return _result(request_id, {"resources": resource_definitions(paths)})
        if method == "resources/read":
            params = message.get("params") or {}
            return _result(request_id, {"contents": [_read_resource(paths, _required_str(params, "uri"))]})
        if method in {"resources/templates/list", "resources/list_templates"}:
            return _result(request_id, {"resourceTemplates": resource_template_definitions()})
        if method == "prompts/list":
            return _result(request_id, {"prompts": prompt_definitions()})
        if method == "prompts/get":
            params = message.get("params") or {}
            prompt = _get_prompt(paths, _required_str(params, "name"), params.get("arguments") or {})
            return _result(request_id, prompt)
        if method == "tools/list":
            return _result(request_id, {"tools": tool_definitions()})
        if method == "tools/call":
            params = message.get("params") or {}
            tool_name = str(params.get("name") or "")
            arguments = params.get("arguments") or {}
            payload = call_mcp_tool(tool_name, arguments, root=paths.root)
            return _result(request_id, _tool_result(payload))
        return _error(request_id, -32601, f"Method not found: {method}")
    except Exception as exc:
        return _result(request_id, _tool_result({"ok": False, "error": {"code": "tool-failed", "message": str(exc)}}, is_error=True))


def _read_message(stream: BinaryIO) -> tuple[dict[str, Any], str] | None:
    headers: dict[str, str] = {}
    first_line = stream.readline()
    if first_line == b"":
        return None
    if first_line.lstrip().startswith(b"{"):
        return json.loads(first_line.decode("utf-8")), MCP_FRAMING_JSONL
    if first_line in {b"\r\n", b"\n"}:
        return None
    name, _, value = first_line.decode("ascii", errors="replace").partition(":")
    headers[name.lower()] = value.strip()
    while True:
        line = stream.readline()
        if line == b"":
            return None
        if line in {b"\r\n", b"\n"}:
            break
        name, _, value = line.decode("ascii", errors="replace").partition(":")
        headers[name.lower()] = value.strip()
    length = int(headers.get("content-length", "0"))
    if length <= 0:
        return None
    return json.loads(stream.read(length).decode("utf-8")), MCP_FRAMING_HEADERS


def _write_message(stream: BinaryIO, payload: dict[str, Any], *, framing: str = MCP_FRAMING_HEADERS) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    if framing == MCP_FRAMING_JSONL:
        stream.write(body + b"\n")
    else:
        stream.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body)
    stream.flush()


def _read_resource(paths: WikiPaths, uri: str) -> dict[str, Any]:
    if uri == "llmw://context":
        return {
            "uri": uri,
            "mimeType": "application/json",
            "text": json.dumps({"ok": True, "context": build_context(paths)}, indent=2, ensure_ascii=False),
        }
    for static_uri, _name, _description, mime_type, rel_path in STATIC_RESOURCES:
        if uri == static_uri:
            if not rel_path:
                break
            path = paths.root / rel_path
            return {"uri": uri, "mimeType": mime_type, "text": read_text(path)}
    prefix = "llmw://wiki/page/"
    if uri.startswith(prefix):
        rel_path = unquote(uri.removeprefix(prefix))
        path = _resolve_allowed_resource_path(paths, rel_path, allowed_roots=[paths.wiki])
        return {"uri": uri, "mimeType": "text/markdown", "text": read_text(path)}
    raise ValueError(f"Unknown MCP resource: {uri}")


def _get_prompt(paths: WikiPaths, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name in PROMPT_FILES:
        description, rel_path, guidance = PROMPT_FILES[name]
        text = read_text(paths.root / rel_path)
        return {
            "description": description,
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": f"{text.rstrip()}\n\nProject root: {paths.root}\nUsage guidance: {guidance}",
                    },
                }
            ],
        }
    if name == "llmw_maintain_runbook":
        goal = str(arguments.get("goal") or "maintain this LLM Wiki safely").strip()
        text = "\n".join(
            [
                f"Goal: {goal}",
                "",
                "Follow the LLM Wiki agent maintenance loop:",
                "1. Call `llmw_context` first.",
                "2. Call `llmw_next`/`llmw_maintain` for task discovery and planning.",
                "3. Use `llmw_search` before answering or editing.",
                "4. Use `deep: true` only when recall matters; a pre-warmed `llmw search-daemon start --deep` is reused automatically.",
                "5. For planned writes, create a plan and dry-run apply before real apply.",
                "6. Never rewrite `raw/`; keep wiki claims source-backed.",
                "7. Finish with `llmw_health_check` and, after search changes, `llmw_benchmark_search`.",
            ]
        )
        return {
            "description": "Run the standard agent maintenance loop safely.",
            "messages": [{"role": "user", "content": {"type": "text", "text": text}}],
        }
    raise ValueError(f"Unknown MCP prompt: {name}")


def _resolve_allowed_resource_path(paths: WikiPaths, rel_path: str, *, allowed_roots: list[Path]) -> Path:
    candidate = (paths.root / rel_path).resolve()
    if candidate.is_dir():
        raise ValueError(f"Resource path is a directory: {rel_path}")
    if not candidate.exists():
        raise ValueError(f"Resource path does not exist: {rel_path}")
    for allowed_root in allowed_roots:
        try:
            candidate.relative_to(allowed_root.resolve())
            return candidate
        except ValueError:
            continue
    display_path = relative_to_root(candidate, paths.root)
    raise ValueError(f"Resource path is outside allowed roots: {display_path}")


def _tool(name: str, description: str, properties: dict[str, Any], *, required: list[str] | None = None) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "inputSchema": {
            "type": "object",
            "properties": properties,
            "required": required or [],
            "additionalProperties": False,
        },
    }


def _resolve_mcp_plan_file(paths: WikiPaths, plan_file: str) -> Path:
    candidate = Path(plan_file)
    if candidate.is_absolute():
        target = candidate.resolve()
    else:
        target = (paths.root / candidate).resolve()
    plans_root = (paths.state / "plans").resolve()
    try:
        target.relative_to(plans_root)
    except ValueError as exc:
        raise ValueError("MCP apply may only read saved plans under .llmw/plans/") from exc
    if target.is_dir():
        raise ValueError(f"Plan file is a directory: {plan_file}")
    return target


def _tool_result(payload: dict[str, Any], *, is_error: bool = False) -> dict[str, Any]:
    if "ok" not in payload:
        payload = {"ok": True, **payload}
    return {
        "content": [{"type": "text", "text": json.dumps(payload, indent=2, ensure_ascii=False)}],
        "isError": is_error,
    }


def _mcp_search_payload(paths: WikiPaths, query: str, *, limit: int, deep: bool) -> dict[str, Any]:
    if deep:
        try:
            from llmw.search.daemon import query_deep_daemon_if_running

            daemon_payload = query_deep_daemon_if_running(paths, query, limit=limit)
        except Exception:
            daemon_payload = None
        if daemon_payload is not None:
            daemon_payload.pop("ok", None)
            daemon_payload["results"] = [
                _compact_search_result(result) for result in daemon_payload.get("results", [])
            ]
            return daemon_payload
        try:
            return _run_deep_search_subprocess(paths, query, limit=limit)
        except Exception as exc:
            payload = _run_fast_search(paths, query, limit=limit)
            payload["warning"] = f"deep search unavailable in MCP; returned fast fallback: {exc}"
            payload["requested_deep"] = True
            return payload
    return _run_fast_search(paths, query, limit=limit)


def _run_fast_search(paths: WikiPaths, query: str, *, limit: int) -> dict[str, Any]:
    config = load_config(paths)
    service = build_search_service(paths, config.qmd_collection, use_qmd=False)
    results, warning = service.search(query, limit=limit, deep=False)
    return {
        "warning": warning,
        "strategy": recommend_search_strategy(query, deep=False),
        "results": [_compact_search_result(result.model_dump()) for result in results],
    }


def _run_deep_search_subprocess(paths: WikiPaths, query: str, *, limit: int) -> dict[str, Any]:
    timeout = _mcp_deep_timeout_seconds()
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "llmw",
            "search",
            query,
            "--root",
            paths.root.as_posix(),
            "--limit",
            str(limit),
            "--deep",
            "--json",
        ],
        cwd=paths.root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    if proc.returncode != 0:
        message = (proc.stderr or proc.stdout or "deep search subprocess failed").strip()
        raise RuntimeError(_tail(message))
    payload = json.loads(proc.stdout)
    if payload.get("ok") is False:
        error = payload.get("error") or {}
        raise RuntimeError(str(error.get("message") or "deep search subprocess returned ok=false"))
    payload.pop("ok", None)
    payload["results"] = [_compact_search_result(result) for result in payload.get("results", [])]
    return payload


def _compact_search_result(result: dict[str, Any], *, max_snippet_chars: int = 500) -> dict[str, Any]:
    snippet = str(result.get("snippet") or "")
    if len(snippet) > max_snippet_chars:
        result = {**result, "snippet": snippet[:max_snippet_chars].rstrip() + "…"}
    return result


def _mcp_deep_timeout_seconds() -> float:
    raw = os.environ.get("LLMW_MCP_DEEP_TIMEOUT_SECONDS", "35").strip()
    try:
        value = float(raw)
    except ValueError:
        return 35
    return max(value, 1)


def _tail(value: str, *, max_chars: int = 1000) -> str:
    return value[-max_chars:]


def _result(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def _required_str(args: dict[str, Any], key: str) -> str:
    value = str(args.get(key) or "").strip()
    if not value:
        raise ValueError(f"Missing required argument: {key}")
    return value
