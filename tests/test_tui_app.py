import asyncio

from textual.widgets import SelectionList
from typer.testing import CliRunner

from llmw.cli.main import app as cli_app
from llmw.core.config import ensure_project_dirs
from llmw.core.paths import WikiPaths
from llmw.tui.app import WizardApp
from llmw.sources.registry import load_registry


def test_wizard_command_is_registered() -> None:
    result = CliRunner().invoke(cli_app, ["--help"])

    assert result.exit_code == 0
    assert "wizard" in result.output


def test_wizard_app_starts_and_lists_sources(tmp_path) -> None:
    async def run_app() -> None:
        paths = WikiPaths.from_root(tmp_path)
        ensure_project_dirs(paths)
        source = paths.raw_inbox / "note.md"
        source.write_text("# Note\n\nTUI source.", encoding="utf-8")
        app = WizardApp(paths)
        async with app.run_test(size=(100, 32)) as pilot:
            await pilot.pause()
            inbox = app.query_one("#inbox", SelectionList)
            assert inbox.option_count == 1

    asyncio.run(run_app())


def test_wizard_app_registers_selected_source(tmp_path) -> None:
    async def run_app() -> None:
        paths = WikiPaths.from_root(tmp_path)
        ensure_project_dirs(paths)
        source = paths.raw_inbox / "note.md"
        source.write_text("# Note\n\nTUI source.", encoding="utf-8")
        app = WizardApp(paths)
        async with app.run_test(size=(100, 32)) as pilot:
            await pilot.pause()
            inbox = app.query_one("#inbox", SelectionList)
            inbox.select_all()
            await app.action_register_selected()
            registry = load_registry(paths)
            assert len(registry.sources) == 1

    asyncio.run(run_app())
