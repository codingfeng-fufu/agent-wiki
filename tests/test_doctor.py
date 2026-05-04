from __future__ import annotations

import json

from typer.testing import CliRunner

from llmw.cli.main import app


runner = CliRunner()


def test_doctor_json_reports_usable_project_with_warnings(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    init = runner.invoke(app, ["init", "--root", str(tmp_path)])
    assert init.exit_code == 0

    result = runner.invoke(app, ["doctor", "--root", str(tmp_path), "--no-codex", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["doctor"]["readiness"] == "usable-with-warnings"
    assert any(check["id"] == "llm.provider" and check["status"] == "warn" for check in payload["doctor"]["checks"])


def test_doctor_strict_json_fails_on_warning(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    init = runner.invoke(app, ["init", "--root", str(tmp_path)])
    assert init.exit_code == 0

    result = runner.invoke(app, ["doctor", "--root", str(tmp_path), "--no-codex", "--strict", "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "doctor-failed"
    assert payload["doctor"]["readiness"] == "blocked"


def test_doctor_fails_when_project_is_not_initialized(tmp_path) -> None:
    result = runner.invoke(app, ["doctor", "--root", str(tmp_path), "--no-codex", "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert any(check["id"] == "project.dirs" and check["status"] == "fail" for check in payload["doctor"]["checks"])
