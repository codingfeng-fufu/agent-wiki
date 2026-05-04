from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_cli_source_to_search_contract_integration(tmp_path) -> None:
    project = tmp_path / "wiki-project"
    project.mkdir()

    _run_llmw(["init", "--root", project.as_posix()])
    source = project / "raw" / "inbox" / "integration-source.md"
    source.write_text("# Integration Source\n\nAgents use guardrails for safe tool calls.\n", encoding="utf-8")

    added = _json(_run_llmw(["source", "add", source.as_posix(), "--root", project.as_posix(), "--json"]))
    source_id = added["source"]["source_id"]

    packet = _json(_run_llmw(["ingest", "packet", source_id, "--root", project.as_posix(), "--json"]))
    assert packet["ok"] is True
    assert source_id in packet["packet"]

    source_page = project / "wiki" / "sources" / f"{source_id}.md"
    concept_page = project / "wiki" / "concepts" / "integration-guardrails.md"
    source_page.write_text(
        f"""---
title: Integration Source
type: source
status: draft
sources: ["{source_id}"]
tags: []
---

# Integration Source

Source-backed notes about [[Integration Guardrails]].
""",
        encoding="utf-8",
    )
    concept_page.write_text(
        f"""---
title: Integration Guardrails
type: concept
status: draft
sources: ["{source_id}"]
tags: []
---

# Integration Guardrails

Agents use guardrails to constrain tool calls and unsafe actions. See [[Integration Source]].
""",
        encoding="utf-8",
    )

    recorded = _json(
        _run_llmw(
            [
                "ingest",
                "record",
                source_id,
                "--root",
                project.as_posix(),
                "--page",
                f"wiki/sources/{source_id}.md",
                "--page",
                "wiki/concepts/integration-guardrails.md",
                "--json",
            ]
        )
    )
    assert recorded["ok"] is True

    context = _json(_run_llmw(["context", "--root", project.as_posix(), "--json"]))
    assert context["context"]["sources"]["statuses"] == {"ingested": 1}
    assert context["context"]["health"]["errors"] == 0

    health = _json(_run_llmw(["health", "check", "--root", project.as_posix(), "--json"]))
    assert health["ok"] is True
    assert not [issue for issue in health["issues"] if issue["severity"] == "error"]

    results = _json(_run_llmw(["search", "guardrails tool calls", "--root", project.as_posix(), "--limit", "3", "--json"]))
    assert results["ok"] is True
    assert results["results"][0]["path"] == "wiki/concepts/integration-guardrails.md"

    maintenance = _json(
        _run_llmw(["maintain", "--root", project.as_posix(), "--no-audit", "--no-save-plan", "--json"])
    )
    assert maintenance["ok"] is True
    assert maintenance["maintenance"]["health"]["errors"] == 0


def test_cli_safe_apply_contract_integration(tmp_path) -> None:
    project = tmp_path / "apply-project"
    project.mkdir()
    _run_llmw(["init", "--root", project.as_posix()])
    page = project / "wiki" / "concepts" / "safe-apply.md"
    page.write_text("# Safe Apply\n\nOld integration text.\n", encoding="utf-8")
    plan_path = project / "patch-plan.json"
    plan_path.write_text(
        json.dumps(
            {
                "plan_id": "plan-safe-apply-integration",
                "goal": "patch a wiki page",
                "created_at": "2026-01-01T00:00:00Z",
                "steps": [
                    {
                        "id": "step-1",
                        "action": "wiki_patch",
                        "args": {
                            "path": "wiki/concepts/safe-apply.md",
                            "old": "Old integration text.",
                            "new": "New integration text.",
                        },
                        "writes": ["wiki/concepts/safe-apply.md"],
                        "risk": "low",
                    }
                ],
                "writes": ["wiki/concepts/safe-apply.md"],
                "requires_confirmation": True,
            }
        ),
        encoding="utf-8",
    )

    preview = _json(_run_llmw(["apply", plan_path.as_posix(), "--root", project.as_posix(), "--dry-run", "--json"]))
    assert preview["ok"] is True
    assert preview["dry_run"] is True
    assert "+New integration text." in preview["results"][0]["output"]["diff"]
    assert "Old integration text." in page.read_text(encoding="utf-8")

    applied = _json(_run_llmw(["apply", plan_path.as_posix(), "--root", project.as_posix(), "--json"]))
    assert applied["ok"] is True
    assert applied["applied"] == 1
    assert "New integration text." in page.read_text(encoding="utf-8")

    bad_plan = project / "bad-plan.json"
    bad_plan.write_text(
        json.dumps(
            {
                "plan_id": "plan-bad-apply-integration",
                "goal": "patch raw",
                "created_at": "2026-01-01T00:00:00Z",
                "steps": [
                    {
                        "id": "step-1",
                        "action": "wiki_patch",
                        "args": {"path": "raw/inbox/source.md", "create": True, "new": "# Bad"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    rejected = _run_llmw(
        ["apply", bad_plan.as_posix(), "--root", project.as_posix(), "--dry-run", "--json"],
        check=False,
    )
    payload = _json(rejected)
    assert rejected.returncode == 1
    assert payload["ok"] is False
    assert "wiki/ or system/" in payload["error"]["message"]


def test_search_daemon_cli_integration(tmp_path) -> None:
    project = tmp_path / "daemon-project"
    project.mkdir()
    _run_llmw(["init", "--root", project.as_posix()])
    page = project / "wiki" / "concepts" / "daemon-search.md"
    page.write_text("# Daemon Search\n\nWarm daemon integration retrieval works.\n", encoding="utf-8")

    env = {"LLMW_DISABLE_QMD": "1"}
    try:
        started = _json(
            _run_llmw(["search-daemon", "start", "--root", project.as_posix(), "--limit", "2", "--json"], env=env)
        )
        assert started["daemon"]["running"] is True

        status = _json(_run_llmw(["search-daemon", "status", "--root", project.as_posix(), "--json"], env=env))
        assert status["daemon"]["running"] is True

        results = _json(
            _run_llmw(
                ["search-daemon", "query", "daemon integration retrieval", "--root", project.as_posix(), "--json"],
                env=env,
            )
        )
        assert results["ok"] is True
        assert results["results"][0]["path"] == "wiki/concepts/daemon-search.md"
    finally:
        _run_llmw(["search-daemon", "stop", "--root", project.as_posix(), "--json"], env=env, check=False)


def test_mcp_stdio_cli_integration(tmp_path) -> None:
    project = tmp_path / "mcp-project"
    project.mkdir()
    _run_llmw(["init", "--root", project.as_posix()])
    page = project / "wiki" / "concepts" / "mcp-contract.md"
    page.write_text("# MCP Contract\n\nMCP integration search works.\n", encoding="utf-8")

    process = subprocess.Popen(
        [sys.executable, "-m", "llmw", "mcp", "--root", project.as_posix()],
        cwd=PROJECT_ROOT,
        env=_env(),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert process.stdin is not None
    assert process.stdout is not None
    try:
        _write_mcp(
            process.stdin,
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}},
        )
        initialized = _read_mcp(process.stdout)
        assert initialized["result"]["serverInfo"]["name"] == "llm-wiki"

        _write_mcp(process.stdin, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        listed = _read_mcp(process.stdout)
        assert any(tool["name"] == "llmw_search" for tool in listed["result"]["tools"])

        _write_mcp(
            process.stdin,
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "llmw_search", "arguments": {"query": "MCP integration search", "limit": 2}},
            },
        )
        called = _read_mcp(process.stdout)
        content = json.loads(called["result"]["content"][0]["text"])
        assert content["ok"] is True
        assert content["results"][0]["path"] == "wiki/concepts/mcp-contract.md"
    finally:
        process.stdin.close()
        process.terminate()
        process.wait(timeout=10)


def test_mcp_jsonl_cli_integration(tmp_path) -> None:
    project = tmp_path / "mcp-jsonl-project"
    project.mkdir()
    _run_llmw(["init", "--root", project.as_posix()])

    process = subprocess.Popen(
        [sys.executable, "-m", "llmw", "mcp", "--root", project.as_posix()],
        cwd=PROJECT_ROOT,
        env=_env(),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert process.stdin is not None
    assert process.stdout is not None
    try:
        _write_mcp_jsonl(
            process.stdin,
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
        )
        initialized = _read_mcp_jsonl(process.stdout)
        assert initialized["result"]["serverInfo"]["name"] == "llm-wiki"

        _write_mcp_jsonl(process.stdin, {"jsonrpc": "2.0", "method": "notifications/initialized"})

        _write_mcp_jsonl(process.stdin, {"jsonrpc": "2.0", "id": 2, "method": "resources/list"})
        resources = _read_mcp_jsonl(process.stdout)
        assert any(resource["uri"] == "llmw://context" for resource in resources["result"]["resources"])

        _write_mcp_jsonl(process.stdin, {"jsonrpc": "2.0", "id": 3, "method": "tools/list"})
        listed = _read_mcp_jsonl(process.stdout)
        assert any(tool["name"] == "llmw_context" for tool in listed["result"]["tools"])
    finally:
        process.stdin.close()
        process.terminate()
        process.wait(timeout=10)


def _run_llmw(
    args: list[str],
    *,
    env: dict[str, str] | None = None,
    check: bool = True,
    timeout: int = 30,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, "-m", "llmw", *args],
        cwd=PROJECT_ROOT,
        env=_env(env),
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    if check and result.returncode != 0:
        raise AssertionError(
            f"llmw command failed: {' '.join(args)}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def _json(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"stdout was not JSON:\n{result.stdout}\nstderr:\n{result.stderr}") from exc


def _env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = os.environ.copy()
    src = (PROJECT_ROOT / "src").as_posix()
    current = env.get("PYTHONPATH")
    env["PYTHONPATH"] = f"{src}{os.pathsep}{current}" if current else src
    if extra:
        env.update(extra)
    return env


def _write_mcp(stream, payload: dict[str, Any]) -> None:
    body = json.dumps(payload).encode("utf-8")
    stream.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body)
    stream.flush()


def _read_mcp(stream) -> dict[str, Any]:
    headers: dict[str, str] = {}
    while True:
        line = stream.readline()
        if line in {b"\r\n", b"\n"}:
            break
        if line == b"":
            raise AssertionError("MCP server closed stdout")
        key, _, value = line.decode("ascii").partition(":")
        headers[key.lower()] = value.strip()
    length = int(headers["content-length"])
    return json.loads(stream.read(length).decode("utf-8"))


def _write_mcp_jsonl(stream, payload: dict[str, Any]) -> None:
    stream.write(json.dumps(payload).encode("utf-8") + b"\n")
    stream.flush()


def _read_mcp_jsonl(stream) -> dict[str, Any]:
    line = stream.readline()
    if line == b"":
        raise AssertionError("MCP server closed stdout")
    return json.loads(line.decode("utf-8"))
