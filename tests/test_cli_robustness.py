import json

from typer.testing import CliRunner

from llmw.cli.main import app


runner = CliRunner()


def test_source_add_missing_file_reports_clean_error(tmp_path) -> None:
    result = runner.invoke(
        app,
        ["source", "add", str(tmp_path / "missing.md"), "--root", str(tmp_path)],
    )

    assert result.exit_code == 1
    assert "Error:" in result.output
    assert "missing.md" in result.output
    assert "Traceback" not in result.output


def test_source_add_missing_file_reports_json_error(tmp_path) -> None:
    result = runner.invoke(
        app,
        ["source", "add", str(tmp_path / "missing.md"), "--root", str(tmp_path), "--json"],
    )

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "source-add-failed"


def test_ingest_packet_unknown_source_reports_clean_error(tmp_path) -> None:
    result = runner.invoke(
        app,
        ["ingest", "packet", "missing-source-id", "--root", str(tmp_path)],
    )

    assert result.exit_code == 1
    assert "Error: Unknown source_id: missing-source-id" in result.output
    assert "Traceback" not in result.output


def test_index_check_json_reports_stale_index(tmp_path) -> None:
    result = runner.invoke(app, ["index", "check", "--root", str(tmp_path), "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "index-stale"


def test_llm_check_missing_key_reports_clean_error(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    init = runner.invoke(app, ["init", "--root", str(tmp_path)])
    assert init.exit_code == 0

    result = runner.invoke(app, ["llm", "check", "--root", str(tmp_path)])

    assert result.exit_code == 1
    assert "Error: Missing environment variable: DASHSCOPE_API_KEY" in result.output
    assert "Traceback" not in result.output


def test_llm_check_missing_key_reports_json_error(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    init = runner.invoke(app, ["init", "--root", str(tmp_path)])
    assert init.exit_code == 0

    result = runner.invoke(app, ["llm", "check", "--root", str(tmp_path), "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "llm-check-failed"
