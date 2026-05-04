from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path

from typer.testing import CliRunner

from llmw.cli.main import app
from llmw.core.config import ensure_project_dirs, write_config
from llmw.core.paths import WikiPaths
from llmw.integrations.codex import install_codex_mcp, probe_mcp_command


runner = CliRunner()
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_install_codex_mcp_writes_and_backs_up_config(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    project = tmp_path / "wiki"
    project.mkdir()
    paths = WikiPaths.from_root(project)
    ensure_project_dirs(paths)
    config_path = tmp_path / ".codex" / "config.toml"
    config_path.parent.mkdir()
    config_path.write_text(
        '[mcp_servers.llm_wiki]\ncommand = "old"\nargs = ["mcp"]\n\n[mcp_servers.other]\ncommand = "other"\n',
        encoding="utf-8",
    )

    payload = install_codex_mcp(paths)

    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    server = config["mcp_servers"]["llm_wiki"]
    assert server["command"].endswith("llmw") or server["command"] == "llmw"
    assert server["args"] == ["mcp", "--root", project.as_posix()]
    assert server["default_tools_approval_mode"] == "approve"
    assert config["mcp_servers"]["other"]["command"] == "other"
    assert payload["backup_path"]


def test_codex_status_json_reports_missing_codex_server(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("PATH", "")

    result = runner.invoke(app, ["integration", "codex", "status", "--root", str(tmp_path), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["codex"]["codex_found"] is False
    assert payload["codex"]["ready"] is False


def test_probe_mcp_command_reads_context_resource(tmp_path, monkeypatch) -> None:
    paths = WikiPaths.from_root(tmp_path)
    ensure_project_dirs(paths)
    write_config(paths)
    paths.log_path.write_text("# Log\n\n", encoding="utf-8")
    monkeypatch.setenv("PYTHONPATH", str(PROJECT_ROOT / "src"))

    payload = probe_mcp_command(
        [sys.executable, "-m", "llmw", "mcp", "--root", tmp_path.as_posix()],
        cwd=tmp_path,
    )

    assert payload["ok"] is True
    assert payload["has_llmw_context"] is True
    assert payload["wiki_pages"] == 0
