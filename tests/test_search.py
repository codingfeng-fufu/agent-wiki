import io
import json

import pytest
from typer.testing import CliRunner

from llmw.cli.main import app
from llmw.core.config import ensure_project_dirs, write_config
from llmw.core.paths import WikiPaths
from llmw.search import daemon as search_daemon
from llmw.search import providers
from llmw.search.daemon import daemon_status, query_daemon, query_deep_daemon_if_running, start_daemon, stop_daemon
from llmw.search.providers import QmdSearchProvider, RgSearchProvider, SearchService, build_search_service, recommend_search_strategy
from llmw.search.server import serve_search_lines


runner = CliRunner()


def test_python_scan_fallback_search(tmp_path) -> None:
    paths = WikiPaths.from_root(tmp_path)
    page_dir = tmp_path / "wiki" / "concepts"
    page_dir.mkdir(parents=True)
    (page_dir / "alpha.md").write_text(
        "---\ntitle: Alpha\ntype: concept\n---\n\n# Alpha\n\nRetrieval synthesis notes.",
        encoding="utf-8",
    )

    provider = RgSearchProvider(paths, executable="")
    results = provider.search("synthesis")

    assert len(results) == 1
    assert results[0].title == "Alpha"
    assert results[0].provider == "python-scan"


def test_rg_search_falls_back_to_terms_for_question_queries(tmp_path) -> None:
    paths = WikiPaths.from_root(tmp_path)
    page_dir = tmp_path / "wiki" / "concepts"
    page_dir.mkdir(parents=True)
    (page_dir / "guardrails.md").write_text(
        "---\ntitle: Guardrails\ntype: concept\n---\n\n# Guardrails\n\nAgents use guardrails for safety.",
        encoding="utf-8",
    )

    results = RgSearchProvider(paths).search("how should agents use guardrails?", limit=3)

    assert results
    assert results[0].title == "Guardrails"


def test_python_scan_skips_index_and_log(tmp_path) -> None:
    paths = WikiPaths.from_root(tmp_path)
    paths.wiki.mkdir(parents=True)
    paths.index_path.write_text("# Index\n\nGuardrails guardrails guardrails.", encoding="utf-8")
    paths.log_path.write_text("# Log\n\nGuardrails guardrails guardrails.", encoding="utf-8")
    page_dir = tmp_path / "wiki" / "concepts"
    page_dir.mkdir(parents=True)
    (page_dir / "guardrails.md").write_text("# Guardrails\n\nGuardrails.", encoding="utf-8")

    results = RgSearchProvider(paths, executable="").search("guardrails")

    assert [result.path for result in results] == ["wiki/concepts/guardrails.md"]


def test_python_scan_ranks_specific_concept_above_long_overview(tmp_path) -> None:
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

    results = RgSearchProvider(paths, executable="").search(
        "persisting agent snapshots for recovery",
        limit=3,
    )

    assert [result.path for result in results][0] == "wiki/concepts/agent-checkpointing.md"


def test_python_scan_normalizes_light_word_forms(tmp_path) -> None:
    paths = WikiPaths.from_root(tmp_path)
    page_dir = tmp_path / "wiki" / "concepts"
    page_dir.mkdir(parents=True)
    (page_dir / "durability.md").write_text(
        "---\ntitle: Durable Agent Execution\ntype: concept\n---\n\n"
        "# Durable Agent Execution\n\n"
        "Durable execution persists workflow state and resumes after interruption.",
        encoding="utf-8",
    )

    results = RgSearchProvider(paths, executable="").search("persisting interrupted workflows", limit=3)

    assert results
    assert results[0].path == "wiki/concepts/durability.md"


def test_python_scan_matches_chinese_natural_language_query(tmp_path) -> None:
    paths = WikiPaths.from_root(tmp_path)
    page_dir = tmp_path / "wiki" / "concepts"
    page_dir.mkdir(parents=True)
    (page_dir / "长期记忆层.md").write_text(
        "---\ntitle: 长期记忆层\ntype: concept\n---\n\n"
        "# 长期记忆层\n\n"
        "长期记忆层帮助 coding agent 减少重复读取项目上下文。",
        encoding="utf-8",
    )

    results = RgSearchProvider(paths, executable="").search("这个项目为什么需要一个长期记忆层？", limit=3)

    assert results
    assert results[0].path == "wiki/concepts/长期记忆层.md"


def test_python_scan_reuses_cached_rank_index(tmp_path, monkeypatch) -> None:
    paths = WikiPaths.from_root(tmp_path)
    concept_dir = tmp_path / "wiki" / "concepts"
    concept_dir.mkdir(parents=True)
    (concept_dir / "alpha.md").write_text(
        "---\ntitle: Alpha\ntype: concept\n---\n\n# Alpha\n\nRetrieval synthesis notes.",
        encoding="utf-8",
    )

    calls = {"count": 0}
    original = providers._build_rank_index

    def wrapped(documents, *, root):
        calls["count"] += 1
        return original(documents, root=root)

    monkeypatch.setattr(providers, "_build_rank_index", wrapped)

    provider = RgSearchProvider(paths, executable="")
    provider.search("synthesis", limit=3)
    provider.search("alpha", limit=3)

    assert calls["count"] == 1


def test_python_scan_persists_rank_index_between_provider_instances(tmp_path, monkeypatch) -> None:
    paths = WikiPaths.from_root(tmp_path)
    concept_dir = tmp_path / "wiki" / "concepts"
    concept_dir.mkdir(parents=True)
    (concept_dir / "alpha.md").write_text(
        "---\ntitle: Alpha\ntype: concept\n---\n\n# Alpha\n\nRetrieval synthesis notes.",
        encoding="utf-8",
    )

    first = RgSearchProvider(paths, executable="")
    assert first.search("synthesis", limit=3)

    cache_path = paths.state / "cache" / "python-rank-content.json"
    assert cache_path.exists()

    def fail_read_markdown(path):
        raise AssertionError(f"unexpected markdown read after cache warm: {path}")

    monkeypatch.setattr(providers, "read_markdown", fail_read_markdown)

    second = RgSearchProvider(paths, executable="")
    results = second.search("synthesis", limit=3)

    assert results[0].path == "wiki/concepts/alpha.md"


def test_python_scan_invalidates_persisted_rank_index_when_page_changes(tmp_path) -> None:
    paths = WikiPaths.from_root(tmp_path)
    concept_dir = tmp_path / "wiki" / "concepts"
    concept_dir.mkdir(parents=True)
    page = concept_dir / "alpha.md"
    page.write_text(
        "---\ntitle: Alpha\ntype: concept\n---\n\n# Alpha\n\nRetrieval synthesis notes.",
        encoding="utf-8",
    )

    assert RgSearchProvider(paths, executable="").search("synthesis", limit=3)
    page.write_text(
        "---\ntitle: Alpha\ntype: concept\n---\n\n# Alpha\n\nCheckpoint replay notes.",
        encoding="utf-8",
    )

    results = RgSearchProvider(paths, executable="").search("checkpoint", limit=3)

    assert results
    assert results[0].path == "wiki/concepts/alpha.md"


class FailingProvider:
    name = "failing"

    def available(self) -> bool:
        return True

    def search(self, query: str, *, limit: int = 10, deep: bool = False):
        raise RuntimeError("boom")


def test_search_service_warns_on_primary_failure(tmp_path) -> None:
    paths = WikiPaths.from_root(tmp_path)
    (tmp_path / "wiki").mkdir()
    fallback = RgSearchProvider(paths, executable="")
    service = SearchService(FailingProvider(), fallback)

    results, warning = service.search("anything")

    assert results == []
    assert warning is not None
    assert "fell back" in warning


def test_search_strategy_recommends_deep_for_cross_cutting_queries() -> None:
    strategy = recommend_search_strategy("how should agents coordinate reviewer and human approval roles")

    assert strategy["mode"] == "fast"
    assert strategy["deep_recommended"] is True
    assert "search-server --deep" in strategy["reason"]


def test_search_cli_json_includes_strategy(tmp_path) -> None:
    paths = WikiPaths.from_root(tmp_path)
    paths.wiki_concepts.mkdir(parents=True)
    (paths.wiki_concepts / "guardrails.md").write_text(
        "---\ntitle: Guardrails\ntype: concept\n---\n\n# Guardrails\n\nAgents use guardrails for safety.",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["search", "how should agents use guardrails?", "--root", str(tmp_path), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["strategy"]["deep_recommended"] is True
    assert payload["results"][0]["path"] == "wiki/concepts/guardrails.md"


def test_search_server_serves_ndjson_requests(tmp_path) -> None:
    paths = WikiPaths.from_root(tmp_path)
    paths.wiki_concepts.mkdir(parents=True)
    (paths.wiki_concepts / "alpha.md").write_text(
        "---\ntitle: Alpha\ntype: concept\n---\n\n# Alpha\n\nRetrieval synthesis notes.",
        encoding="utf-8",
    )
    output = io.StringIO()

    serve_search_lines(
        paths,
        input_stream=io.StringIO('{"query":"synthesis","limit":2}\n{"action":"ping"}\n{"action":"exit"}\n'),
        output_stream=output,
    )

    lines = [json.loads(line) for line in output.getvalue().splitlines()]
    assert lines[0]["ready"] is True
    assert lines[1]["ok"] is True
    assert lines[1]["results"][0]["path"] == "wiki/concepts/alpha.md"
    assert lines[2]["pong"] is True
    assert lines[3]["bye"] is True


def test_search_daemon_lifecycle_serves_queries(tmp_path) -> None:
    paths = WikiPaths.from_root(tmp_path)
    ensure_project_dirs(paths)
    write_config(paths)
    (paths.wiki_concepts / "alpha.md").write_text(
        "---\ntitle: Alpha\ntype: concept\n---\n\n# Alpha\n\nWarm daemon retrieval.",
        encoding="utf-8",
    )

    try:
        started = start_daemon(paths, default_limit=2, timeout_seconds=10)
        assert started["running"] is True
        payload = query_daemon(paths, "daemon")
        assert payload["ok"] is True
        assert payload["results"][0]["path"] == "wiki/concepts/alpha.md"
        assert daemon_status(paths)["running"] is True
    finally:
        stopped = stop_daemon(paths)

    assert stopped.get("stopped") in {True, False}
    assert daemon_status(paths)["running"] is False


def test_deep_daemon_query_helper_only_uses_deep_daemon(tmp_path, monkeypatch) -> None:
    paths = WikiPaths.from_root(tmp_path)
    calls = {"count": 0}

    monkeypatch.setattr(search_daemon, "daemon_status", lambda paths: {"running": True, "deep": False})
    monkeypatch.setattr(search_daemon, "query_daemon", lambda *args, **kwargs: calls.__setitem__("count", calls["count"] + 1))

    assert query_deep_daemon_if_running(paths, "daemon") is None
    assert calls["count"] == 0

    def fake_query_daemon(paths_arg, query, *, limit, deep):
        calls["count"] += 1
        assert paths_arg.root == paths.root
        assert query == "daemon"
        assert limit == 2
        assert deep is True
        return {
            "ok": True,
            "results": [
                {
                    "path": "wiki/concepts/alpha.md",
                    "title": "Alpha",
                    "snippet": "Warm daemon retrieval.",
                    "score": 1.0,
                    "provider": "qmd",
                }
            ],
        }

    monkeypatch.setattr(search_daemon, "daemon_status", lambda paths: {"running": True, "deep": True})
    monkeypatch.setattr(search_daemon, "query_daemon", fake_query_daemon)

    payload = query_deep_daemon_if_running(paths, "daemon", limit=2)

    assert payload is not None
    assert payload["served_by"] == "search-daemon"
    assert payload["results"][0]["path"] == "wiki/concepts/alpha.md"


def test_qmd_provider_finds_executable_next_to_python(tmp_path, monkeypatch) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    python = bin_dir / "python"
    qmd = bin_dir / "qmd"
    python.write_text("", encoding="utf-8")
    qmd.write_text("", encoding="utf-8")
    monkeypatch.setattr(providers.shutil, "which", lambda name: None)
    monkeypatch.setattr(providers.sys, "executable", str(python))

    provider = QmdSearchProvider(WikiPaths.from_root(tmp_path), "test")

    assert provider.executable == str(qmd)


def test_qmd_provider_can_be_disabled_with_env(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LLMW_DISABLE_QMD", "1")

    provider = QmdSearchProvider(WikiPaths.from_root(tmp_path), "test", executable="qmd")

    assert not provider.available()


def test_qmd_provider_uses_python_sdk_when_available(tmp_path, monkeypatch) -> None:
    paths = WikiPaths.from_root(tmp_path)
    paths.wiki_concepts.mkdir(parents=True)
    paths.index_path.parent.mkdir(parents=True, exist_ok=True)
    paths.index_path.write_text("# Index\n\nsynthesis", encoding="utf-8")
    paths.log_path.write_text("# Log\n\nsynthesis", encoding="utf-8")
    (paths.wiki_concepts / "alpha.md").write_text(
        "---\ntitle: Alpha\ntype: concept\n---\n\n# Alpha\n\nRetrieval synthesis notes.",
        encoding="utf-8",
    )
    fake_collection = FakeQmdCollection()
    monkeypatch.setattr(providers.importlib, "import_module", lambda name: FakeQmdModule(fake_collection))
    provider = QmdSearchProvider(paths, "test", executable=None)
    monkeypatch.setattr(provider, "_run", lambda args: (_ for _ in ()).throw(AssertionError("CLI should not run")))

    results = provider.search("synthesis", limit=3, deep=True)

    assert [result.path for result in results] == ["wiki/concepts/alpha.md"]
    assert results[0].provider == "qmd"
    assert fake_collection.last_rerank is False
    assert set(fake_collection.documents) == {"wiki/concepts/alpha.md"}
    assert paths.qmd_manifest_path.exists()


def test_qmd_provider_sanitizes_question_queries_for_sdk(tmp_path, monkeypatch) -> None:
    paths = WikiPaths.from_root(tmp_path)
    paths.wiki_concepts.mkdir(parents=True)
    paths.index_path.parent.mkdir(parents=True, exist_ok=True)
    paths.index_path.write_text("# Index\n\n", encoding="utf-8")
    paths.log_path.write_text("# Log\n\n", encoding="utf-8")
    (paths.wiki_concepts / "guardrails.md").write_text(
        "---\ntitle: Guardrails\ntype: concept\n---\n\n# Guardrails\n\nAgents use guardrails for safety.",
        encoding="utf-8",
    )
    fake_collection = FakeQmdCollection()
    monkeypatch.setattr(providers.importlib, "import_module", lambda name: FakeQmdModule(fake_collection))
    provider = QmdSearchProvider(paths, "test", executable=None)

    results = provider.search("guardrails?", limit=3, deep=True)

    assert [result.path for result in results] == ["wiki/concepts/guardrails.md"]
    assert fake_collection.last_query == "guardrails"


def test_qmd_backend_cli_env_forces_executable_path(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LLMW_QMD_BACKEND", "cli")
    monkeypatch.setattr(providers.importlib, "import_module", lambda name: FakeQmdModule(FakeQmdCollection()))
    monkeypatch.setattr(providers.shutil, "which", lambda name: None)
    monkeypatch.setattr(providers, "_sibling_executable", lambda name: None)

    provider = QmdSearchProvider(WikiPaths.from_root(tmp_path), "test")

    assert not provider.available()


def test_build_search_service_uses_rg_unless_qmd_requested(tmp_path) -> None:
    paths = WikiPaths.from_root(tmp_path)

    fast = build_search_service(paths, "test", use_qmd=False)
    deep = build_search_service(paths, "test", use_qmd=True)

    assert fast.primary.name == "rg"
    assert deep.primary.name == "qmd"


def test_qmd_provider_times_out_slow_commands(tmp_path) -> None:
    qmd = tmp_path / "qmd"
    qmd.write_text("#!/bin/sh\nsleep 2\n", encoding="utf-8")
    qmd.chmod(0o755)
    provider = QmdSearchProvider(WikiPaths.from_root(tmp_path), "test", executable=str(qmd), timeout_seconds=0.1)

    with pytest.raises(RuntimeError, match="timed out"):
        provider._run(["search"])


class FakeQmdModule:
    def __init__(self, collection):
        self.collection = collection

    def connect(self, db_path, config_overrides=None):
        return FakeQmdClient(self.collection)


class FakeQmdClient:
    def __init__(self, collection):
        self._collection = collection

    def collection(self, name):
        return self._collection


class FakeQmdCollection:
    def __init__(self):
        self.documents = {}
        self.last_rerank = None
        self.last_query = None

    def delete_document(self, document_id):
        self.documents.pop(document_id, None)

    def list_documents(self):
        return sorted(self.documents)

    def add_documents(self, documents):
        for document in documents:
            self.documents[document["document_id"]] = document

    def hybrid_search(self, query, top_k=5, rerank=False):
        self.last_rerank = rerank
        self.last_query = query
        results = []
        for document_id, document in self.documents.items():
            if query.lower() in document["markdown"].lower():
                results.append(
                    FakeQmdResult(
                        document_id=document_id,
                        text=document["markdown"],
                        score=1.0,
                        metadata=document["metadata"],
                    )
                )
        return results[:top_k]


class FakeQmdResult:
    def __init__(self, *, document_id, text, score, metadata):
        self.chunk_ref = FakeChunkRef(document_id)
        self.text = text
        self.score = score
        self.metadata = metadata


class FakeChunkRef:
    def __init__(self, document_id):
        self.document_id = document_id
