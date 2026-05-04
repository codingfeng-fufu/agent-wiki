from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Annotated

import typer

from llmw import __version__
from llmw.core.paths import WikiPaths


DEFAULT_SERVER_NAME = "llm_wiki"


app = typer.Typer(help="Local tooling for an agent-maintained Markdown wiki.")
source_app = typer.Typer(help="Register and inspect raw sources.")
ingest_app = typer.Typer(help="Create ingest packets and record completed ingest work.")
index_app = typer.Typer(help="Build and check wiki/index.md.")
health_app = typer.Typer(help="Run wiki health checks.")
log_app = typer.Typer(help="Append structured log entries.")
llm_app = typer.Typer(help="Check and use configured LLM providers.")
benchmark_app = typer.Typer(help="Run built-in quality and performance benchmarks.")
search_daemon_app = typer.Typer(help="Manage a warm local search daemon.")
integration_app = typer.Typer(help="Install and test agent runtime integrations.")
codex_integration_app = typer.Typer(help="Manage Codex MCP integration.")
release_app = typer.Typer(help="Run release readiness checks.")
package_app = typer.Typer(help="Build audited local package artifacts.")
install_agent_app = typer.Typer(help="Install LLM Wiki into local agent runtimes.")

app.add_typer(source_app, name="source")
app.add_typer(ingest_app, name="ingest")
app.add_typer(index_app, name="index")
app.add_typer(health_app, name="health")
app.add_typer(log_app, name="log")
app.add_typer(llm_app, name="llm")
app.add_typer(benchmark_app, name="benchmark")
app.add_typer(search_daemon_app, name="search-daemon")
app.add_typer(integration_app, name="integration")
integration_app.add_typer(codex_integration_app, name="codex")
app.add_typer(release_app, name="release")
app.add_typer(package_app, name="package")
app.add_typer(install_agent_app, name="install-agent")


def _paths(root: Path | None = None) -> WikiPaths:
    return WikiPaths.from_root(root or Path.cwd())


def _abort(message: str) -> None:
    typer.secho(f"Error: {message}", fg=typer.colors.RED, err=True)
    raise typer.Exit(1)


def _error_message(exc: Exception) -> str:
    if isinstance(exc, KeyError) and exc.args:
        return str(exc.args[0])
    return str(exc)


def _json_ok(payload: dict) -> None:
    typer.echo(json.dumps({"ok": True, **payload}, indent=2, ensure_ascii=False))


def _abort_json(exc: Exception, *, code: str = "error") -> None:
    typer.echo(
        json.dumps(
            {"ok": False, "error": {"code": code, "message": _error_message(exc)}},
            indent=2,
            ensure_ascii=False,
        )
    )
    raise typer.Exit(1)


def load_provider_registry(*args, **kwargs):
    from llmw.llm.config import load_provider_registry as _load_provider_registry

    return _load_provider_registry(*args, **kwargs)


def run_health_audit(*args, **kwargs):
    from llmw.llm.health import run_health_audit as _run_health_audit

    return _run_health_audit(*args, **kwargs)


def run_ingest(*args, **kwargs):
    from llmw.llm.ingest import run_ingest as _run_ingest

    return _run_ingest(*args, **kwargs)


def run_query(*args, **kwargs):
    from llmw.llm.query import run_query as _run_query

    return _run_query(*args, **kwargs)


class _StaticSearchService:
    def __init__(self, results_payload: list[dict], warning: str | None = None):
        self.results_payload = results_payload
        self.warning = warning

    def search(self, query: str, *, limit: int = 10, deep: bool = False):
        from llmw.core.search_result import SearchResult

        return [SearchResult(**item) for item in self.results_payload[:limit]], self.warning


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Annotated[bool, typer.Option("--version", help="Show version and exit.")] = False,
) -> None:
    if version:
        typer.echo(f"llmw {__version__}")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@app.command()
def init(
    root: Annotated[Path, typer.Option("--root", "-r", help="Project root.")] = Path("."),
    force: Annotated[bool, typer.Option("--force", help="Overwrite generated config/index/log files.")] = False,
) -> None:
    from llmw.core.config import ensure_project_dirs, write_config
    from llmw.core.settings import LLMWConfig
    from llmw.wiki.index import build_index_content

    paths = _paths(root)
    ensure_project_dirs(paths)
    write_config(paths, LLMWConfig(), overwrite=force)
    _write_bootstrap_files(paths, overwrite=force)
    typer.echo(f"Initialized LLM Wiki at {paths.root}")


@app.command()
def context(
    root: Annotated[Path, typer.Option("--root", "-r", help="Project root.")] = Path("."),
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON.")] = False,
) -> None:
    from llmw.agent.context import build_context

    try:
        payload = build_context(_paths(root))
    except Exception as exc:
        if json_output:
            _abort_json(exc, code="context-failed")
        _abort(_error_message(exc))
    if json_output:
        _json_ok({"context": payload})
        return
    typer.echo(f"Root: {payload['root']}")
    typer.echo(f"Wiki pages: {payload['wiki']['pages']}")
    typer.echo(f"Sources: {payload['sources']['total']}")
    typer.echo(
        "Health: "
        f"{payload['health']['errors']} error(s), "
        f"{payload['health']['warnings']} warning(s), "
        f"{payload['health']['infos']} info issue(s)"
    )


@app.command()
def doctor(
    root: Annotated[Path, typer.Option("--root", "-r", help="Project root.")] = Path("."),
    codex: Annotated[bool, typer.Option("--codex/--no-codex", help="Include Codex MCP configuration checks.")] = True,
    probe_mcp: Annotated[bool, typer.Option("--probe-mcp", help="Start the MCP server and run a direct protocol probe.")] = False,
    strict: Annotated[bool, typer.Option("--strict", help="Treat warnings as failures.")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON.")] = False,
) -> None:
    from llmw.doctor import format_doctor, run_doctor

    try:
        payload = run_doctor(_paths(root), include_codex=codex, probe_mcp=probe_mcp, strict=strict)
    except Exception as exc:
        if json_output:
            _abort_json(exc, code="doctor-failed")
        _abort(_error_message(exc))
    if json_output:
        output = {"ok": payload["ok"], "doctor": payload}
        if not payload["ok"]:
            output["error"] = {
                "code": "doctor-failed",
                "message": f"doctor readiness is {payload['readiness']}",
            }
        typer.echo(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        typer.echo(format_doctor(payload))
    if not payload["ok"]:
        raise typer.Exit(1)


@release_app.command("check")
def release_check(
    root: Annotated[Path, typer.Option("--root", "-r", help="Project root.")] = Path("."),
    tests: Annotated[bool, typer.Option("--tests/--no-tests", help="Run pytest when tests/ exists.")] = True,
    benchmark: Annotated[bool, typer.Option("--benchmark/--no-benchmark", help="Run search benchmark gates.")] = True,
    sdist: Annotated[bool, typer.Option("--sdist/--no-sdist", help="Build and audit a source distribution.")] = False,
    codex: Annotated[bool, typer.Option("--codex/--no-codex", help="Include Codex MCP config readiness.")] = True,
    probe_mcp: Annotated[bool, typer.Option("--probe-mcp", help="Start the MCP server and run a direct protocol probe.")] = False,
    strict: Annotated[bool, typer.Option("--strict/--no-strict", help="Treat warnings as release failures.")] = True,
    search_provider: Annotated[str, typer.Option("--search-provider", help="Search benchmark provider.")] = "python",
    search_top_k: Annotated[int, typer.Option("--search-top-k", min=1, max=20, help="Search benchmark top-k.")] = 5,
    fail_under_f1: Annotated[float, typer.Option("--fail-under-f1", help="Minimum benchmark F1.")] = 0.20,
    fail_under_recall: Annotated[float, typer.Option("--fail-under-recall", help="Minimum benchmark recall.")] = 0.60,
    fail_under_hit_rate: Annotated[float, typer.Option("--fail-under-hit-rate", help="Minimum benchmark hit rate.")] = 0.60,
    timeout_seconds: Annotated[float, typer.Option("--timeout", min=1, help="Timeout for subprocess checks.")] = 180,
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON.")] = False,
) -> None:
    from llmw.release import format_release_report, run_release_check

    try:
        payload = run_release_check(
            _paths(root),
            include_tests=tests,
            include_benchmark=benchmark,
            include_sdist=sdist,
            include_codex=codex,
            probe_mcp=probe_mcp,
            strict=strict,
            search_provider=search_provider,
            search_top_k=search_top_k,
            fail_under_f1=fail_under_f1,
            fail_under_recall=fail_under_recall,
            fail_under_hit_rate=fail_under_hit_rate,
            timeout_seconds=timeout_seconds,
        )
    except Exception as exc:
        if json_output:
            _abort_json(exc, code="release-check-failed")
        _abort(_error_message(exc))
    if json_output:
        output = {"ok": payload["ok"], "release": payload}
        if not payload["ok"]:
            output["error"] = {
                "code": "release-check-failed",
                "message": f"release readiness is {payload['readiness']}",
            }
        typer.echo(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        typer.echo(format_release_report(payload))
    if not payload["ok"]:
        raise typer.Exit(1)


@package_app.command("build")
def package_build(
    root: Annotated[Path, typer.Option("--root", "-r", help="Project root.")] = Path("."),
    out_dir: Annotated[Path, typer.Option("--out-dir", help="Output directory for artifacts and package report.")] = Path("dist"),
    sdist: Annotated[bool, typer.Option("--sdist/--no-sdist", help="Build source distribution.")] = True,
    wheel: Annotated[bool, typer.Option("--wheel/--no-wheel", help="Build wheel distribution.")] = True,
    check: Annotated[bool, typer.Option("--check/--no-check", help="Run release checks before building.")] = True,
    probe_mcp: Annotated[bool, typer.Option("--probe-mcp", help="Include MCP probe in pre-build release check.")] = False,
    strict: Annotated[bool, typer.Option("--strict/--no-strict", help="Treat warnings as pre-build release failures.")] = True,
    timeout_seconds: Annotated[float, typer.Option("--timeout", min=1, help="Timeout for subprocess checks.")] = 180,
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON.")] = False,
) -> None:
    from llmw.package import build_package, format_package_report

    try:
        payload = build_package(
            _paths(root),
            out_dir=out_dir,
            sdist=sdist,
            wheel=wheel,
            check=check,
            probe_mcp=probe_mcp,
            strict=strict,
            timeout_seconds=timeout_seconds,
        )
    except Exception as exc:
        if json_output:
            _abort_json(exc, code="package-build-failed")
        _abort(_error_message(exc))
    if json_output:
        output = {"ok": payload["ok"], "package": payload}
        if not payload["ok"]:
            output["error"] = {
                "code": "package-build-failed",
                "message": str(payload.get("error") or "package build failed"),
            }
        typer.echo(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        typer.echo(format_package_report(payload))
    if not payload["ok"]:
        raise typer.Exit(1)


@install_agent_app.command("codex")
def install_agent_codex(
    root: Annotated[Path, typer.Option("--root", "-r", help="Project root.")] = Path("."),
    server_name: Annotated[str, typer.Option("--server-name", help="Codex MCP server name.")] = DEFAULT_SERVER_NAME,
    test: Annotated[bool, typer.Option("--test/--no-test", help="Probe the MCP server after installation.")] = True,
    timeout: Annotated[float, typer.Option("--timeout", min=1, help="MCP probe timeout in seconds.")] = 15,
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON.")] = False,
) -> None:
    from llmw.integrations.codex import install_codex_mcp, test_codex_mcp

    try:
        paths = _paths(root)
        installed = install_codex_mcp(paths, server_name=server_name)
        probe = test_codex_mcp(paths, server_name=server_name, timeout=timeout) if test else None
    except Exception as exc:
        if json_output:
            _abort_json(exc, code="install-agent-codex-failed")
        _abort(_error_message(exc))
    payload = {"agent": "codex", "installed": installed, "test": probe}
    ok = probe is None or bool(probe.get("ok"))
    if json_output:
        output = {"ok": ok, "install_agent": payload}
        if not ok:
            output["error"] = {
                "code": "install-agent-codex-failed",
                "message": str((probe or {}).get("error") or "Codex MCP probe failed"),
            }
        typer.echo(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        typer.echo(f"Installed Codex MCP server: {installed['server_name']}")
        typer.echo(f"Config: {installed['config_path']}")
        if installed["backup_path"]:
            typer.echo(f"Backup: {installed['backup_path']}")
        if probe is not None:
            typer.echo("Probe: passed" if ok else f"Probe: failed ({probe.get('error')})")
    if not ok:
        raise typer.Exit(1)


@app.command("next")
def next_tasks(
    root: Annotated[Path, typer.Option("--root", "-r", help="Project root.")] = Path("."),
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON.")] = False,
) -> None:
    from llmw.agent.tools import build_next_tasks

    try:
        tasks = build_next_tasks(_paths(root))
    except Exception as exc:
        if json_output:
            _abort_json(exc, code="next-failed")
        _abort(_error_message(exc))
    if json_output:
        _json_ok({"tasks": tasks})
        return
    for task in tasks:
        typer.echo(f"- [{task['priority']}] {task['title']}")
        if task.get("command"):
            typer.echo(f"  {task['command']}")


@app.command("plan")
def plan_command(
    goal: Annotated[str, typer.Argument(help="Goal to turn into a safe tool plan.")],
    root: Annotated[Path, typer.Option("--root", "-r", help="Project root.")] = Path("."),
    save: Annotated[bool, typer.Option("--save", help="Save plan under .llmw/plans/.")] = False,
    preview: Annotated[bool, typer.Option("--preview", help="Include a dry-run preview of the generated plan.")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON.")] = False,
) -> None:
    from llmw.agent.tools import create_plan, preview_plan, save_plan

    paths = _paths(root)
    try:
        plan = create_plan(paths, goal)
        saved_plan = save_plan(paths, plan) if save else None
        preview_payload = preview_plan(paths, plan) if preview else None
    except Exception as exc:
        if json_output:
            _abort_json(exc, code="plan-failed")
        _abort(_error_message(exc))
    payload = {"plan": plan.model_dump(), "saved_plan": saved_plan, "preview": preview_payload}
    if json_output:
        _json_ok(payload)
        return
    typer.echo(f"Plan: {plan.plan_id}")
    typer.echo(f"Goal: {plan.goal}")
    for step in plan.steps:
        typer.echo(f"- {step.id}: {step.action} risk={step.risk} writes={', '.join(step.writes) or 'none'}")
    if saved_plan:
        typer.echo(f"Saved: {saved_plan}")


@app.command("apply")
def apply_command(
    plan_file: Annotated[Path, typer.Argument(help="Plan JSON file produced by `llmw plan --save`.")],
    root: Annotated[Path, typer.Option("--root", "-r", help="Project root.")] = Path("."),
    provider: Annotated[str | None, typer.Option("--provider", help="Provider name from provider config.")] = None,
    provider_config: Annotated[Path | None, typer.Option("--provider-config", help="Provider config JSON path.")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Validate and preview the plan without writing files.")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON.")] = False,
) -> None:
    from llmw.agent.tools import apply_plan as apply_tool_plan
    from llmw.agent.tools import load_plan

    paths = _paths(root)
    try:
        plan = load_plan(plan_file)
        needs_provider = any(step.action in {"query_save", "health_audit_save"} for step in plan.steps)
        provider_config_model = None
        if needs_provider:
            registry = load_provider_registry(paths, provider_config)
            provider_config_model = registry.get(provider)
        result = apply_tool_plan(paths, plan, provider=provider_config_model, dry_run=dry_run)
    except Exception as exc:
        if json_output:
            _abort_json(exc, code="apply-failed")
        _abort(_error_message(exc))
    if json_output:
        _json_ok(result)
        return
    if dry_run:
        typer.echo(f"Dry-run preview for {result['plan_id']} ({len(result['results'])} step(s))")
        return
    typer.echo(f"Applied {result['applied']} step(s) from {result['plan_id']}")


@app.command()
def maintain(
    root: Annotated[Path, typer.Option("--root", "-r", help="Project root.")] = Path("."),
    provider: Annotated[str | None, typer.Option("--provider", help="Provider name from provider config.")] = None,
    provider_config: Annotated[Path | None, typer.Option("--provider-config", help="Provider config JSON path.")] = None,
    audit: Annotated[bool, typer.Option("--audit/--no-audit", help="Run LLM semantic audit as part of maintenance planning.")] = True,
    save_plan_file: Annotated[bool, typer.Option("--save-plan/--no-save-plan", help="Save generated plan under .llmw/plans/.")] = True,
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON.")] = False,
) -> None:
    from llmw.agent.maintain import run_maintain

    paths = _paths(root)
    try:
        provider_config_model = None
        audit_warning = None
        if audit:
            try:
                registry = load_provider_registry(paths, provider_config)
                provider_config_model = registry.get(provider)
            except Exception as exc:
                audit_warning = _error_message(exc)
        maintenance = run_maintain(
            paths,
            provider=provider_config_model,
            audit=audit,
            save_plan_file=save_plan_file,
            audit_warning=audit_warning,
        )
    except Exception as exc:
        if json_output:
            _abort_json(exc, code="maintain-failed")
        _abort(_error_message(exc))
    if json_output:
        _json_ok({"maintenance": maintenance})
        return
    typer.echo(f"Tasks: {len(maintenance['tasks'])}")
    typer.echo(f"Plan: {maintenance['plan']['plan_id']} ({len(maintenance['plan']['steps'])} step(s))")
    if maintenance["saved_plan"]:
        typer.echo(f"Saved plan: {maintenance['saved_plan']}")
    for warning in maintenance["warnings"]:
        typer.secho(f"Warning: {warning}", fg=typer.colors.YELLOW)


@source_app.command("add")
def source_add(
    path: Annotated[Path, typer.Argument(help="Markdown, text, or PDF source file.")],
    root: Annotated[Path, typer.Option("--root", "-r", help="Project root.")] = Path("."),
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON.")] = False,
) -> None:
    from llmw.core.config import ensure_project_dirs, load_config
    from llmw.sources.registry import add_source

    paths = _paths(root)
    ensure_project_dirs(paths)
    try:
        config = load_config(paths)
        record = add_source(paths, path, config.source_extensions)
    except Exception as exc:
        if json_output:
            _abort_json(exc, code="source-add-failed")
        _abort(_error_message(exc))
    if json_output:
        _json_ok({"source": record.model_dump()})
        return
    typer.echo(json.dumps(record.model_dump(), indent=2, ensure_ascii=False))


@source_app.command("list")
def source_list(
    root: Annotated[Path, typer.Option("--root", "-r", help="Project root.")] = Path("."),
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON.")] = False,
) -> None:
    from llmw.sources.registry import load_registry

    try:
        registry = load_registry(_paths(root))
    except Exception as exc:
        if json_output:
            _abort_json(exc, code="source-list-failed")
        _abort(_error_message(exc))
    if json_output:
        _json_ok({"sources": [record.model_dump() for record in registry.sources.values()]})
        return
    if not registry.sources:
        typer.echo("No sources registered.")
        return
    for record in registry.sources.values():
        typer.echo(f"{record.source_id}\t{record.status}\t{record.path}")


@ingest_app.command("packet")
def ingest_packet(
    source_id: Annotated[str, typer.Argument(help="Registered source id.")],
    root: Annotated[Path, typer.Option("--root", "-r", help="Project root.")] = Path("."),
    max_chars: Annotated[int, typer.Option("--max-chars", help="Maximum extracted text chars.")] = 12000,
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON.")] = False,
) -> None:
    from llmw.sources.ingest import build_ingest_packet

    try:
        packet = build_ingest_packet(_paths(root), source_id, max_chars=max_chars)
    except Exception as exc:
        if json_output:
            _abort_json(exc, code="ingest-packet-failed")
        _abort(_error_message(exc))
    if json_output:
        _json_ok({"source_id": source_id, "packet": packet})
        return
    typer.echo(packet)


@ingest_app.command("record")
def ingest_record(
    source_id: Annotated[str, typer.Argument(help="Registered source id.")],
    pages: Annotated[list[str], typer.Option("--page", help="Wiki page updated during ingest.")] = [],
    note: Annotated[str, typer.Option("--note", help="Optional log note.")] = "",
    root: Annotated[Path, typer.Option("--root", "-r", help="Project root.")] = Path("."),
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON.")] = False,
) -> None:
    from llmw.sources.registry import get_source, update_source
    from llmw.wiki.index import rebuild_index
    from llmw.wiki.log import append_log

    paths = _paths(root)
    try:
        record = get_source(paths, source_id)
        record.status = "ingested"
        record.pages = pages
        update_source(paths, record)
        append_log(paths, "Ingest", record.title, note or f"Processed `{source_id}`. Updated pages: {', '.join(pages) or 'none listed'}.")
        rebuild_index(paths)
    except Exception as exc:
        if json_output:
            _abort_json(exc, code="ingest-record-failed")
        _abort(_error_message(exc))
    if json_output:
        _json_ok({"source_id": source_id, "pages": pages})
        return
    typer.echo(f"Recorded ingest for {source_id}")


@ingest_app.command("run")
def ingest_run(
    source_id: Annotated[str, typer.Argument(help="Registered source id.")],
    root: Annotated[Path, typer.Option("--root", "-r", help="Project root.")] = Path("."),
    provider: Annotated[str | None, typer.Option("--provider", help="Provider name from provider config.")] = None,
    provider_config: Annotated[Path | None, typer.Option("--provider-config", help="Provider config JSON path.")] = None,
    max_chars: Annotated[int, typer.Option("--max-chars", help="Maximum extracted source chars.")] = 12000,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Call the model but do not write generated pages.")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON.")] = False,
) -> None:
    paths = _paths(root)
    try:
        registry = load_provider_registry(paths, provider_config)
        provider_config_model = registry.get(provider)
        result = run_ingest(
            paths,
            source_id,
            provider=provider_config_model,
            dry_run=dry_run,
            max_chars=max_chars,
        )
    except Exception as exc:
        if json_output:
            _abort_json(exc, code="ingest-run-failed")
        _abort(_error_message(exc))
    payload = {
        "source_id": result.source_id,
        "pages": result.pages,
        "log_note": result.log_note,
        "health_errors": result.health_errors,
        "health_warnings": result.health_warnings,
        "dry_run": result.dry_run,
    }
    if json_output:
        _json_ok(payload)
        return
    action = "Generated" if dry_run else "Wrote"
    typer.echo(f"{action} {len(result.pages)} page(s) for {source_id}")
    for page in result.pages:
        typer.echo(f"- {page}")
    if not dry_run:
        typer.echo(f"Health: {result.health_errors} error(s), {result.health_warnings} warning(s)")


@benchmark_app.command("search")
def benchmark_search(
    root: Annotated[Path, typer.Option("--root", "-r", help="Project root.")] = Path("."),
    provider: Annotated[str, typer.Option("--provider", help="Search provider: python, rg, qmd, or llmw.")] = "python",
    top_k: Annotated[int, typer.Option("--top-k", min=1, max=50, help="Number of results per query.")] = 5,
    include_special: Annotated[bool, typer.Option("--include-special", help="Include wiki/index.md and wiki/log.md.")] = False,
    fail_under_f1: Annotated[float | None, typer.Option("--fail-under-f1", help="Fail if F1 is below threshold.")] = None,
    fail_under_recall: Annotated[float | None, typer.Option("--fail-under-recall", help="Fail if recall is below threshold.")] = None,
    fail_under_hit_rate: Annotated[float | None, typer.Option("--fail-under-hit-rate", help="Fail if hit rate is below threshold.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON.")] = False,
) -> None:
    from llmw.search.benchmark import assert_benchmark_gates, format_benchmark_summary, run_search_benchmark

    try:
        payload = run_search_benchmark(
            _paths(root),
            provider=provider,
            top_k=top_k,
            include_special=include_special,
        )
        assert_benchmark_gates(
            payload["summary"],
            fail_under_f1=fail_under_f1,
            fail_under_recall=fail_under_recall,
            fail_under_hit_rate=fail_under_hit_rate,
        )
    except Exception as exc:
        if json_output:
            _abort_json(exc, code="benchmark-failed")
        _abort(_error_message(exc))
    if json_output:
        _json_ok({"benchmark": payload})
        return
    typer.echo(format_benchmark_summary(payload))


@benchmark_app.command("perf")
def benchmark_perf(
    root: Annotated[Path, typer.Option("--root", "-r", help="Project root.")] = Path("."),
    repeat: Annotated[int, typer.Option("--repeat", min=1, max=20, help="Number of repeated runs per fast check.")] = 3,
    limit: Annotated[int, typer.Option("--limit", "-n", min=1, max=20, help="Search result limit.")] = 3,
    include_deep: Annotated[bool, typer.Option("--include-deep", help="Include one qmd deep-search run per query.")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON.")] = False,
) -> None:
    from llmw.perf import format_perf_report, run_perf_benchmark

    try:
        payload = run_perf_benchmark(_paths(root), repeat=repeat, limit=limit, include_deep=include_deep)
    except Exception as exc:
        if json_output:
            _abort_json(exc, code="perf-benchmark-failed")
        _abort(_error_message(exc))
    if json_output:
        _json_ok({"performance": payload})
        return
    typer.echo(format_perf_report(payload))


@app.command()
def search(
    query: Annotated[str, typer.Argument(help="Search query.")],
    root: Annotated[Path, typer.Option("--root", "-r", help="Project root.")] = Path("."),
    limit: Annotated[int, typer.Option("--limit", "-n", min=1, max=50, help="Maximum results.")] = 10,
    deep: Annotated[bool, typer.Option("--deep", help="Use qmd hybrid query when available.")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON.")] = False,
) -> None:
    from llmw.core.config import load_config
    from llmw.search.providers import build_search_service, recommend_search_strategy

    paths = _paths(root)
    try:
        daemon_payload = None
        if deep:
            from llmw.search.daemon import query_deep_daemon_if_running

            daemon_payload = query_deep_daemon_if_running(paths, query, limit=limit)
        if daemon_payload is not None:
            warning = daemon_payload.get("warning")
            strategy = daemon_payload.get("strategy") or recommend_search_strategy(query, deep=True)
            results_payload = daemon_payload.get("results", [])
            served_by = daemon_payload.get("served_by")
            results = []
        else:
            config = load_config(paths)
            service = build_search_service(paths, config.qmd_collection, use_qmd=deep)
            results, warning = service.search(query, limit=limit, deep=deep)
            strategy = recommend_search_strategy(query, deep=deep)
            results_payload = [r.model_dump() for r in results]
            served_by = None
    except Exception as exc:
        if json_output:
            _abort_json(exc, code="search-failed")
        _abort(_error_message(exc))
    if json_output:
        payload = {"warning": warning, "strategy": strategy, "results": results_payload}
        if served_by:
            payload["served_by"] = served_by
        _json_ok(payload)
        return
    if served_by:
        typer.secho(f"Using {served_by}.", fg=typer.colors.BLUE, err=True)
    if warning:
        typer.secho(warning, fg=typer.colors.YELLOW, err=True)
    if strategy["deep_recommended"] and not deep:
        typer.secho(f"Hint: {strategy['reason']}", fg=typer.colors.BLUE, err=True)
    for item in results_payload:
        score_value = item.get("score") if isinstance(item, dict) else None
        score = f" score={score_value}" if score_value is not None else ""
        typer.echo(f"{item.get('path', '')}{score}\n  {item.get('snippet', '')}")


@app.command("search-server")
def search_server(
    root: Annotated[Path, typer.Option("--root", "-r", help="Project root.")] = Path("."),
    deep: Annotated[bool, typer.Option("--deep", help="Keep qmd hybrid search warm for repeated requests.")] = False,
    limit: Annotated[int, typer.Option("--limit", "-n", min=1, max=50, help="Default result limit.")] = 5,
) -> None:
    from llmw.search.server import serve_search_lines

    try:
        serve_search_lines(_paths(root), deep=deep, default_limit=limit)
    except Exception as exc:
        _abort(_error_message(exc))


@search_daemon_app.command("start")
def search_daemon_start(
    root: Annotated[Path, typer.Option("--root", "-r", help="Project root.")] = Path("."),
    deep: Annotated[bool, typer.Option("--deep", help="Keep qmd hybrid search warm.")] = False,
    limit: Annotated[int, typer.Option("--limit", "-n", min=1, max=50, help="Default result limit.")] = 5,
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON.")] = False,
) -> None:
    from llmw.search.daemon import start_daemon

    try:
        status = start_daemon(_paths(root), deep=deep, default_limit=limit)
    except Exception as exc:
        if json_output:
            _abort_json(exc, code="search-daemon-start-failed")
        _abort(_error_message(exc))
    if json_output:
        _json_ok({"daemon": status})
        return
    typer.echo(f"Search daemon running pid={status['pid']} socket={status['socket_path']}")


@search_daemon_app.command("status")
def search_daemon_status(
    root: Annotated[Path, typer.Option("--root", "-r", help="Project root.")] = Path("."),
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON.")] = False,
) -> None:
    from llmw.search.daemon import daemon_status

    try:
        status = daemon_status(_paths(root))
    except Exception as exc:
        if json_output:
            _abort_json(exc, code="search-daemon-status-failed")
        _abort(_error_message(exc))
    if json_output:
        _json_ok({"daemon": status})
        return
    state = "running" if status["running"] else "stopped"
    typer.echo(f"Search daemon: {state}")
    typer.echo(f"Socket: {status['socket_path']}")
    typer.echo(f"Log: {status['log_path']}")


@search_daemon_app.command("stop")
def search_daemon_stop(
    root: Annotated[Path, typer.Option("--root", "-r", help="Project root.")] = Path("."),
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON.")] = False,
) -> None:
    from llmw.search.daemon import stop_daemon

    try:
        status = stop_daemon(_paths(root))
    except Exception as exc:
        if json_output:
            _abort_json(exc, code="search-daemon-stop-failed")
        _abort(_error_message(exc))
    if json_output:
        _json_ok({"daemon": status})
        return
    typer.echo("Search daemon stopped." if status.get("stopped") else "Search daemon was not running.")


@search_daemon_app.command("query")
def search_daemon_query(
    query: Annotated[str, typer.Argument(help="Search query.")],
    root: Annotated[Path, typer.Option("--root", "-r", help="Project root.")] = Path("."),
    limit: Annotated[int, typer.Option("--limit", "-n", min=1, max=50, help="Maximum results.")] = 5,
    deep: Annotated[bool, typer.Option("--deep", help="Force deep mode for this request.")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON.")] = False,
) -> None:
    from llmw.search.daemon import query_daemon

    try:
        payload = query_daemon(_paths(root), query, limit=limit, deep=True if deep else None)
        if payload.get("ok") is False:
            error = payload.get("error") or {}
            raise RuntimeError(str(error.get("message") or "search daemon query failed"))
    except Exception as exc:
        if json_output:
            _abort_json(exc, code="search-daemon-query-failed")
        _abort(_error_message(exc))
    if json_output:
        _json_ok(payload)
        return
    for item in payload.get("results", []):
        typer.echo(f"{item['path']}\n  {item['snippet']}")


@codex_integration_app.command("status")
def codex_integration_status(
    root: Annotated[Path, typer.Option("--root", "-r", help="Project root.")] = Path("."),
    server_name: Annotated[str, typer.Option("--server-name", help="Codex MCP server name.")] = DEFAULT_SERVER_NAME,
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON.")] = False,
) -> None:
    from llmw.integrations.codex import codex_status

    try:
        payload = codex_status(_paths(root), server_name=server_name)
    except Exception as exc:
        if json_output:
            _abort_json(exc, code="codex-status-failed")
        _abort(_error_message(exc))
    if json_output:
        _json_ok({"codex": payload})
        return
    typer.echo(f"Codex found: {payload['codex_found']}")
    typer.echo(f"Server configured: {payload['configured']}")
    typer.echo(f"Command matches: {payload['command_matches']}")
    typer.echo(f"Args match: {payload['args_match']}")
    typer.echo(f"Approval mode: {payload['approval_mode'] or 'missing'}")
    typer.echo(f"Ready: {payload['ready']}")
    if not payload["ready"]:
        typer.echo("\nRecommended config:")
        typer.echo(payload["config_snippet"])


@codex_integration_app.command("install")
def codex_integration_install(
    root: Annotated[Path, typer.Option("--root", "-r", help="Project root.")] = Path("."),
    server_name: Annotated[str, typer.Option("--server-name", help="Codex MCP server name.")] = DEFAULT_SERVER_NAME,
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON.")] = False,
) -> None:
    from llmw.integrations.codex import install_codex_mcp

    try:
        payload = install_codex_mcp(_paths(root), server_name=server_name)
    except Exception as exc:
        if json_output:
            _abort_json(exc, code="codex-install-failed")
        _abort(_error_message(exc))
    if json_output:
        _json_ok({"codex": payload})
        return
    typer.echo(f"Installed Codex MCP server: {payload['server_name']}")
    typer.echo(f"Config: {payload['config_path']}")
    if payload["backup_path"]:
        typer.echo(f"Backup: {payload['backup_path']}")


@codex_integration_app.command("test")
def codex_integration_test(
    root: Annotated[Path, typer.Option("--root", "-r", help="Project root.")] = Path("."),
    server_name: Annotated[str, typer.Option("--server-name", help="Codex MCP server name.")] = DEFAULT_SERVER_NAME,
    timeout: Annotated[float, typer.Option("--timeout", min=1, help="MCP probe timeout in seconds.")] = 15,
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON.")] = False,
) -> None:
    from llmw.integrations.codex import test_codex_mcp

    try:
        payload = test_codex_mcp(_paths(root), server_name=server_name, timeout=timeout)
    except Exception as exc:
        if json_output:
            _abort_json(exc, code="codex-test-failed")
        _abort(_error_message(exc))
    if json_output:
        if payload.get("ok"):
            _json_ok({"codex": payload})
        else:
            _abort_json(RuntimeError(str(payload.get("error") or "codex MCP test failed")), code="codex-test-failed")
        return
    if payload.get("ok"):
        probe = payload.get("probe") or {}
        typer.echo(f"Codex MCP probe passed. tools={probe.get('tools_count')} wiki_pages={probe.get('wiki_pages')}")
        return
    typer.echo(f"Codex MCP probe failed: {payload.get('error') or (payload.get('probe') or {}).get('error')}")
    raise typer.Exit(1)


@app.command()
def mcp(
    root: Annotated[Path, typer.Option("--root", "-r", help="Project root.")] = Path("."),
) -> None:
    from llmw.mcp.server import serve_mcp_stdio

    try:
        serve_mcp_stdio(_paths(root))
    except Exception as exc:
        _abort(_error_message(exc))


@app.command()
def query(
    question: Annotated[str, typer.Argument(help="Question to answer from the maintained wiki.")],
    root: Annotated[Path, typer.Option("--root", "-r", help="Project root.")] = Path("."),
    provider: Annotated[str | None, typer.Option("--provider", help="Provider name from provider config.")] = None,
    provider_config: Annotated[Path | None, typer.Option("--provider-config", help="Provider config JSON path.")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", min=1, max=20, help="Maximum wiki pages to use as evidence.")] = 5,
    deep: Annotated[bool, typer.Option("--deep", help="Use qmd reranking when available.")] = False,
    save: Annotated[bool, typer.Option("--save", help="Save the answer under wiki/outputs/ and log it.")] = False,
    max_page_chars: Annotated[int, typer.Option("--max-page-chars", min=500, help="Maximum chars to include from each evidence page.")] = 4000,
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON.")] = False,
) -> None:
    from llmw.core.config import load_config
    from llmw.search.providers import build_search_service

    paths = _paths(root)
    try:
        registry = load_provider_registry(paths, provider_config)
        provider_config_model = registry.get(provider)
        daemon_payload = None
        if deep:
            from llmw.search.daemon import query_deep_daemon_if_running

            daemon_payload = query_deep_daemon_if_running(paths, question, limit=max(limit * 3, limit))
        if daemon_payload is not None:
            service = _StaticSearchService(
                daemon_payload.get("results", []),
                daemon_payload.get("warning"),
            )
        else:
            config = load_config(paths)
            service = build_search_service(paths, config.qmd_collection, use_qmd=deep)
        result = run_query(
            paths,
            question,
            provider=provider_config_model,
            limit=limit,
            deep=deep,
            save=save,
            max_page_chars=max_page_chars,
            search_service=service,
        )
    except Exception as exc:
        if json_output:
            _abort_json(exc, code="query-failed")
        _abort(_error_message(exc))

    payload = asdict(result)
    if json_output:
        _json_ok(payload)
        return
    if result.warning:
        typer.secho(result.warning, fg=typer.colors.YELLOW, err=True)
    typer.echo(result.answer)
    typer.echo("\nEvidence pages:")
    for page in result.pages:
        typer.echo(f"- {page.title} ({page.path})")
    typer.echo(f"\nModel: {result.model}")
    if result.saved_page:
        typer.echo(f"Saved: {result.saved_page}")


@app.command()
def agent(
    root: Annotated[Path, typer.Option("--root", "-r", help="Project root.")] = Path("."),
    provider: Annotated[str | None, typer.Option("--provider", help="Provider name from provider config.")] = None,
    provider_config: Annotated[Path | None, typer.Option("--provider-config", help="Provider config JSON path.")] = None,
    deep: Annotated[bool, typer.Option("--deep", help="Use qmd search for search/query actions.")] = False,
    session_log: Annotated[bool, typer.Option("--session-log/--no-session-log", help="Write local session summaries under .llmw/sessions/.")] = True,
) -> None:
    from llmw.agent.session import AgentSession

    AgentSession(
        _paths(root),
        provider=provider,
        provider_config=provider_config,
        deep=deep,
        session_log=session_log,
    ).run()


@app.command()
def wizard(
    root: Annotated[Path, typer.Option("--root", "-r", help="Project root.")] = Path("."),
    provider: Annotated[str | None, typer.Option("--provider", help="Provider name from provider config.")] = None,
    provider_config: Annotated[Path | None, typer.Option("--provider-config", help="Provider config JSON path.")] = None,
    max_chars: Annotated[int, typer.Option("--max-chars", help="Maximum extracted source chars.")] = 12000,
) -> None:
    from llmw.tui.app import WizardApp

    WizardApp(
        _paths(root),
        provider=provider,
        provider_config=provider_config,
        max_chars=max_chars,
    ).run()


@index_app.command("rebuild")
def index_rebuild(
    root: Annotated[Path, typer.Option("--root", "-r", help="Project root.")] = Path("."),
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON.")] = False,
) -> None:
    from llmw.wiki.index import rebuild_index

    try:
        rebuild_index(_paths(root))
    except Exception as exc:
        if json_output:
            _abort_json(exc, code="index-rebuild-failed")
        _abort(_error_message(exc))
    if json_output:
        _json_ok({"path": "wiki/index.md"})
        return
    typer.echo("Rebuilt wiki/index.md")


@index_app.command("check")
def index_check(
    root: Annotated[Path, typer.Option("--root", "-r", help="Project root.")] = Path("."),
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON.")] = False,
) -> None:
    from llmw.wiki.index import index_is_current

    try:
        current = index_is_current(_paths(root))
    except Exception as exc:
        if json_output:
            _abort_json(exc, code="index-check-failed")
        _abort(_error_message(exc))
    if json_output:
        payload = {"current": current}
        if current:
            _json_ok(payload)
        else:
            _abort_json(RuntimeError("wiki/index.md is stale or missing."), code="index-stale")
        return
    if current:
        typer.echo("wiki/index.md is current.")
        return
    typer.echo("wiki/index.md is stale or missing.")
    raise typer.Exit(1)


@health_app.command("check")
def health_check(
    root: Annotated[Path, typer.Option("--root", "-r", help="Project root.")] = Path("."),
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON.")] = False,
) -> None:
    from llmw.health.checks import HealthChecker

    try:
        issues = HealthChecker(_paths(root)).run()
    except Exception as exc:
        if json_output:
            _abort_json(exc, code="health-check-failed")
        _abort(_error_message(exc))
    if json_output:
        _json_ok({"issues": [issue.model_dump() for issue in issues]})
    elif not issues:
        typer.echo("No health issues found.")
    else:
        for issue in issues:
            location = f" {issue.path}" if issue.path else ""
            typer.echo(f"{issue.severity.upper()}\t{issue.code}{location}\t{issue.message}")
    if any(issue.severity == "error" for issue in issues):
        raise typer.Exit(1)


@health_app.command("audit")
def health_audit(
    root: Annotated[Path, typer.Option("--root", "-r", help="Project root.")] = Path("."),
    provider: Annotated[str | None, typer.Option("--provider", help="Provider name from provider config.")] = None,
    provider_config: Annotated[Path | None, typer.Option("--provider-config", help="Provider config JSON path.")] = None,
    save: Annotated[bool, typer.Option("--save", help="Save the report under wiki/outputs/ and log it.")] = False,
    max_pages: Annotated[int, typer.Option("--max-pages", min=1, help="Maximum wiki pages to include.")] = 40,
    max_page_chars: Annotated[int, typer.Option("--max-page-chars", min=500, help="Maximum chars to include from each page.")] = 2500,
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON.")] = False,
) -> None:
    paths = _paths(root)
    try:
        registry = load_provider_registry(paths, provider_config)
        provider_config_model = registry.get(provider)
        result = run_health_audit(
            paths,
            provider=provider_config_model,
            save=save,
            max_pages=max_pages,
            max_page_chars=max_page_chars,
        )
    except Exception as exc:
        if json_output:
            _abort_json(exc, code="health-audit-failed")
        _abort(_error_message(exc))

    payload = asdict(result)
    if json_output:
        _json_ok(payload)
        return
    typer.echo(result.report)
    typer.echo(f"\nModel: {result.model}")
    if result.saved_page:
        typer.echo(f"Saved: {result.saved_page}")


@log_app.command("add")
def log_add(
    kind: Annotated[str, typer.Argument(help="Entry kind, e.g. Query, Ingest, Health.")],
    title: Annotated[str, typer.Argument(help="Entry title.")],
    note: Annotated[str, typer.Option("--note", help="Optional log note.")] = "",
    root: Annotated[Path, typer.Option("--root", "-r", help="Project root.")] = Path("."),
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON.")] = False,
) -> None:
    from llmw.wiki.log import append_log

    try:
        entry = append_log(_paths(root), kind, title, note)
    except Exception as exc:
        if json_output:
            _abort_json(exc, code="log-add-failed")
        _abort(_error_message(exc))
    if json_output:
        _json_ok({"entry": entry})
        return
    typer.echo(entry)


@llm_app.command("check")
def llm_check(
    root: Annotated[Path, typer.Option("--root", "-r", help="Project root.")] = Path("."),
    provider: Annotated[str | None, typer.Option("--provider", help="Provider name from provider config.")] = None,
    provider_config: Annotated[Path | None, typer.Option("--provider-config", help="Provider config JSON path.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON.")] = False,
) -> None:
    from llmw.llm.config import load_provider_registry
    from llmw.llm.client import OpenAICompatibleClient

    paths = _paths(root)
    try:
        registry = load_provider_registry(paths, provider_config)
        config = registry.get(provider)
        result = OpenAICompatibleClient(config).chat(
            system_prompt="You are a connection test. Reply with exactly OK.",
            user_prompt="Reply with exactly OK.",
            temperature=0,
            top_p=1,
            max_tokens=8,
        )
    except Exception as exc:
        if json_output:
            _abort_json(exc, code="llm-check-failed")
        _abort(_error_message(exc))
    payload = {
        "provider": provider or registry.default_provider,
        "model": result.model,
        "connection_ok": result.content.strip().upper().startswith("OK"),
        "response": result.content.strip(),
        "usage": result.usage,
    }
    if json_output:
        _json_ok(payload)
        return
    typer.echo(f"Provider: {payload['provider']}")
    typer.echo(f"Model: {payload['model']}")
    typer.echo(f"Response: {payload['response']}")


def _write_bootstrap_files(paths: WikiPaths, *, overwrite: bool = False) -> None:
    from llmw.wiki.index import build_index_content

    files = {
        paths.index_path: build_index_content(paths),
        paths.log_path: "# Log\n\n",
        paths.state / ".env.example": "DASHSCOPE_API_KEY=your-dashscope-api-key\n",
        paths.root / "AGENTS.md": _agents_doc(),
        paths.system / "architecture.md": _architecture_doc(),
        paths.system / "providers" / "qwen-plus.json": _qwen_provider_config(),
        paths.system / "prompts" / "ingest.md": _ingest_prompt(),
        paths.system / "prompts" / "query.md": _query_prompt(),
        paths.system / "prompts" / "health.md": _health_prompt(),
        paths.system / "prompts" / "agent.md": _agent_prompt(),
        paths.templates / "wiki_page.md": _wiki_page_template(),
        paths.templates / "source_page.md": _source_page_template(),
    }
    for path, content in files.items():
        if path.exists() and not overwrite:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def _agents_doc() -> str:
    return """# LLM Wiki Agent Guide

You maintain `wiki/`; raw sources under `raw/` are read-only evidence.

Agent-native workflow:
1. Start with `llmw context --json` to understand project state.
2. Use `llmw maintain --json` for routine maintenance planning, or `llmw next --json` for lightweight task discovery.
3. Prefer `llmw search <query> --json` for low-latency lookup; inspect the `strategy` field to decide whether `--deep` is warranted.
4. For repeated high-recall retrieval, keep `llmw search-server --deep` running and send NDJSON requests instead of repeatedly spawning `llmw search --deep`.
5. Use `llmw search-daemon start --deep` when a background warm search service is easier than holding an NDJSON process.
6. Agent runtimes that support MCP can launch `llmw mcp --root .` and use the exposed `llmw_*` tools.
7. Run `llmw benchmark search --json` after search changes.
8. For write operations that can be planned, use `llmw plan "<goal>" --json --save --preview`, inspect the plan, then prefer `llmw apply <plan_file> --dry-run --json` before a real apply.
9. Never run arbitrary shell edits through this tool; use the documented `llmw` primitives.

Workflow:
1. Use `llmw source add <path>` to register new Markdown/Text/PDF sources.
2. Use `llmw ingest packet <source_id>` before editing wiki pages.
3. Create or update source, entity, concept, and analysis pages with Obsidian `[[links]]`.
4. Keep `source_id` references in frontmatter or citations for factual claims.
5. Run `llmw ingest record <source_id> --page <path>` after edits.
6. Use `llmw health check` before considering work complete.

Do not rewrite raw sources. Prefer small, connected pages over large unlinked summaries.
"""


def _architecture_doc() -> str:
    return """# Architecture

This project is a local, agent-driven Markdown wiki.

- `raw/`: immutable source material.
- `wiki/`: maintained knowledge pages owned by the LLM agent.
- `system/`: templates and operating rules.
- `.llmw/`: local tool state such as config, source registry, and qmd cache.

The CLI provides structure, search, validation, indexing, and logging so an agent
can maintain the wiki consistently. Commands such as `llmw ingest run`,
`llmw query`, and `llmw health audit` can optionally call the configured LLM
provider.
"""


def _wiki_page_template() -> str:
    return """---
title: Untitled
type: concept
status: draft
created:
updated:
sources: []
tags: []
---

# Untitled

## Summary

## Key Links
"""


def _source_page_template() -> str:
    return """---
title: Untitled Source
type: source
status: draft
created:
updated:
sources: []
tags: []
---

# Untitled Source

## Source Summary

## Important Claims

## Links
"""


def _qwen_provider_config() -> str:
    return """{
  "default_provider": "qwen_plus",
  "providers": {
    "qwen_plus": {
      "type": "openai_compatible",
      "vendor": "alibaba_cloud_model_studio",
      "model": "qwen-plus",
      "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
      "api_key_env": "DASHSCOPE_API_KEY",
      "timeout_seconds": 120,
      "max_retries": 2,
      "generation_defaults": {
        "temperature": 0.2,
        "top_p": 0.8,
        "max_tokens": 4096
      },
      "usage": {
        "ingest": {
          "system_prompt_file": "system/prompts/ingest.md",
          "temperature": 0.2,
          "max_tokens": 4096
        },
        "query": {
          "system_prompt_file": "system/prompts/query.md",
          "temperature": 0.1,
          "max_tokens": 4096
        },
        "health": {
          "system_prompt_file": "system/prompts/health.md",
          "temperature": 0.0,
          "max_tokens": 2048
        },
        "agent": {
          "system_prompt_file": "system/prompts/agent.md",
          "temperature": 0.0,
          "max_tokens": 512
        }
      }
    }
  }
}
"""


def _ingest_prompt() -> str:
    return """# Ingest Agent Prompt

You are maintaining an LLM Wiki. Raw sources are read-only evidence. Wiki pages
are the maintained knowledge layer.

For each ingest task:

1. Read the provided source packet and source file.
2. Create or update a source page under `wiki/sources/`.
3. Update relevant concept, entity, and analysis pages.
4. Use Obsidian wiki links for relationships.
5. Preserve source traceability with `source_id` in frontmatter or citations.
6. Keep pages concise, connected, and factual.

Do not invent unsupported claims. If the source conflicts with existing wiki
content, mark the conflict explicitly instead of silently overwriting it.
"""


def _query_prompt() -> str:
    return """# Query Agent Prompt

Answer questions using only the maintained wiki evidence provided in the user
prompt. Do not use unsupported outside facts.

If the evidence is insufficient, say so explicitly and explain what source or
wiki page would be needed.

Include source-aware references using page titles or source_id values when
making factual claims.
"""


def _health_prompt() -> str:
    return """# Health Agent Prompt

Review only the provided wiki context for semantic maintenance issues:

- contradictions between pages
- stale claims replaced by newer sources
- missing cross-links
- orphan pages that should be linked
- important mentioned concepts without pages
- pages with weak or missing source traceability
- follow-up source gaps that would improve the wiki

Return concrete edits or follow-up tasks. Prefer small, actionable fixes. Cite
page titles, paths, or source_id values for each finding.
"""


def _agent_prompt() -> str:
    return """# Agent Router Prompt

Classify a user's natural-language LLM Wiki request into one safe action.

Return JSON only. Do not include Markdown fences.

Allowed actions:

- search
- query
- query_save
- source_list
- source_register
- ingest
- health_check
- health_audit
- health_audit_save
- status

Schema:

{"action": "query", "text": "question or search text", "target": "", "save": false, "deep": false}

Do not invent shell commands. Do not request arbitrary file edits. If uncertain,
choose query.
"""
