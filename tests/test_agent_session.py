from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from llmw.agent.session import AgentAction, AgentSession, route_user_input
from llmw.cli.main import app
from llmw.core.config import ensure_project_dirs, write_config
from llmw.core.models import SearchResult
from llmw.core.paths import WikiPaths
from llmw.llm.client import ChatResult
from llmw.llm.config import ProviderConfig
from llmw.llm.query import QueryRunResult
from llmw.sources.registry import load_registry


runner = CliRunner()


class FakePlannerClient:
    def __init__(self, provider: ProviderConfig):
        self.provider = provider

    def chat(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        top_p: float | None = None,
        max_tokens: int | None = None,
    ) -> ChatResult:
        return ChatResult(content='{"action":"health_check"}', model="fake-planner")


def test_route_rules_cover_common_natural_language(tmp_path) -> None:
    paths = WikiPaths.from_root(tmp_path)

    assert route_user_input(paths, "/status").action == "status"
    assert route_user_input(paths, "搜索 guardrails").action == "search"
    assert route_user_input(paths, "how should agents use guardrails?").action == "query"
    assert route_user_input(paths, "语义健康审计").action == "health_audit"
    assert route_user_input(paths, "登记全部资料").action == "source_register"


def test_route_uses_llm_planner_for_unclassified_requests(tmp_path) -> None:
    paths = _agent_project(tmp_path, include_agent_usage=True)

    action = route_user_input(
        paths,
        "please maintain this knowledge base",
        provider=_provider(include_agent_usage=True),
        client_factory=FakePlannerClient,
    )

    assert action == AgentAction("health_check")


def test_agent_cli_status_smoke(tmp_path) -> None:
    result = runner.invoke(
        app,
        ["agent", "--root", str(tmp_path), "--no-session-log"],
        input="/status\n/exit\n",
    )

    assert result.exit_code == 0
    assert "LLM Wiki agent ready" in result.output
    assert "Wiki pages:" in result.output
    assert "Bye." in result.output


def test_agent_register_requires_confirmation(tmp_path) -> None:
    paths = _agent_project(tmp_path)
    source = paths.raw_inbox / "note.md"
    source.write_text("# Note\n\nNew source.", encoding="utf-8")
    inputs = _inputs(["/register all", "no", "/exit"])
    output: list[str] = []

    AgentSession(paths, input_func=inputs, output_func=output.append, session_log=False).run()

    assert load_registry(paths).sources == {}
    assert any("Skipped registration" in line for line in output)


def test_agent_query_uses_runner_and_session_log_is_summary_only(tmp_path) -> None:
    paths = _agent_project(tmp_path)
    output: list[str] = []

    def fake_query_runner(*args, **kwargs):
        return QueryRunResult(
            question=args[1],
            answer="SECRET_ANSWER",
            pages=[],
            model="fake-model",
            usage={"total_tokens": 1},
        )

    AgentSession(
        paths,
        input_func=_inputs(["what is guardrails?", "/exit"]),
        output_func=output.append,
        query_runner=fake_query_runner,
    ).run()

    logs = list((paths.state / "sessions").glob("*.jsonl"))
    assert logs
    assert any("SECRET_ANSWER" in line for line in output)
    assert "SECRET_ANSWER" not in logs[0].read_text(encoding="utf-8")


def test_agent_search_prints_results(tmp_path) -> None:
    paths = _agent_project(tmp_path)
    page = paths.wiki_concepts / "guardrails.md"
    page.write_text("# Guardrails\n\nAgents use guardrails for safety.", encoding="utf-8")
    output: list[str] = []

    AgentSession(
        paths,
        input_func=_inputs(["/search how should agents use guardrails?", "/exit"]),
        output_func=output.append,
        session_log=False,
    ).run()

    assert any("Guardrails" in line for line in output)


def _agent_project(tmp_path: Path, *, include_agent_usage: bool = False) -> WikiPaths:
    paths = WikiPaths.from_root(tmp_path)
    ensure_project_dirs(paths)
    write_config(paths)
    paths.log_path.write_text("# Log\n\n", encoding="utf-8")
    (paths.system / "prompts").mkdir(parents=True, exist_ok=True)
    (paths.system / "prompts" / "query.md").write_text("Use wiki evidence.", encoding="utf-8")
    (paths.system / "prompts" / "agent.md").write_text("Route safely.", encoding="utf-8")
    (paths.system / "providers").mkdir(parents=True, exist_ok=True)
    usage = {
        "query": {
            "system_prompt_file": "system/prompts/query.md",
            "temperature": 0.1,
            "max_tokens": 512,
        }
    }
    if include_agent_usage:
        usage["agent"] = {
            "system_prompt_file": "system/prompts/agent.md",
            "temperature": 0.0,
            "max_tokens": 128,
        }
    (paths.system / "providers" / "qwen-plus.json").write_text(
        json.dumps(
            {
                "default_provider": "fake",
                "providers": {
                    "fake": {
                        "type": "openai_compatible",
                        "model": "fake-model",
                        "base_url": "https://example.invalid/v1",
                        "api_key_env": "FAKE_API_KEY",
                        "usage": usage,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    return paths


def _provider(*, include_agent_usage: bool = False) -> ProviderConfig:
    usage = {
        "query": {
            "system_prompt_file": "system/prompts/query.md",
            "temperature": 0.1,
            "max_tokens": 512,
        }
    }
    if include_agent_usage:
        usage["agent"] = {
            "system_prompt_file": "system/prompts/agent.md",
            "temperature": 0.0,
            "max_tokens": 128,
        }
    return ProviderConfig(
        type="openai_compatible",
        model="fake-model",
        base_url="https://example.invalid/v1",
        api_key_env="FAKE_API_KEY",
        usage=usage,
    )


def _inputs(values: list[str]):
    iterator = iter(values)

    def read(prompt: str) -> str:
        return next(iterator)

    return read
