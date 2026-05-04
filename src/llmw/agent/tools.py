from __future__ import annotations

import difflib
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from llmw.core.config import load_config
from llmw.core.fs import ensure_parent, relative_to_root, slugify, utc_now_iso
from llmw.core.paths import WikiPaths
from llmw.agent.context import build_context, find_unregistered_sources
from llmw.health.checks import HealthChecker
from llmw.llm.config import ProviderConfig
from llmw.sources.registry import add_source, get_source, load_registry, update_source
from llmw.wiki.index import index_is_current, rebuild_index
from llmw.wiki.log import append_log


PlanAction = Literal[
    "source_add",
    "ingest_record",
    "query",
    "query_save",
    "health_audit_save",
    "index_rebuild",
    "wiki_patch",
    "audit_issue_plan",
]

APPLY_ACTIONS = {
    "source_add",
    "ingest_record",
    "query_save",
    "health_audit_save",
    "index_rebuild",
    "wiki_patch",
    "audit_issue_plan",
}


class ToolStep(BaseModel):
    id: str
    action: str
    args: dict[str, Any] = Field(default_factory=dict)
    writes: list[str] = Field(default_factory=list)
    risk: str = "low"
    status: str = "pending"


class ToolPlan(BaseModel):
    plan_id: str
    goal: str
    created_at: str
    steps: list[ToolStep] = Field(default_factory=list)
    writes: list[str] = Field(default_factory=list)
    requires_confirmation: bool = False


def build_next_tasks(paths: WikiPaths) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for source in _unregistered_sources(paths):
        tasks.append(
            {
                "id": f"register:{source}",
                "kind": "source_register",
                "priority": "high",
                "title": f"Register raw source {source}",
                "command": f"llmw source add {source} --json",
            }
        )
    for record in load_registry(paths).sources.values():
        if record.status != "ingested":
            tasks.append(
                {
                    "id": f"ingest:{record.source_id}",
                    "kind": "source_ingest",
                    "priority": "high",
                    "title": f"Ingest registered source {record.source_id}",
                    "command": f"llmw ingest packet {record.source_id}",
                }
            )
    if not index_is_current(paths):
        tasks.append(
            {
                "id": "index:rebuild",
                "kind": "index",
                "priority": "medium",
                "title": "Rebuild stale wiki index",
                "command": "llmw index rebuild",
            }
        )
    for issue in HealthChecker(paths).run()[:20]:
        tasks.append(
            {
                "id": f"health:{issue.code}:{issue.path or 'project'}",
                "kind": "health_issue",
                "priority": "high" if issue.severity == "error" else "medium",
                "title": issue.message,
                "path": issue.path,
                "command": "llmw health check --json",
            }
        )
    if not tasks:
        tasks.append(
            {
                "id": "audit:semantic",
                "kind": "health_audit",
                "priority": "low",
                "title": "Run semantic health audit when deeper maintenance review is needed",
                "command": "llmw health audit --json",
            }
        )
    tasks.append(
        {
            "id": "benchmark:search",
            "kind": "benchmark",
            "priority": "low",
            "title": "Run search benchmark before release or search changes",
            "command": "llmw benchmark search --provider python --top-k 5 --json",
        }
    )
    return tasks


def create_plan(paths: WikiPaths, goal: str) -> ToolPlan:
    clean_goal = goal.strip()
    if not clean_goal:
        raise ValueError("Plan goal must not be empty")
    lower_goal = clean_goal.lower()
    steps: list[ToolStep] = []

    if any(token in lower_goal for token in ["register", "登记", "注册"]):
        targets = _unregistered_sources(paths)
        for index, target in enumerate(targets, start=1):
            steps.append(
                ToolStep(
                    id=f"step-{index}",
                    action="source_add",
                    args={"path": target},
                    writes=[".llmw/sources.json", "raw/processed/"],
                    risk="medium",
                )
            )
    elif any(token in lower_goal for token in ["index", "索引"]):
        steps.append(
            ToolStep(
                id="step-1",
                action="index_rebuild",
                writes=["wiki/index.md"],
                risk="low",
            )
        )
    elif any(token in lower_goal for token in ["audit", "审计", "semantic health", "语义健康"]):
        steps.append(
            ToolStep(
                id="step-1",
                action="health_audit_save",
                args={"max_pages": 40, "max_page_chars": 2500},
                writes=["wiki/outputs/", "wiki/log.md", "wiki/index.md"],
                risk="medium",
            )
        )
    elif any(token in lower_goal for token in ["save", "保存"]):
        question = _strip_plan_query(clean_goal)
        steps.append(
            ToolStep(
                id="step-1",
                action="query_save",
                args={"question": question, "limit": 5, "deep": False, "max_page_chars": 4000},
                writes=["wiki/outputs/", "wiki/log.md", "wiki/index.md"],
                risk="medium",
            )
        )
    else:
        steps.append(
            ToolStep(
                id="step-1",
                action="query",
                args={"question": clean_goal, "limit": 5, "deep": False},
                writes=[],
                risk="low",
            )
        )

    writes = _dedupe_write_paths(path for step in steps for path in step.writes)
    return ToolPlan(
        plan_id=_plan_id(clean_goal),
        goal=clean_goal,
        created_at=utc_now_iso(),
        steps=steps,
        writes=writes,
        requires_confirmation=bool(writes),
    )


def save_plan(paths: WikiPaths, plan: ToolPlan) -> str:
    rel_path = Path(".llmw") / "plans" / f"{plan.plan_id}.json"
    destination = paths.root / rel_path
    ensure_parent(destination)
    destination.write_text(plan.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return rel_path.as_posix()


def load_plan(path: Path) -> ToolPlan:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "plan" in data:
        data = data["plan"]
    return ToolPlan.model_validate(data)


def apply_plan(
    paths: WikiPaths,
    plan: ToolPlan,
    *,
    provider: ProviderConfig | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for step in plan.steps:
        if step.action not in APPLY_ACTIONS:
            raise ValueError(f"Unsupported apply action: {step.action}")
        output = _preview_step(paths, step) if dry_run else _apply_step(paths, step, provider=provider)
        status = "dry_run" if dry_run else "applied"
        if not dry_run:
            step.status = status
        results.append({"step_id": step.id, "action": step.action, "status": status, "output": output})
    return {"plan_id": plan.plan_id, "dry_run": dry_run, "applied": 0 if dry_run else len(results), "results": results}


def preview_plan(paths: WikiPaths, plan: ToolPlan) -> dict[str, Any]:
    return apply_plan(paths, plan, dry_run=True)


def _apply_step(paths: WikiPaths, step: ToolStep, *, provider: ProviderConfig | None) -> dict[str, Any]:
    if step.action == "source_add":
        config = load_config(paths)
        record = add_source(paths, paths.root / str(step.args["path"]), config.source_extensions)
        return {"source_id": record.source_id, "path": record.path}
    if step.action == "ingest_record":
        source_id = str(step.args["source_id"])
        pages = [str(page) for page in step.args.get("pages", [])]
        note = str(step.args.get("note", ""))
        record = get_source(paths, source_id)
        record.status = "ingested"
        record.pages = pages
        update_source(paths, record)
        append_log(paths, "Ingest", record.title, note or f"Processed `{source_id}`. Updated pages: {', '.join(pages) or 'none listed'}.")
        rebuild_index(paths)
        return {"source_id": source_id, "pages": pages}
    if step.action == "query_save":
        from llmw.llm.query import run_query
        from llmw.search.providers import build_search_service

        if provider is None:
            raise ValueError("Provider is required for query_save")
        config = load_config(paths)
        service = build_search_service(paths, config.qmd_collection, use_qmd=bool(step.args.get("deep", False)))
        result = run_query(
            paths,
            str(step.args["question"]),
            provider=provider,
            limit=int(step.args.get("limit", 5)),
            deep=bool(step.args.get("deep", False)),
            save=True,
            max_page_chars=int(step.args.get("max_page_chars", 4000)),
            search_service=service,
        )
        return {"saved_page": result.saved_page, "pages": [page.path for page in result.pages]}
    if step.action == "health_audit_save":
        from llmw.llm.health import run_health_audit

        if provider is None:
            raise ValueError("Provider is required for health_audit_save")
        result = run_health_audit(
            paths,
            provider=provider,
            save=True,
            max_pages=int(step.args.get("max_pages", 40)),
            max_page_chars=int(step.args.get("max_page_chars", 2500)),
        )
        return {"saved_page": result.saved_page, "pages": len(result.pages)}
    if step.action == "index_rebuild":
        rebuild_index(paths)
        return {"path": "wiki/index.md"}
    if step.action == "wiki_patch":
        patch = _build_wiki_patch(paths, step)
        patch.path.parent.mkdir(parents=True, exist_ok=True)
        patch.path.write_text(patch.after.rstrip() + "\n", encoding="utf-8")
        return {"path": patch.rel_path, "diff": patch.diff}
    if step.action == "audit_issue_plan":
        return {"review_required": True, "issue": step.args}
    raise ValueError(f"Unsupported apply action: {step.action}")


def _preview_step(paths: WikiPaths, step: ToolStep) -> dict[str, Any]:
    if step.action == "wiki_patch":
        patch = _build_wiki_patch(paths, step)
        return {"path": patch.rel_path, "diff": patch.diff}
    if step.action == "audit_issue_plan":
        return {"review_required": True, "issue": step.args}
    return {"writes": step.writes, "message": "No mutation performed in dry-run mode."}


class _WikiPatch(BaseModel):
    path: Path
    rel_path: str
    before: str
    after: str
    diff: str


def _build_wiki_patch(paths: WikiPaths, step: ToolStep) -> _WikiPatch:
    rel_path = str(step.args.get("path") or "").strip()
    if not rel_path:
        raise ValueError("wiki_patch requires args.path")
    target = _resolve_safe_patch_path(paths, rel_path)
    before = target.read_text(encoding="utf-8", errors="replace") if target.exists() else ""
    create = bool(step.args.get("create", False))
    old = step.args.get("old")
    new = step.args.get("new")
    if not isinstance(new, str):
        raise ValueError("wiki_patch requires string args.new")
    if create:
        if target.exists():
            raise ValueError(f"wiki_patch create target already exists: {rel_path}")
        after = new
    else:
        if not target.exists():
            raise ValueError(f"wiki_patch target does not exist: {rel_path}")
        if not isinstance(old, str) or old == "":
            raise ValueError("wiki_patch requires non-empty string args.old unless create=true")
        occurrences = before.count(old)
        if occurrences != 1:
            raise ValueError(f"wiki_patch old text must match exactly once in {rel_path}; matched {occurrences}")
        after = before.replace(old, new, 1)
    diff = "\n".join(
        difflib.unified_diff(
            before.splitlines(),
            after.splitlines(),
            fromfile=f"a/{rel_path}",
            tofile=f"b/{rel_path}",
            lineterm="",
        )
    )
    return _WikiPatch(path=target, rel_path=rel_path, before=before, after=after, diff=diff)


def _resolve_safe_patch_path(paths: WikiPaths, rel_path: str) -> Path:
    candidate = Path(rel_path)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"Unsafe wiki_patch path: {rel_path}")
    if not candidate.parts or candidate.parts[0] not in {"wiki", "system"}:
        raise ValueError("wiki_patch may only write under wiki/ or system/")
    target = (paths.root / candidate).resolve()
    root = paths.root.resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Unsafe wiki_patch path: {rel_path}") from exc
    return target


def _unregistered_sources(paths: WikiPaths) -> list[str]:
    return find_unregistered_sources(paths)


def _dedupe_write_paths(paths: Any) -> list[str]:
    deduped: list[str] = []
    for path in paths:
        if path not in deduped:
            deduped.append(path)
    return deduped


def _plan_id(goal: str) -> str:
    stamp = utc_now_iso().replace("-", "").replace(":", "").replace("Z", "")
    return f"plan-{stamp}-{slugify(goal, fallback='task')[:40]}"


def _strip_plan_query(goal: str) -> str:
    cleaned = goal.strip()
    for prefix in ["save", "保存", "保存回答", "保存查询"]:
        if cleaned.lower().startswith(prefix.lower()):
            return cleaned[len(prefix) :].strip(" :：") or cleaned
    return cleaned
