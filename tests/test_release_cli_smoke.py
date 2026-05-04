from __future__ import annotations

import json

from typer.testing import CliRunner

from llmw.cli.main import app
from llmw.search import providers as search_providers


runner = CliRunner()


def test_clean_project_cli_release_flow(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(search_providers.shutil, "which", lambda name: None)
    monkeypatch.setattr(search_providers, "_sibling_executable", lambda name: None)

    init = runner.invoke(app, ["init", "--root", str(tmp_path)])
    assert init.exit_code == 0
    assert "Traceback" not in init.output

    source = tmp_path / "raw" / "inbox" / "sample.md"
    source.write_text("# Sample Source\n\nThis is a release smoke source about agent testing.\n", encoding="utf-8")

    added = runner.invoke(app, ["source", "add", str(source), "--root", str(tmp_path)])
    assert added.exit_code == 0
    assert "Traceback" not in added.output
    record = json.loads(added.output)
    source_id = record["source_id"]

    packet = runner.invoke(app, ["ingest", "packet", source_id, "--root", str(tmp_path), "--max-chars", "500"])
    assert packet.exit_code == 0
    assert "Required Agent Work" in packet.output
    assert source_id in packet.output

    source_page = tmp_path / "wiki" / "sources" / f"{source_id}.md"
    concept_page = tmp_path / "wiki" / "concepts" / "release-smoke-concept.md"
    source_page.write_text(
        f"""---
title: Sample Source
type: source
status: draft
sources: ["{source_id}"]
tags: []
---

# Sample Source

Release smoke content about agent testing and [[Release Smoke Concept]].
""",
        encoding="utf-8",
    )
    concept_page.write_text(
        f"""---
title: Release Smoke Concept
type: concept
status: draft
sources: ["{source_id}"]
tags: []
---

# Release Smoke Concept

This concept links back to [[Sample Source]] for release smoke coverage.
""",
        encoding="utf-8",
    )

    recorded = runner.invoke(
        app,
        [
            "ingest",
            "record",
            source_id,
            "--root",
            str(tmp_path),
            "--page",
            f"wiki/sources/{source_id}.md",
            "--page",
            "wiki/concepts/release-smoke-concept.md",
        ],
    )
    assert recorded.exit_code == 0
    assert "Traceback" not in recorded.output

    health = runner.invoke(app, ["health", "check", "--root", str(tmp_path)])
    assert health.exit_code == 0
    assert "No health issues found." in health.output

    index = runner.invoke(app, ["index", "check", "--root", str(tmp_path)])
    assert index.exit_code == 0
    assert "wiki/index.md is current." in index.output

    listed = runner.invoke(app, ["source", "list", "--root", str(tmp_path)])
    assert listed.exit_code == 0
    assert f"{source_id}\tingested\t" in listed.output

    search = runner.invoke(app, ["search", "agent", "--root", str(tmp_path), "--limit", "3"])
    assert search.exit_code == 0
    assert f"wiki/sources/{source_id}.md" in search.output
