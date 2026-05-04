from __future__ import annotations

import json

from typer.testing import CliRunner

from llmw.agent.maintain import run_maintain
from llmw.cli.main import app
from llmw.core.config import ensure_project_dirs, write_config
from llmw.core.paths import WikiPaths
from llmw.llm.config import ProviderConfig
from llmw.llm.health import HealthAuditResult
from llmw.wiki.index import rebuild_index


runner = CliRunner()


def test_maintain_cli_json_no_audit_returns_saved_plan(tmp_path) -> None:
    paths = _project(tmp_path)
    rebuild_index(paths)

    result = runner.invoke(app, ["maintain", "--root", str(tmp_path), "--no-audit", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    maintenance = payload["maintenance"]
    assert payload["ok"] is True
    assert maintenance["context"]["root"] == tmp_path.as_posix()
    assert maintenance["tasks"]
    assert maintenance["plan"]["goal"] == "maintain wiki"
    assert maintenance["plan"]["steps"] == []
    assert maintenance["saved_plan"]
    assert (tmp_path / maintenance["saved_plan"]).exists()


def test_maintain_cli_default_audit_warns_when_provider_missing(tmp_path) -> None:
    paths = _project(tmp_path)
    rebuild_index(paths)

    result = runner.invoke(app, ["maintain", "--root", str(tmp_path), "--no-save-plan", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    warnings = payload["maintenance"]["warnings"]
    assert payload["ok"] is True
    assert any("Semantic audit skipped" in warning for warning in warnings)


def test_maintain_no_save_plan_does_not_create_plan_directory(tmp_path) -> None:
    paths = _project(tmp_path)
    rebuild_index(paths)

    result = runner.invoke(
        app,
        ["maintain", "--root", str(tmp_path), "--no-audit", "--no-save-plan", "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["maintenance"]["saved_plan"] is None
    assert not (tmp_path / ".llmw" / "plans").exists()


def test_maintain_plans_unregistered_raw_source(tmp_path) -> None:
    paths = _project(tmp_path)
    rebuild_index(paths)
    source = paths.raw_inbox / "new-note.md"
    source.write_text("# New Note\n", encoding="utf-8")

    result = runner.invoke(app, ["maintain", "--root", str(tmp_path), "--no-audit", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    maintenance = payload["maintenance"]
    assert any(task["kind"] == "source_register" for task in maintenance["tasks"])
    assert maintenance["plan"]["steps"][0]["action"] == "source_add"
    assert maintenance["plan"]["steps"][0]["args"]["path"] == "raw/inbox/new-note.md"
    assert (tmp_path / maintenance["saved_plan"]).exists()


def test_maintain_plans_stale_index_rebuild(tmp_path) -> None:
    paths = _project(tmp_path)
    (paths.wiki_concepts / "alpha.md").write_text(
        """---
title: Alpha
type: concept
sources: []
---

# Alpha

Concept page.
""",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["maintain", "--root", str(tmp_path), "--no-audit", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    steps = payload["maintenance"]["plan"]["steps"]
    assert any(step["action"] == "index_rebuild" for step in steps)


def test_run_maintain_includes_audit_summary_from_runner(tmp_path) -> None:
    paths = _project(tmp_path)
    provider = _provider()

    def fake_audit_runner(paths, *, provider, save):
        return HealthAuditResult(
            report="## Summary\n\nLooks coherent.",
            pages=[],
            model=provider.model,
            usage={"total_tokens": 1},
        )

    maintenance = run_maintain(
        paths,
        provider=provider,
        audit=True,
        save_plan_file=False,
        health_audit_runner=fake_audit_runner,
    )

    assert maintenance["audit_summary"]["model"] == "fake-model"
    assert maintenance["audit_summary"]["pages"] == 0
    assert "Looks coherent" in maintenance["audit_summary"]["report_excerpt"]
    assert maintenance["warnings"] == []


def test_run_maintain_turns_audit_issues_into_review_steps(tmp_path) -> None:
    paths = _project(tmp_path)
    provider = _provider()

    def fake_audit_runner(paths, *, provider, save):
        return HealthAuditResult(
            report="## Findings\n\n- Missing link between guardrails and tracing.",
            pages=[],
            model=provider.model,
            issues=[
                {
                    "section": "Findings",
                    "title": "Missing link between guardrails and tracing.",
                    "detail": "Missing link between guardrails and tracing.",
                    "severity": "medium",
                }
            ],
        )

    maintenance = run_maintain(
        paths,
        provider=provider,
        audit=True,
        save_plan_file=False,
        health_audit_runner=fake_audit_runner,
    )

    assert maintenance["audit_summary"]["issues"]
    audit_steps = [step for step in maintenance["plan"]["steps"] if step["action"] == "audit_issue_plan"]
    assert audit_steps
    assert audit_steps[0]["args"]["section"] == "Findings"


def test_run_maintain_turns_audit_failure_into_warning(tmp_path) -> None:
    paths = _project(tmp_path)
    provider = _provider()

    def failing_audit_runner(paths, *, provider, save):
        raise RuntimeError("provider offline")

    maintenance = run_maintain(
        paths,
        provider=provider,
        audit=True,
        save_plan_file=False,
        health_audit_runner=failing_audit_runner,
    )

    assert maintenance["audit_summary"] is None
    assert any("provider offline" in warning for warning in maintenance["warnings"])


def _project(tmp_path) -> WikiPaths:
    paths = WikiPaths.from_root(tmp_path)
    ensure_project_dirs(paths)
    write_config(paths)
    paths.log_path.write_text("# Log\n\n", encoding="utf-8")
    return paths


def _provider() -> ProviderConfig:
    return ProviderConfig(
        type="openai_compatible",
        model="fake-model",
        base_url="https://example.invalid/v1",
        api_key_env="FAKE_API_KEY",
    )
