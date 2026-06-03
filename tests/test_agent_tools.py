from __future__ import annotations

import json

from typer.testing import CliRunner

from llmw.agent.tools import ToolPlan, ToolStep, create_plan
from llmw.cli.main import app
from llmw.core.config import ensure_project_dirs, write_config
from llmw.core.paths import WikiPaths
from llmw.sources.registry import load_registry
from llmw.wiki.index import index_is_current


runner = CliRunner()


def test_context_json_reports_project_state(tmp_path) -> None:
    paths = _project(tmp_path)
    (paths.wiki_concepts / "alpha.md").write_text("# Alpha\n\nConcept.", encoding="utf-8")

    result = runner.invoke(app, ["context", "--root", str(tmp_path), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["context"]["root"] == tmp_path.as_posix()
    assert payload["context"]["wiki"]["pages"] == 1
    assert "llmw_next" in payload["context"]["recommended_commands"]


def test_next_json_finds_unregistered_raw_source(tmp_path) -> None:
    paths = _project(tmp_path)
    source = paths.raw_inbox / "new-note.md"
    source.write_text("# New Note\n", encoding="utf-8")

    result = runner.invoke(app, ["next", "--root", str(tmp_path), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert any(task["kind"] == "source_register" for task in payload["tasks"])


def test_plan_save_and_apply_source_add(tmp_path) -> None:
    paths = _project(tmp_path)
    source = paths.raw_inbox / "new-note.md"
    source.write_text("# New Note\n", encoding="utf-8")

    planned = runner.invoke(app, ["plan", "register all sources", "--root", str(tmp_path), "--save", "--json"])
    assert planned.exit_code == 0
    plan_payload = json.loads(planned.output)
    plan_path = tmp_path / plan_payload["saved_plan"]

    applied = runner.invoke(app, ["apply", str(plan_path), "--root", str(tmp_path), "--json"])

    assert applied.exit_code == 0
    apply_payload = json.loads(applied.output)
    assert apply_payload["ok"] is True
    assert apply_payload["applied"] == 1
    registry = load_registry(paths)
    assert len(registry.sources) == 1


def test_apply_rejects_non_whitelisted_action_with_json_error(tmp_path) -> None:
    paths = _project(tmp_path)
    plan = ToolPlan(
        plan_id="plan-bad",
        goal="bad",
        created_at="2026-01-01T00:00:00Z",
        steps=[ToolStep(id="step-1", action="query", args={"question": "hello"})],
    )
    plan_path = tmp_path / "bad-plan.json"
    plan_path.write_text(plan.model_dump_json(), encoding="utf-8")

    result = runner.invoke(app, ["apply", str(plan_path), "--root", str(tmp_path), "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "apply-failed"
    assert "Unsupported apply action" in payload["error"]["message"]


def test_apply_index_rebuild_plan(tmp_path) -> None:
    paths = _project(tmp_path)
    page = paths.wiki_concepts / "alpha.md"
    page.write_text("# Alpha\n\nConcept.", encoding="utf-8")
    plan = create_plan(paths, "rebuild index")
    plan_path = tmp_path / "index-plan.json"
    plan_path.write_text(plan.model_dump_json(), encoding="utf-8")

    result = runner.invoke(app, ["apply", str(plan_path), "--root", str(tmp_path), "--json"])

    assert result.exit_code == 0
    assert index_is_current(paths)


def test_apply_wiki_patch_dry_run_then_apply(tmp_path) -> None:
    paths = _project(tmp_path)
    page = paths.wiki_concepts / "alpha.md"
    page.write_text("# Alpha\n\nOld text.", encoding="utf-8")
    plan = ToolPlan(
        plan_id="plan-patch",
        goal="patch wiki",
        created_at="2026-01-01T00:00:00Z",
        steps=[
            ToolStep(
                id="step-1",
                action="wiki_patch",
                args={"path": "wiki/concepts/alpha.md", "old": "Old text.", "new": "New text."},
                writes=["wiki/concepts/alpha.md"],
            )
        ],
    )
    plan_path = tmp_path / "patch-plan.json"
    plan_path.write_text(plan.model_dump_json(), encoding="utf-8")

    preview = runner.invoke(app, ["apply", str(plan_path), "--root", str(tmp_path), "--dry-run", "--json"])
    assert preview.exit_code == 0
    preview_payload = json.loads(preview.output)
    assert preview_payload["dry_run"] is True
    assert "+New text." in preview_payload["results"][0]["output"]["diff"]
    assert "Old text." in page.read_text(encoding="utf-8")

    applied = runner.invoke(app, ["apply", str(plan_path), "--root", str(tmp_path), "--json"])
    assert applied.exit_code == 0
    assert "New text." in page.read_text(encoding="utf-8")


def test_wiki_patch_rejects_raw_paths(tmp_path) -> None:
    _project(tmp_path)
    plan = ToolPlan(
        plan_id="plan-raw",
        goal="bad patch",
        created_at="2026-01-01T00:00:00Z",
        steps=[
            ToolStep(
                id="step-1",
                action="wiki_patch",
                args={"path": "raw/inbox/source.md", "create": True, "new": "# Bad"},
            )
        ],
    )
    plan_path = tmp_path / "raw-plan.json"
    plan_path.write_text(plan.model_dump_json(), encoding="utf-8")

    result = runner.invoke(app, ["apply", str(plan_path), "--root", str(tmp_path), "--dry-run", "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert "wiki/ or system/" in payload["error"]["message"]


def test_plan_source_add_rejects_files_outside_raw_inbox(tmp_path) -> None:
    _project(tmp_path)
    private_source = tmp_path / "private-note.md"
    private_source.write_text("# Private\n", encoding="utf-8")
    plan = ToolPlan(
        plan_id="plan-private-source",
        goal="bad source",
        created_at="2026-01-01T00:00:00Z",
        steps=[
            ToolStep(
                id="step-1",
                action="source_add",
                args={"path": "private-note.md"},
                writes=[".llmw/sources.json", "raw/processed/"],
            )
        ],
    )
    plan_path = tmp_path / "private-source-plan.json"
    plan_path.write_text(plan.model_dump_json(), encoding="utf-8")

    result = runner.invoke(app, ["apply", str(plan_path), "--root", str(tmp_path), "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert "raw/inbox" in payload["error"]["message"]


def test_query_json_error_contract(tmp_path) -> None:
    paths = _project(tmp_path)
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
                        "api_key_env": "MISSING_FAKE_KEY",
                        "usage": {
                            "query": {
                                "system_prompt_file": "system/prompts/query.md",
                                "temperature": 0.1,
                                "max_tokens": 128,
                            }
                        },
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    (paths.system / "prompts").mkdir(parents=True, exist_ok=True)
    (paths.system / "prompts" / "query.md").write_text("Use wiki evidence.", encoding="utf-8")

    result = runner.invoke(app, ["query", "missing topic", "--root", str(tmp_path), "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "query-failed"


def _project(tmp_path) -> WikiPaths:
    paths = WikiPaths.from_root(tmp_path)
    ensure_project_dirs(paths)
    write_config(paths)
    paths.log_path.write_text("# Log\n\n", encoding="utf-8")
    return paths
