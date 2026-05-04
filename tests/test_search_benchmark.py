from __future__ import annotations

import json
import sys
from pathlib import Path

from typer.testing import CliRunner

from llmw.cli.main import app

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from benchmarks.evaluate_search import evaluate
from benchmarks.search_benchmark import QueryCase, load_cases, missing_references
from llmw.core.paths import WikiPaths
from llmw.search.benchmark import build_searcher


runner = CliRunner()


def test_search_benchmark_has_about_one_hundred_cases() -> None:
    cases = load_cases()

    assert len(cases) == 102
    assert len({case.id for case in cases}) == len(cases)
    assert all(case.query for case in cases)
    assert all(case.relevant for case in cases)


def test_search_benchmark_references_existing_wiki_pages() -> None:
    if not (PROJECT_ROOT / "wiki").exists():
        return

    assert missing_references(PROJECT_ROOT) == []


def test_evaluate_computes_precision_recall_f1_and_mrr() -> None:
    cases = [
        QueryCase("q1", "alpha", ["a.md"], "unit"),
        QueryCase("q2", "beta", ["b.md", "c.md"], "unit"),
    ]

    def searcher(query: str, top_k: int) -> list[str]:
        if query == "alpha":
            return ["a.md", "x.md"]
        return ["x.md", "c.md"]

    summary, scores = evaluate(cases, searcher, top_k=2)

    assert [score.hits for score in scores] == [1, 1]
    assert summary["precision_at_k"] == 0.5
    assert summary["recall_at_k"] == 0.75
    assert round(summary["f1_at_k"], 4) == 0.5833
    assert summary["hit_rate_at_k"] == 1.0
    assert summary["mrr_at_k"] == 0.75


def test_python_benchmark_searcher_reuses_fast_search_ranking(tmp_path) -> None:
    paths = WikiPaths.from_root(tmp_path)
    concept_dir = tmp_path / "wiki" / "concepts"
    analysis_dir = tmp_path / "wiki" / "analyses"
    concept_dir.mkdir(parents=True)
    analysis_dir.mkdir(parents=True)
    (concept_dir / "agent-checkpointing.md").write_text(
        "---\ntitle: Agent Checkpointing\ntype: concept\n---\n\n"
        "# Agent Checkpointing\n\n"
        "Checkpointing persists agent state snapshots for recovery and auditing.",
        encoding="utf-8",
    )
    (analysis_dir / "overview.md").write_text(
        "---\ntitle: Agent Development Overview\ntype: analysis\n---\n\n"
        "# Agent Development Overview\n\n"
        + "agent runtime interoperability security tool protocol " * 80,
        encoding="utf-8",
    )

    searcher = build_searcher("python", paths, content_only=True)

    assert searcher("persisting agent snapshots for recovery", 3)[0] == "wiki/concepts/agent-checkpointing.md"


def test_python_benchmark_searcher_is_stable_across_repeated_queries(tmp_path) -> None:
    paths = WikiPaths.from_root(tmp_path)
    concept_dir = tmp_path / "wiki" / "concepts"
    concept_dir.mkdir(parents=True)
    (concept_dir / "guardrails.md").write_text(
        "---\ntitle: Guardrails\ntype: concept\n---\n\n# Guardrails\n\nAgents use guardrails for safety.",
        encoding="utf-8",
    )

    searcher = build_searcher("python", paths, content_only=True)

    assert searcher("guardrails", 3) == searcher("guardrails", 3)


def test_benchmark_search_cli_json() -> None:
    result = runner.invoke(
        app,
        [
            "benchmark",
            "search",
            "--root",
            str(PROJECT_ROOT),
            "--provider",
            "python",
            "--top-k",
            "5",
            "--fail-under-f1",
            "0.10",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["benchmark"]["summary"]["queries"] == 102
    assert "precision_at_k_ceiling" in payload["benchmark"]["summary"]
