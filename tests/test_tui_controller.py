from llmw.core.config import ensure_project_dirs
from llmw.core.paths import WikiPaths
from llmw.sources.registry import add_source
from llmw.tui.controller import WizardController


def test_controller_scans_nested_unregistered_sources(tmp_path) -> None:
    paths = WikiPaths.from_root(tmp_path)
    ensure_project_dirs(paths)
    nested = paths.raw_inbox / "agent" / "note.md"
    nested.parent.mkdir(parents=True)
    nested.write_text("# Note\n\nA nested Markdown source.", encoding="utf-8")
    unsupported = paths.raw_inbox / "agent" / "data.bin"
    unsupported.write_text("binary-ish", encoding="utf-8")

    candidates = WizardController(paths).scan_unregistered_sources()

    assert [candidate.rel_path for candidate in candidates] == ["raw/inbox/agent/note.md"]


def test_controller_filters_registered_original_path(tmp_path) -> None:
    paths = WikiPaths.from_root(tmp_path)
    ensure_project_dirs(paths)
    source = paths.raw_inbox / "note.md"
    source.write_text("# Note\n\nAlready registered.", encoding="utf-8")
    add_source(paths, source, [".md"])

    candidates = WizardController(paths).scan_unregistered_sources()

    assert candidates == []


def test_controller_registers_selected_sources(tmp_path) -> None:
    paths = WikiPaths.from_root(tmp_path)
    ensure_project_dirs(paths)
    source = paths.raw_inbox / "note.md"
    source.write_text("# Note\n\nRegister me.", encoding="utf-8")
    controller = WizardController(paths)

    records = controller.register_sources(["raw/inbox/note.md"])

    assert len(records) == 1
    assert records[0].source_id.startswith("note-")
    assert controller.scan_unregistered_sources() == []
    assert controller.pending_ingest_sources()[0].source_id == records[0].source_id
