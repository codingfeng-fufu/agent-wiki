from __future__ import annotations

from typing import Any, Callable

from llmw.agent.context import build_context
from llmw.agent.tools import ToolPlan, ToolStep, build_next_tasks, save_plan
from llmw.core.fs import slugify, utc_now_iso
from llmw.core.paths import WikiPaths
from llmw.llm.config import ProviderConfig
from llmw.llm.health import HealthAuditResult, run_health_audit


HealthAuditRunner = Callable[..., HealthAuditResult]


def run_maintain(
    paths: WikiPaths,
    *,
    provider: ProviderConfig | None = None,
    audit: bool = True,
    save_plan_file: bool = True,
    audit_warning: str | None = None,
    health_audit_runner: HealthAuditRunner = run_health_audit,
) -> dict[str, Any]:
    context = build_context(paths)
    tasks = build_next_tasks(paths)
    warnings: list[str] = []
    audit_summary: dict[str, Any] | None = None
    audit_issues: list[dict[str, Any]] = []

    if audit:
        if audit_warning:
            warnings.append(f"Semantic audit skipped: {audit_warning}")
        elif provider is None:
            warnings.append("Semantic audit skipped: provider is not configured.")
        else:
            try:
                audit_result = health_audit_runner(paths, provider=provider, save=False)
                audit_summary = {
                    "model": audit_result.model,
                    "pages": len(audit_result.pages),
                    "report_excerpt": _excerpt(audit_result.report),
                    "issues": audit_result.issues,
                    "usage": audit_result.usage,
                }
                audit_issues = audit_result.issues
            except Exception as exc:
                warnings.append(f"Semantic audit failed: {exc}")

    plan = build_maintenance_plan(paths, tasks, audit_issues=audit_issues)
    saved_plan = save_plan(paths, plan) if save_plan_file else None
    recommended_commands = [
        "llmw context --json",
        "llmw next --json",
        "llmw health check --json",
    ]
    if audit:
        recommended_commands.append("llmw health audit --json")
    if saved_plan:
        recommended_commands.append(f"llmw apply {saved_plan} --dry-run --json")
        recommended_commands.append(f"llmw apply {saved_plan} --json")

    return {
        "context": context,
        "tasks": tasks,
        "health": context["health"],
        "audit_summary": audit_summary,
        "warnings": warnings,
        "plan": plan.model_dump(),
        "saved_plan": saved_plan,
        "recommended_commands": recommended_commands,
    }


def build_maintenance_plan(
    paths: WikiPaths,
    tasks: list[dict[str, Any]],
    *,
    audit_issues: list[dict[str, Any]] | None = None,
) -> ToolPlan:
    steps: list[ToolStep] = []
    step_index = 1
    for task in tasks:
        if task.get("kind") == "source_register":
            source_path = str(task["id"]).removeprefix("register:")
            steps.append(
                ToolStep(
                    id=f"step-{step_index}",
                    action="source_add",
                    args={"path": source_path},
                    writes=[".llmw/sources.json", "raw/processed/"],
                    risk="medium",
                )
            )
            step_index += 1
        elif task.get("id") == "index:rebuild":
            steps.append(
                ToolStep(
                    id=f"step-{step_index}",
                    action="index_rebuild",
                    writes=["wiki/index.md"],
                    risk="low",
                )
            )
            step_index += 1
    for issue in (audit_issues or [])[:10]:
        steps.append(
            ToolStep(
                id=f"step-{step_index}",
                action="audit_issue_plan",
                args=issue,
                writes=[],
                risk="review",
            )
        )
        step_index += 1

    writes = _dedupe(path for step in steps for path in step.writes)
    return ToolPlan(
        plan_id=_maintenance_plan_id(paths),
        goal="maintain wiki",
        created_at=utc_now_iso(),
        steps=steps,
        writes=writes,
        requires_confirmation=bool(writes),
    )


def _maintenance_plan_id(paths: WikiPaths) -> str:
    stamp = utc_now_iso().replace("-", "").replace(":", "").replace("Z", "")
    return f"plan-{stamp}-{slugify(paths.root.name, fallback='wiki')}-maintain"


def _dedupe(values) -> list[str]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def _excerpt(text: str, *, limit: int = 800) -> str:
    clean = text.strip()
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1].rstrip() + "…"
