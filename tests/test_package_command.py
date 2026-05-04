from __future__ import annotations

import json
import shutil
import tomllib
from pathlib import Path

import pytest
from typer.testing import CliRunner

from llmw.cli.main import app


runner = CliRunner()
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_package_build_sdist_json(tmp_path) -> None:
    if shutil.which("uv") is None:
        pytest.skip("uv is required for package build checks")

    result = runner.invoke(
        app,
        [
            "package",
            "build",
            "--root",
            str(PROJECT_ROOT),
            "--out-dir",
            str(tmp_path),
            "--no-check",
            "--sdist",
            "--no-wheel",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert len(payload["package"]["artifacts"]) == 1
    assert payload["package"]["artifacts"][0]["name"].endswith(".tar.gz")
    assert payload["package"]["audits"][0]["ok"] is True
    assert (tmp_path / "llmw-package-report.json").exists()


def test_package_build_rejects_no_formats(tmp_path) -> None:
    result = runner.invoke(
        app,
        [
            "package",
            "build",
            "--root",
            str(PROJECT_ROOT),
            "--out-dir",
            str(tmp_path),
            "--no-check",
            "--no-sdist",
            "--no-wheel",
            "--json",
        ],
    )

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "package-build-failed"


def test_install_agent_codex_writes_config_without_probe(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    project = tmp_path / "project"
    init = runner.invoke(app, ["init", "--root", str(project)])
    assert init.exit_code == 0

    result = runner.invoke(
        app,
        [
            "install-agent",
            "codex",
            "--root",
            str(project),
            "--no-test",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    config = tomllib.loads((tmp_path / ".codex" / "config.toml").read_text(encoding="utf-8"))
    server = config["mcp_servers"]["llm_wiki"]
    assert server["args"] == ["mcp", "--root", project.as_posix()]
    assert server["default_tools_approval_mode"] == "approve"
