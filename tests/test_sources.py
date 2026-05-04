from llmw.core.config import ensure_project_dirs, write_config
from llmw.core.paths import WikiPaths
from llmw.sources.ingest import build_ingest_packet
from llmw.sources.registry import add_source, load_registry


def test_add_source_copies_to_processed_and_deduplicates(tmp_path) -> None:
    paths = WikiPaths.from_root(tmp_path)
    ensure_project_dirs(paths)
    write_config(paths)
    source = tmp_path / "Raw Article.md"
    source.write_text("# Raw Article\n\nUseful content.", encoding="utf-8")

    first = add_source(paths, source, [".md"])
    second = add_source(paths, source, [".md"])
    registry = load_registry(paths)

    assert first.source_id == second.source_id
    assert first.path.startswith("raw/processed/")
    assert (tmp_path / first.path).exists()
    assert list(registry.sources) == [first.source_id]


def test_build_ingest_packet_contains_agent_work(tmp_path) -> None:
    paths = WikiPaths.from_root(tmp_path)
    ensure_project_dirs(paths)
    source = tmp_path / "note.txt"
    source.write_text("A small note about retrieval and synthesis.", encoding="utf-8")
    record = add_source(paths, source, [".txt"])

    packet = build_ingest_packet(paths, record.source_id)

    assert f"source_id: `{record.source_id}`" in packet
    assert "Required Agent Work" in packet
    assert "retrieval and synthesis" in packet
