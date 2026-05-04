from __future__ import annotations

import asyncio
from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Input, Label, RichLog, SelectionList, Static

from llmw.core.paths import WikiPaths
from llmw.core.models import SourceRecord
from llmw.tui.controller import InboxCandidate, WizardController


class ConfirmScreen(ModalScreen[bool]):
    CSS = """
    ConfirmScreen {
        align: center middle;
    }

    #confirm-box {
        width: 70;
        height: 9;
        border: heavy $accent;
        background: $surface;
        padding: 1 2;
    }

    #confirm-actions {
        height: 3;
        align-horizontal: center;
    }
    """

    def __init__(self, message: str):
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-box"):
            yield Label(self.message)
            with Horizontal(id="confirm-actions"):
                yield Button("Yes", id="confirm-yes", variant="primary")
                yield Button("No", id="confirm-no")

    @on(Button.Pressed, "#confirm-yes")
    def confirm_yes(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#confirm-no")
    def confirm_no(self) -> None:
        self.dismiss(False)


class WizardApp(App[None]):
    CSS = """
    Screen {
        layout: vertical;
    }

    #status {
        height: 1;
        padding: 0 1;
        background: $panel;
    }

    #main {
        height: 1fr;
    }

    #left, #right {
        width: 1fr;
        padding: 1;
    }

    SelectionList {
        height: 1fr;
        border: round $primary;
    }

    #actions {
        height: 3;
        padding: 0 1;
    }

    #search-row {
        height: 3;
        padding: 0 1;
    }

    #search-input {
        width: 1fr;
    }

    #log {
        height: 12;
        border: round $secondary;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("a", "select_all_sources", "Select all"),
        ("c", "clear_source_selection", "Clear"),
        ("enter", "register_selected", "Register"),
        ("i", "ingest_selected", "Ingest"),
        ("h", "run_health", "Health"),
    ]

    def __init__(
        self,
        paths: WikiPaths,
        *,
        provider: str | None = None,
        provider_config: Path | None = None,
        max_chars: int = 12000,
        controller: WizardController | None = None,
    ):
        super().__init__()
        self.paths = paths
        self.controller = controller or WizardController(
            paths,
            provider=provider,
            provider_config=provider_config,
            max_chars=max_chars,
        )

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("", id="status")
        with Horizontal(id="main"):
            with Vertical(id="left"):
                yield Label("Unregistered raw sources")
                yield SelectionList[str](id="inbox")
            with Vertical(id="right"):
                yield Label("Registered sources")
                yield SelectionList[str](id="registered")
        with Horizontal(id="actions"):
            yield Button("Refresh", id="refresh")
            yield Button("Register selected", id="register")
            yield Button("Ingest selected", id="ingest")
            yield Button("Health", id="health")
        with Horizontal(id="search-row"):
            yield Input(placeholder="Search wiki...", id="search-input")
            yield Button("Search", id="search")
        yield RichLog(id="log", wrap=True, highlight=True, markup=True)
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_lists()
        self.write_log("[bold]LLM Wiki wizard ready.[/bold]")

    def refresh_lists(self) -> None:
        candidates = self.controller.scan_unregistered_sources()
        registered = self.controller.registered_sources()
        inbox = self.query_one("#inbox", SelectionList)
        registered_list = self.query_one("#registered", SelectionList)
        inbox.clear_options()
        registered_list.clear_options()
        inbox.add_options([(candidate.label, candidate.rel_path, False) for candidate in candidates])
        registered_list.add_options([(self._record_label(record), record.source_id, False) for record in registered])
        self.query_one("#status", Static).update(
            f"{len(candidates)} unregistered source(s), {len(registered)} registered source(s)"
        )

    def write_log(self, message: str) -> None:
        self.query_one("#log", RichLog).write(message)

    @on(Button.Pressed, "#refresh")
    def refresh_button(self) -> None:
        self.action_refresh()

    @on(Button.Pressed, "#register")
    async def register_button(self) -> None:
        await self.action_register_selected()

    @on(Button.Pressed, "#ingest")
    async def ingest_button(self) -> None:
        await self.action_ingest_selected()

    @on(Button.Pressed, "#health")
    async def health_button(self) -> None:
        await self.action_run_health()

    @on(Button.Pressed, "#search")
    async def search_button(self) -> None:
        await self._run_search()

    @on(Input.Submitted, "#search-input")
    async def search_submitted(self) -> None:
        await self._run_search()

    def action_refresh(self) -> None:
        self.refresh_lists()
        self.write_log("Refreshed source lists.")

    def action_select_all_sources(self) -> None:
        self.query_one("#inbox", SelectionList).select_all()

    def action_clear_source_selection(self) -> None:
        self.query_one("#inbox", SelectionList).deselect_all()

    async def action_register_selected(self) -> None:
        selected = list(self.query_one("#inbox", SelectionList).selected)
        if not selected:
            self.write_log("[yellow]No raw sources selected.[/yellow]")
            return
        self.write_log(f"Registering {len(selected)} source(s)...")
        try:
            records = await asyncio.to_thread(self.controller.register_sources, selected)
        except Exception as exc:
            self.write_log(f"[red]Registration failed: {exc}[/red]")
            return
        for record in records:
            self.write_log(f"[green]Registered[/green] {record.source_id} -> {record.path}")
        self.refresh_lists()

    async def action_ingest_selected(self) -> None:
        selected = list(self.query_one("#registered", SelectionList).selected)
        if not selected:
            pending = self.controller.pending_ingest_sources()
            if not pending:
                self.write_log("[yellow]No registered source selected and no pending source found.[/yellow]")
                return
            selected = [pending[0].source_id]

        for source_id in selected:
            confirmed = await self.push_screen_wait(ConfirmScreen(f"Call LLM provider for {source_id}?"))
            if not confirmed:
                self.write_log(f"Skipped ingest for {source_id}.")
                continue
            self.write_log(f"Running LLM ingest for {source_id}...")
            try:
                result = await asyncio.to_thread(self.controller.ingest_source, source_id)
            except Exception as exc:
                self.write_log(f"[red]Ingest failed for {source_id}: {exc}[/red]")
                continue
            self.write_log(f"[green]Ingested[/green] {source_id}: {len(result.pages)} page(s)")
            for page in result.pages:
                self.write_log(f"  - {page}")
            self.write_log(f"Health after ingest: {result.health_errors} error(s), {result.health_warnings} warning(s)")
        self.refresh_lists()

    async def action_run_health(self) -> None:
        self.write_log("Running health and index checks...")
        try:
            index_current, health = await asyncio.to_thread(self._health_and_index)
        except Exception as exc:
            self.write_log(f"[red]Health check failed: {exc}[/red]")
            return
        self.write_log(f"Index: {'current' if index_current else 'stale'}")
        self.write_log(
            f"Health: {health.errors} error(s), {health.warnings} warning(s), {health.infos} info issue(s)"
        )
        for issue in health.issues[:20]:
            location = f" {issue.path}" if issue.path else ""
            self.write_log(f"{issue.severity.upper()} {issue.code}{location}: {issue.message}")
        if len(health.issues) > 20:
            self.write_log(f"... {len(health.issues) - 20} more issue(s)")

    async def _run_search(self) -> None:
        query = self.query_one("#search-input", Input).value.strip()
        if not query:
            self.write_log("[yellow]Enter a search query first.[/yellow]")
            return
        self.write_log(f"Searching: {query}")
        try:
            results, warning = await asyncio.to_thread(self.controller.search, query)
        except Exception as exc:
            self.write_log(f"[red]Search failed: {exc}[/red]")
            return
        if warning:
            self.write_log(f"[yellow]{warning}[/yellow]")
        if not results:
            self.write_log("No results.")
            return
        for result in results:
            score = f" score={result.score}" if result.score is not None else ""
            self.write_log(f"[bold]{result.path}[/bold]{score}\n{result.snippet}")

    def _health_and_index(self):
        return self.controller.index_current(), self.controller.health_summary()

    @staticmethod
    def _record_label(record: SourceRecord) -> str:
        return f"{record.source_id} [{record.status}] {record.path}"
