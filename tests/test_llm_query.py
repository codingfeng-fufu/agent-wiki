from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from llmw.cli import main as cli_main
from llmw.cli.main import app
from llmw.core.config import ensure_project_dirs, write_config
from llmw.core.models import SearchResult
from llmw.core.paths import WikiPaths
from llmw.health.checks import HealthChecker
from llmw.llm.client import ChatResult
from llmw.llm.config import ProviderConfig
from llmw.llm.query import QueryRunResult, build_query_prompt, run_query
from llmw.wiki.index import index_is_current


runner = CliRunner()


class FakeSearchService:
    def __init__(self, results: list[SearchResult], warning: str | None = None):
        self.results = results
        self.warning = warning
        self.calls: list[tuple[str, int, bool]] = []

    def search(self, query: str, *, limit: int = 10, deep: bool = False):
        self.calls.append((query, limit, deep))
        return self.results, self.warning


class FakeClient:
    prompts: list[tuple[str, str]] = []

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
        self.prompts.append((system_prompt, user_prompt))
        return ChatResult(
            content="Use guardrails before tool calls. Cite Evidence Source and source-1.",
            model="fake-model",
            usage={"total_tokens": 12},
        )


def test_run_query_reads_evidence_and_calls_provider(tmp_path) -> None:
    paths = _query_project(tmp_path)
    _write_page(paths, "wiki/concepts/evidence.md", title="Evidence Source", source_id="source-1")
    search = FakeSearchService([SearchResult(path="wiki/concepts/evidence.md", title="Evidence Source", provider="fake")])
    FakeClient.prompts = []

    result = run_query(
        paths,
        "How should agents use guardrails?",
        provider=_provider(),
        search_service=search,
        client_factory=FakeClient,
    )

    assert result.answer.startswith("Use guardrails")
    assert result.model == "fake-model"
    assert result.usage == {"total_tokens": 12}
    assert result.pages[0].path == "wiki/concepts/evidence.md"
    assert result.pages[0].sources == ["source-1"]
    assert search.calls == [("How should agents use guardrails?", 15, False)]
    assert "Evidence Source" in FakeClient.prompts[0][1]
    assert "source-1" in FakeClient.prompts[0][1]


def test_run_query_save_writes_output_updates_log_and_index(tmp_path) -> None:
    paths = _query_project(tmp_path)
    _write_page(paths, "wiki/concepts/evidence.md", title="Evidence Source", source_id="source-1")
    search = FakeSearchService([SearchResult(path="wiki/concepts/evidence.md", title="Evidence Source", provider="fake")])

    result = run_query(
        paths,
        "How should agents use guardrails?",
        provider=_provider(),
        search_service=search,
        client_factory=FakeClient,
        save=True,
    )

    assert result.saved_page is not None
    saved = paths.root / result.saved_page
    assert saved.exists()
    assert "type: output" in saved.read_text(encoding="utf-8")
    assert "[[Evidence Source]]" in saved.read_text(encoding="utf-8")
    assert "Query | How should agents use guardrails" in paths.log_path.read_text(encoding="utf-8")
    assert index_is_current(paths)
    assert not [issue for issue in HealthChecker(paths).run() if issue.severity == "error"]


def test_run_query_reports_no_search_results(tmp_path) -> None:
    paths = _query_project(tmp_path)

    with pytest.raises(ValueError, match="No relevant wiki pages"):
        run_query(
            paths,
            "missing topic",
            provider=_provider(),
            search_service=FakeSearchService([]),
            client_factory=FakeClient,
        )


def test_build_query_prompt_requires_evidence_only(tmp_path) -> None:
    paths = _query_project(tmp_path)
    _write_page(paths, "wiki/concepts/evidence.md", title="Evidence Source", source_id="source-1")
    search = FakeSearchService([SearchResult(path="wiki/concepts/evidence.md", title="Evidence Source", provider="fake")])
    result = run_query(
        paths,
        "What is supported?",
        provider=_provider(),
        search_service=search,
        client_factory=FakeClient,
    )

    prompt = build_query_prompt(result.question, result.pages)

    assert "using only the maintained wiki evidence" in prompt
    assert "If the evidence is insufficient" in prompt
    assert "Evidence Source" in prompt


def test_query_cli_json_wires_command(monkeypatch, tmp_path) -> None:
    paths = _query_project(tmp_path)

    def fake_run_query(*args, **kwargs):
        assert args[0].root == paths.root
        assert args[1] == "What is tool safety?"
        assert kwargs["limit"] == 3
        return QueryRunResult(
            question="What is tool safety?",
            answer="Tool safety constrains actions.",
            pages=[],
            model="fake-model",
            usage={"total_tokens": 1},
            warning=None,
            saved_page=None,
        )

    monkeypatch.setattr(cli_main, "run_query", fake_run_query)

    result = runner.invoke(
        app,
        ["query", "What is tool safety?", "--root", str(tmp_path), "--limit", "3", "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["answer"] == "Tool safety constrains actions."
    assert payload["model"] == "fake-model"


def test_query_cli_deep_uses_running_daemon_payload(monkeypatch, tmp_path) -> None:
    paths = _query_project(tmp_path)
    seen = {}

    def fake_daemon(paths_arg, question, *, limit):
        assert paths_arg.root == paths.root
        assert question == "What is tool safety?"
        assert limit == 9
        return {
            "ok": True,
            "served_by": "search-daemon",
            "warning": None,
            "results": [
                {
                    "path": "wiki/concepts/evidence.md",
                    "title": "Evidence Source",
                    "score": 1.0,
                    "snippet": "Tool safety evidence.",
                    "provider": "qmd",
                }
            ],
        }

    def fake_run_query(*args, **kwargs):
        service = kwargs["search_service"]
        results, warning = service.search("ignored", limit=3, deep=True)
        seen["results"] = results
        seen["warning"] = warning
        return QueryRunResult(
            question=args[1],
            answer="Tool safety constrains actions.",
            pages=[],
            model="fake-model",
        )

    monkeypatch.setattr("llmw.search.daemon.query_deep_daemon_if_running", fake_daemon)
    monkeypatch.setattr(cli_main, "run_query", fake_run_query)

    result = runner.invoke(
        app,
        ["query", "What is tool safety?", "--root", str(tmp_path), "--limit", "3", "--deep", "--json"],
    )

    assert result.exit_code == 0
    assert seen["warning"] is None
    assert seen["results"][0].path == "wiki/concepts/evidence.md"


def _query_project(tmp_path) -> WikiPaths:
    paths = WikiPaths.from_root(tmp_path)
    ensure_project_dirs(paths)
    write_config(paths)
    (paths.system / "prompts").mkdir(parents=True, exist_ok=True)
    (paths.system / "prompts" / "query.md").write_text("Use wiki evidence only.", encoding="utf-8")
    (paths.system / "providers").mkdir(parents=True, exist_ok=True)
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
                        "usage": {
                            "query": {
                                "system_prompt_file": "system/prompts/query.md",
                                "temperature": 0.1,
                                "max_tokens": 512,
                            }
                        },
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    paths.log_path.write_text("# Log\n\n", encoding="utf-8")
    return paths


def _write_page(paths: WikiPaths, rel_path: str, *, title: str, source_id: str) -> None:
    page = paths.root / rel_path
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(
        f"""---
title: {title}
type: concept
status: draft
sources: ["{source_id}"]
tags: []
---

# {title}

Guardrails constrain unsafe inputs, malformed outputs, and tool misuse.
""",
        encoding="utf-8",
    )


def _provider() -> ProviderConfig:
    return ProviderConfig(
        type="openai_compatible",
        model="fake-model",
        base_url="https://example.invalid/v1",
        api_key_env="FAKE_API_KEY",
        usage={
            "query": {
                "system_prompt_file": "system/prompts/query.md",
                "temperature": 0.1,
                "max_tokens": 512,
            }
        },
    )
