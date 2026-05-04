from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tomllib
from pathlib import Path
from typing import Any

from llmw.core.fs import utc_now_iso
from llmw.core.paths import WikiPaths


DEFAULT_SERVER_NAME = "llm_wiki"


def expected_codex_command(paths: WikiPaths) -> tuple[str, list[str]]:
    local_llmw = paths.root / ".venv" / "bin" / "llmw"
    command = local_llmw.as_posix() if local_llmw.exists() else "llmw"
    return command, ["mcp", "--root", paths.root.as_posix()]


def codex_config_path(home: Path | None = None) -> Path:
    return (home or Path.home()) / ".codex" / "config.toml"


def codex_config_snippet(paths: WikiPaths, *, server_name: str = DEFAULT_SERVER_NAME) -> str:
    command, args = expected_codex_command(paths)
    encoded_args = ", ".join(json.dumps(arg) for arg in args)
    return "\n".join(
        [
            f"[mcp_servers.{server_name}]",
            f"command = {json.dumps(command)}",
            f"args = [{encoded_args}]",
            'default_tools_approval_mode = "approve"',
            "",
        ]
    )


def codex_status(paths: WikiPaths, *, server_name: str = DEFAULT_SERVER_NAME) -> dict[str, Any]:
    command, args = expected_codex_command(paths)
    codex_bin = shutil.which("codex")
    config_path = codex_config_path()
    config = _read_codex_config(config_path)
    configured_server = (config.get("mcp_servers") or {}).get(server_name) if isinstance(config, dict) else None
    approval_mode = configured_server.get("default_tools_approval_mode") if isinstance(configured_server, dict) else None
    codex_record = _codex_mcp_get(server_name) if codex_bin else None
    transport = (codex_record or {}).get("transport") or {}
    configured = codex_record is not None
    command_matches = transport.get("command") == command
    args_match = transport.get("args") == args
    approval_matches = approval_mode == "approve"
    return {
        "codex_found": codex_bin is not None,
        "codex_path": codex_bin,
        "config_path": config_path.as_posix(),
        "server_name": server_name,
        "configured": configured,
        "enabled": bool((codex_record or {}).get("enabled")) if configured else False,
        "command": transport.get("command"),
        "args": transport.get("args"),
        "expected_command": command,
        "expected_args": args,
        "command_matches": command_matches,
        "args_match": args_match,
        "approval_mode": approval_mode,
        "approval_matches": approval_matches,
        "ready": bool(codex_bin and configured and command_matches and args_match and approval_matches),
        "config_snippet": codex_config_snippet(paths, server_name=server_name),
        "install_command": f"llmw integration codex install --server-name {server_name} --root {paths.root.as_posix()}",
        "checked_at": utc_now_iso(),
    }


def install_codex_mcp(paths: WikiPaths, *, server_name: str = DEFAULT_SERVER_NAME, home: Path | None = None) -> dict[str, Any]:
    config_path = codex_config_path(home)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    existing = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    backup_path = None
    if config_path.exists():
        backup_path = config_path.with_suffix(config_path.suffix + f".llmw-backup-{_timestamp()}")
        backup_path.write_text(existing, encoding="utf-8")
    snippet = codex_config_snippet(paths, server_name=server_name)
    updated = _replace_or_append_server_block(existing, server_name=server_name, block=snippet)
    config_path.write_text(updated, encoding="utf-8")
    return {
        "server_name": server_name,
        "config_path": config_path.as_posix(),
        "backup_path": backup_path.as_posix() if backup_path else None,
        "config_snippet": snippet,
    }


def test_codex_mcp(paths: WikiPaths, *, server_name: str = DEFAULT_SERVER_NAME, timeout: float = 15) -> dict[str, Any]:
    status = codex_status(paths, server_name=server_name)
    if not status["codex_found"]:
        return {"ok": False, "status": status, "error": "codex executable not found"}
    if not status["configured"]:
        return {"ok": False, "status": status, "error": f"codex MCP server not configured: {server_name}"}
    probe = probe_mcp_command([status["command"], *status["args"]], cwd=paths.root, timeout=timeout)
    return {"ok": probe["ok"], "status": status, "probe": probe}


def probe_mcp_command(command: list[str], *, cwd: Path, timeout: float = 15) -> dict[str, Any]:
    env = os.environ.copy()
    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert process.stdin is not None
    assert process.stdout is not None
    try:
        _write_jsonl(process.stdin, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}})
        initialized = _read_jsonl(process.stdout, timeout=timeout)
        _write_jsonl(process.stdin, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        _write_jsonl(process.stdin, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        tools = _read_jsonl(process.stdout, timeout=timeout)
        _write_jsonl(process.stdin, {"jsonrpc": "2.0", "id": 3, "method": "resources/read", "params": {"uri": "llmw://context"}})
        context = _read_jsonl(process.stdout, timeout=timeout)
        tool_names = [tool.get("name") for tool in tools.get("result", {}).get("tools", [])]
        context_text = context.get("result", {}).get("contents", [{}])[0].get("text", "")
        context_payload = json.loads(context_text) if context_text else {}
        return {
            "ok": initialized.get("result", {}).get("serverInfo", {}).get("name") == "llm-wiki"
            and "llmw_context" in tool_names
            and context_payload.get("ok") is True,
            "server_info": initialized.get("result", {}).get("serverInfo"),
            "tools_count": len(tool_names),
            "has_llmw_context": "llmw_context" in tool_names,
            "wiki_pages": ((context_payload.get("context") or {}).get("wiki") or {}).get("pages"),
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    finally:
        try:
            process.stdin.close()
        except Exception:
            pass
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


def _read_codex_config(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        return {}
    try:
        return tomllib.loads(config_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return {}


def _codex_mcp_get(server_name: str) -> dict[str, Any] | None:
    try:
        proc = subprocess.run(["codex", "mcp", "get", server_name, "--json"], text=True, capture_output=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def _replace_or_append_server_block(existing: str, *, server_name: str, block: str) -> str:
    pattern = re.compile(rf"(?ms)^\[mcp_servers\.{re.escape(server_name)}\]\n.*?(?=^\[|\Z)")
    if pattern.search(existing):
        updated = pattern.sub(block, existing)
    else:
        separator = "" if not existing or existing.endswith("\n") else "\n"
        updated = f"{existing}{separator}\n{block}" if existing else block
    return updated if updated.endswith("\n") else f"{updated}\n"


def _timestamp() -> str:
    return utc_now_iso().replace("-", "").replace(":", "").removesuffix("Z")


def _write_jsonl(stream: Any, payload: dict[str, Any]) -> None:
    stream.write(json.dumps(payload) + "\n")
    stream.flush()


def _read_jsonl(stream: Any, *, timeout: float) -> dict[str, Any]:
    import selectors

    selector = selectors.DefaultSelector()
    selector.register(stream, selectors.EVENT_READ)
    try:
        if not selector.select(timeout):
            raise TimeoutError("timed out waiting for MCP response")
        line = stream.readline()
    finally:
        selector.close()
    if not line:
        raise RuntimeError("MCP server closed stdout")
    return json.loads(line)
