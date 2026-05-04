from __future__ import annotations

import json

from typer.testing import CliRunner

from llmw.cli.main import app


runner = CliRunner()


def test_release_check_json_minimal_passes_initialized_project(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DASHSCOPE_API_KEY", "from-test")
    init = runner.invoke(app, ["init", "--root", str(tmp_path)])
    assert init.exit_code == 0

    result = runner.invoke(
        app,
        [
            "release",
            "check",
            "--root",
            str(tmp_path),
            "--no-tests",
            "--no-benchmark",
            "--no-sdist",
            "--no-codex",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["release"]["readiness"] == "ready"
    assert any(check["id"] == "doctor" and check["status"] == "pass" for check in payload["release"]["checks"])


def test_release_check_json_fails_uninitialized_project(tmp_path) -> None:
    result = runner.invoke(
        app,
        [
            "release",
            "check",
            "--root",
            str(tmp_path),
            "--no-tests",
            "--no-benchmark",
            "--no-sdist",
            "--no-codex",
            "--json",
        ],
    )

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "release-check-failed"
    assert payload["release"]["readiness"] == "blocked"


def test_release_check_json_can_run_search_benchmark_on_repo() -> None:
    result = runner.invoke(
        app,
        [
            "release",
            "check",
            "--no-tests",
            "--no-sdist",
            "--no-codex",
            "--no-strict",
            "--search-provider",
            "python",
            "--fail-under-f1",
            "0.10",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    benchmark = next(check for check in payload["release"]["checks"] if check["id"] == "search.benchmark")
    assert benchmark["status"] == "pass"
    assert benchmark["details"]["summary"]["queries"] == 102
