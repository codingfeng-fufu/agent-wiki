from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from llmw.cli import main as cli_main
from llmw.cli.main import app
from llmw.core.config import ensure_project_dirs, write_config
from llmw.core.paths import WikiPaths
from llmw.health.checks import HealthChecker
from llmw.llm.client import ChatResult
from llmw.llm.config import ProviderConfig
from llmw.llm.health import (
    HealthAuditResult,
    build_health_audit_prompt,
    extract_audit_issues,
    run_health_audit,
)
from llmw.wiki.index import index_is_current, rebuild_index


runner = CliRunner()


class FakeClient:
    calls: list[dict] = []

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
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "temperature": temperature,
                "top_p": top_p,
                "max_tokens": max_tokens,
            }
        )
        return ChatResult(
            content="## Summary\n\nReview source traceability for Evidence Source.",
            model="fake-model",
            usage={"total_tokens": 7},
        )


def test_run_health_audit_reads_wiki_context_and_calls_provider(tmp_path) -> None:
    paths = _health_project(tmp_path)
    _write_page(paths, "wiki/concepts/evidence.md", title="Evidence Source", source_id="source-1")
    rebuild_index(paths)
    FakeClient.calls = []

    result = run_health_audit(paths, provider=_provider(), client_factory=FakeClient)

    assert result.report.startswith("## Summary")
    assert result.model == "fake-model"
    assert result.usage == {"total_tokens": 7}
    assert result.pages[0].path == "wiki/concepts/evidence.md"
    assert result.pages[0].sources == ["source-1"]
    assert "Current index:" in FakeClient.calls[0]["user_prompt"]
    assert "Recent log:" in FakeClient.calls[0]["user_prompt"]
    assert "Evidence Source" in FakeClient.calls[0]["user_prompt"]
    assert "source-1" in FakeClient.calls[0]["user_prompt"]
    assert FakeClient.calls[0]["temperature"] == 0.0
    assert FakeClient.calls[0]["max_tokens"] == 256


def test_health_audit_handles_empty_wiki(tmp_path) -> None:
    paths = _health_project(tmp_path)
    FakeClient.calls = []

    result = run_health_audit(paths, provider=_provider(), client_factory=FakeClient)

    assert result.pages == []
    assert "No maintained wiki pages were found." in FakeClient.calls[0]["user_prompt"]
    assert result.report.startswith("## Summary")


def test_health_audit_save_writes_output_updates_log_and_index(tmp_path) -> None:
    paths = _health_project(tmp_path)
    _write_page(paths, "wiki/concepts/evidence.md", title="Evidence Source", source_id="source-1")
    rebuild_index(paths)

    result = run_health_audit(paths, provider=_provider(), client_factory=FakeClient, save=True)

    assert result.saved_page is not None
    saved = paths.root / result.saved_page
    saved_text = saved.read_text(encoding="utf-8")
    assert "type: output" in saved_text
    assert "health" in saved_text
    assert "[[Evidence Source]]" in saved_text
    assert "Health | Health Audit" in paths.log_path.read_text(encoding="utf-8")
    assert index_is_current(paths)
    assert not [issue for issue in HealthChecker(paths).run() if issue.severity == "error"]


def test_health_audit_requires_usage_health(tmp_path) -> None:
    paths = _health_project(tmp_path)
    provider = ProviderConfig(
        type="openai_compatible",
        model="fake-model",
        base_url="https://example.invalid/v1",
        api_key_env="FAKE_API_KEY",
        usage={},
    )

    with pytest.raises(KeyError, match="usage.health"):
        run_health_audit(paths, provider=provider, client_factory=FakeClient)


def test_build_health_audit_prompt_lists_required_sections(tmp_path) -> None:
    paths = _health_project(tmp_path)

    prompt = build_health_audit_prompt(paths, [])

    assert "## Summary" in prompt
    assert "## Findings" in prompt
    assert "weak or missing source traceability" in prompt
    assert "Use only the wiki context" in prompt


def test_extract_audit_issues_from_markdown_sections() -> None:
    issues = extract_audit_issues(
        """## Summary

Looks good.

## Findings

- Missing source traceability in `wiki/concepts/a.md`.

## Follow-up Sources

- Find newer security guidance.
"""
    )

    assert [issue["section"] for issue in issues] == ["Findings", "Follow-up Sources"]
    assert issues[0]["severity"] == "medium"
    assert issues[1]["severity"] == "low"


def test_health_audit_cli_json_wires_command(monkeypatch, tmp_path) -> None:
    paths = _health_project(tmp_path)

    def fake_run_health_audit(*args, **kwargs):
        assert args[0].root == paths.root
        assert kwargs["max_pages"] == 7
        assert kwargs["max_page_chars"] == 900
        assert kwargs["save"] is True
        return HealthAuditResult(
            report="## Summary\n\nLooks good.",
            pages=[],
            model="fake-model",
            usage={"total_tokens": 1},
            saved_page="wiki/outputs/health-audit.md",
        )

    monkeypatch.setattr(cli_main, "run_health_audit", fake_run_health_audit)

    result = runner.invoke(
        app,
        [
            "health",
            "audit",
            "--root",
            str(tmp_path),
            "--max-pages",
            "7",
            "--max-page-chars",
            "900",
            "--save",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["report"].startswith("## Summary")
    assert payload["model"] == "fake-model"
    assert payload["saved_page"] == "wiki/outputs/health-audit.md"


def _health_project(tmp_path) -> WikiPaths:
    paths = WikiPaths.from_root(tmp_path)
    ensure_project_dirs(paths)
    write_config(paths)
    (paths.system / "prompts").mkdir(parents=True, exist_ok=True)
    (paths.system / "prompts" / "health.md").write_text("Audit wiki evidence only.", encoding="utf-8")
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
                            "health": {
                                "system_prompt_file": "system/prompts/health.md",
                                "temperature": 0.0,
                                "max_tokens": 256,
                            }
                        },
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    paths.log_path.write_text("# Log\n\n## [2026-01-01] Ingest | Evidence\n\nAdded evidence.\n", encoding="utf-8")
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
            "health": {
                "system_prompt_file": "system/prompts/health.md",
                "temperature": 0.0,
                "max_tokens": 256,
            }
        },
    )
