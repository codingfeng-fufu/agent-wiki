from __future__ import annotations

import statistics
import time
from typing import Any, Callable

from llmw.agent.context import build_context
from llmw.core.config import load_config
from llmw.core.fs import utc_now_iso
from llmw.core.paths import WikiPaths
from llmw.health.checks import HealthChecker
from llmw.search.providers import build_search_service


DEFAULT_PERF_QUERIES = [
    "guardrails",
    "how should agents use guardrails?",
    "MCP tools resources prompts",
]


def run_perf_benchmark(
    paths: WikiPaths,
    *,
    repeat: int = 3,
    limit: int = 3,
    include_deep: bool = False,
    queries: list[str] | None = None,
) -> dict[str, Any]:
    repeat = max(repeat, 1)
    queries = queries or DEFAULT_PERF_QUERIES
    config = load_config(paths)
    fast_service = build_search_service(paths, config.qmd_collection, use_qmd=False)
    checks: list[dict[str, Any]] = []
    checks.append(_measure("context", repeat, lambda: build_context(paths)))
    checks.append(_measure("health", repeat, lambda: HealthChecker(paths).run()))
    for query in queries:
        checks.append(
            _measure(
                f"search.fast:{query}",
                repeat,
                lambda query=query: fast_service.search(query, limit=limit, deep=False),
            )
        )
    if include_deep:
        deep_service = build_search_service(paths, config.qmd_collection, use_qmd=True)
        for query in queries:
            checks.append(
                _measure(
                    f"search.deep:{query}",
                    1,
                    lambda query=query: deep_service.search(query, limit=limit, deep=True),
                )
            )
    return {
        "checked_at": utc_now_iso(),
        "root": paths.root.as_posix(),
        "repeat": repeat,
        "limit": limit,
        "include_deep": include_deep,
        "checks": checks,
        "summary": {
            "max_p95_ms": max((check["p95_ms"] for check in checks), default=0),
            "max_mean_ms": max((check["mean_ms"] for check in checks), default=0),
        },
    }


def format_perf_report(payload: dict[str, Any]) -> str:
    lines = [
        "LLM Wiki Performance",
        f"Root: {payload['root']}",
        f"Repeat: {payload['repeat']}",
        f"Max p95: {payload['summary']['max_p95_ms']:.1f} ms",
        "",
    ]
    for check in payload["checks"]:
        lines.append(
            f"- {check['name']}: mean={check['mean_ms']:.1f} ms p95={check['p95_ms']:.1f} ms min={check['min_ms']:.1f} ms max={check['max_ms']:.1f} ms"
        )
    return "\n".join(lines)


def _measure(name: str, repeat: int, fn: Callable[[], Any]) -> dict[str, Any]:
    durations: list[float] = []
    for _ in range(repeat):
        started = time.perf_counter()
        fn()
        durations.append((time.perf_counter() - started) * 1000)
    return {
        "name": name,
        "runs": repeat,
        "mean_ms": statistics.fmean(durations),
        "p95_ms": _percentile(durations, 0.95),
        "min_ms": min(durations),
        "max_ms": max(durations),
    }


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * percentile)))
    return ordered[index]
