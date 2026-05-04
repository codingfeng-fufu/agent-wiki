from __future__ import annotations

import io
import json
from llmw.core.config import ensure_project_dirs, write_config
from llmw.core.paths import WikiPaths
from llmw.mcp import server as mcp_server
from llmw.mcp.server import call_mcp_tool, serve_mcp_stdio


def test_mcp_context_tool_returns_project_state(tmp_path) -> None:
    paths = _project(tmp_path)
    (paths.wiki_concepts / "alpha.md").write_text("# Alpha\n\nConcept.", encoding="utf-8")

    payload = call_mcp_tool("llmw_context", {}, root=tmp_path)

    assert payload["context"]["root"] == tmp_path.as_posix()
    assert payload["context"]["wiki"]["pages"] == 1


def test_mcp_stdio_lists_tools(tmp_path) -> None:
    paths = _project(tmp_path)
    request = _message({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    output = io.BytesIO()

    serve_mcp_stdio(paths, input_stream=io.BytesIO(request), output_stream=output)

    response = _read_message(output.getvalue())
    tools = response["result"]["tools"]
    assert response["id"] == 1
    assert any(tool["name"] == "llmw_search" for tool in tools)
    assert any(tool["name"] == "llmw_apply" for tool in tools)


def test_mcp_stdio_supports_jsonl_framing(tmp_path) -> None:
    paths = _project(tmp_path)
    request = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize"}).encode("utf-8") + b"\n"
    output = io.BytesIO()

    serve_mcp_stdio(paths, input_stream=io.BytesIO(request), output_stream=output)

    response = json.loads(output.getvalue().decode("utf-8"))
    assert response["id"] == 1
    assert response["result"]["serverInfo"]["name"] == "llm-wiki"


def test_mcp_stdio_returns_resources_templates_and_prompts(tmp_path) -> None:
    paths = _project(tmp_path)
    (paths.wiki_concepts / "guardrails.md").write_text("# Guardrails\n\nAgent guardrails.", encoding="utf-8")
    request = b"".join(
        json.dumps({"jsonrpc": "2.0", "id": index, "method": method}).encode("utf-8") + b"\n"
        for index, method in enumerate(
            ["resources/list", "resources/templates/list", "prompts/list"],
            start=1,
        )
    )
    output = io.BytesIO()

    serve_mcp_stdio(paths, input_stream=io.BytesIO(request), output_stream=output)

    responses = [json.loads(line) for line in output.getvalue().splitlines()]
    assert any(resource["uri"] == "llmw://context" for resource in responses[0]["result"]["resources"])
    assert any(resource["uri"] == "llmw://wiki/page/wiki/concepts/guardrails.md" for resource in responses[0]["result"]["resources"])
    assert responses[1]["result"]["resourceTemplates"][0]["uriTemplate"] == "llmw://wiki/page/{path}"
    assert any(prompt["name"] == "llmw_maintain_runbook" for prompt in responses[2]["result"]["prompts"])


def test_mcp_stdio_reads_resource_and_prompt(tmp_path) -> None:
    paths = _project(tmp_path)
    (paths.wiki_concepts / "guardrails.md").write_text("# Guardrails\n\nAgent guardrails.", encoding="utf-8")
    request = b"".join(
        json.dumps(payload).encode("utf-8") + b"\n"
        for payload in [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "resources/read",
                "params": {"uri": "llmw://wiki/page/wiki/concepts/guardrails.md"},
            },
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "prompts/get",
                "params": {"name": "llmw_maintain_runbook", "arguments": {"goal": "verify MCP"}},
            },
        ]
    )
    output = io.BytesIO()

    serve_mcp_stdio(paths, input_stream=io.BytesIO(request), output_stream=output)

    responses = [json.loads(line) for line in output.getvalue().splitlines()]
    assert responses[0]["result"]["contents"][0]["text"].startswith("# Guardrails")
    assert "verify MCP" in responses[1]["result"]["messages"][0]["content"]["text"]


def test_mcp_search_tool_returns_json_text_content(tmp_path) -> None:
    paths = _project(tmp_path)
    (paths.wiki_concepts / "guardrails.md").write_text("# Guardrails\n\nAgent guardrails.", encoding="utf-8")

    request = _message(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "llmw_search", "arguments": {"query": "guardrails", "root": tmp_path.as_posix()}},
        }
    )
    output = io.BytesIO()

    serve_mcp_stdio(paths, input_stream=io.BytesIO(request), output_stream=output)

    response = _read_message(output.getvalue())
    content = json.loads(response["result"]["content"][0]["text"])
    assert content["ok"] is True
    assert content["results"][0]["path"] == "wiki/concepts/guardrails.md"


def test_mcp_deep_search_times_out_to_fast_fallback(tmp_path, monkeypatch) -> None:
    paths = _project(tmp_path)
    (paths.wiki_concepts / "guardrails.md").write_text("# Guardrails\n\nAgent guardrails.", encoding="utf-8")

    def timeout_deep(*args, **kwargs):
        raise TimeoutError("deep timeout")

    monkeypatch.setattr(mcp_server, "_run_deep_search_subprocess", timeout_deep)

    payload = call_mcp_tool(
        "llmw_search",
        {"query": "how should agents use guardrails?", "limit": 3, "deep": True},
        root=tmp_path,
    )

    assert payload["requested_deep"] is True
    assert "fast fallback" in payload["warning"]
    assert payload["strategy"]["mode"] == "fast"
    assert payload["results"][0]["path"] == "wiki/concepts/guardrails.md"


def test_mcp_deep_search_prefers_running_daemon(tmp_path, monkeypatch) -> None:
    paths = _project(tmp_path)
    (paths.wiki_concepts / "guardrails.md").write_text("# Guardrails\n\nAgent guardrails.", encoding="utf-8")

    def fake_daemon(paths_arg, query, *, limit):
        assert paths_arg.root == paths.root
        assert query == "how should agents use guardrails?"
        assert limit == 3
        return {
            "ok": True,
            "served_by": "search-daemon",
            "warning": None,
            "strategy": {"mode": "deep", "deep_recommended": True},
            "results": [
                {
                    "path": "wiki/concepts/guardrails.md",
                    "title": "Guardrails",
                    "snippet": "Agent guardrails.",
                    "score": 1.0,
                    "provider": "qmd",
                }
            ],
        }

    def fail_subprocess(*args, **kwargs):
        raise AssertionError("subprocess should not run when daemon is available")

    monkeypatch.setattr("llmw.search.daemon.query_deep_daemon_if_running", fake_daemon)
    monkeypatch.setattr(mcp_server, "_run_deep_search_subprocess", fail_subprocess)

    payload = call_mcp_tool(
        "llmw_search",
        {"query": "how should agents use guardrails?", "limit": 3, "deep": True},
        root=tmp_path,
    )

    assert payload["served_by"] == "search-daemon"
    assert payload["strategy"]["mode"] == "deep"
    assert payload["results"][0]["path"] == "wiki/concepts/guardrails.md"


def _project(tmp_path) -> WikiPaths:
    paths = WikiPaths.from_root(tmp_path)
    ensure_project_dirs(paths)
    write_config(paths)
    paths.log_path.write_text("# Log\n\n", encoding="utf-8")
    return paths


def _message(payload: dict) -> bytes:
    body = json.dumps(payload).encode("utf-8")
    return f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body


def _read_message(raw: bytes) -> dict:
    _, _, body = raw.partition(b"\r\n\r\n")
    return json.loads(body.decode("utf-8"))
