from __future__ import annotations

import json

from typer.testing import CliRunner

from llmw.cli.main import app
from llmw.core.config import ensure_project_dirs, write_config
from llmw.core.paths import WikiPaths


runner = CliRunner()


def test_perf_benchmark_cli_json(tmp_path) -> None:
    paths = WikiPaths.from_root(tmp_path)
    ensure_project_dirs(paths)
    write_config(paths)
    paths.log_path.write_text("# Log\n\n", encoding="utf-8")
    (paths.wiki_concepts / "guardrails.md").write_text("# Guardrails\n\nAgent guardrails.", encoding="utf-8")

    result = runner.invoke(app, ["benchmark", "perf", "--root", str(tmp_path), "--repeat", "1", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["performance"]["summary"]["max_mean_ms"] >= 0
    assert any(check["name"].startswith("search.fast:") for check in payload["performance"]["checks"])
