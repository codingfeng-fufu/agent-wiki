from __future__ import annotations

import json
import sqlite3
import tempfile
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Iterable

from llmw.core.paths import WikiPaths
from llmw.search.providers import QmdSearchProvider, RgSearchProvider, SearchService
from llmw.wiki.pages import load_pages


@dataclass(frozen=True)
class QueryCase:
    id: str
    query: str
    relevant: list[str]
    category: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class QueryScore:
    id: str
    query: str
    category: str
    relevant: list[str]
    retrieved: list[str]
    hits: int
    precision: float
    recall: float
    f1: float
    reciprocal_rank: float


CONCEPT_CASES: list[tuple[str, str, str]] = [
    ("wiki/concepts/Agent Runtime.md", "Agent Runtime", "execution environment for lifecycle routing state persistence and tool invocation"),
    ("wiki/concepts/AutoGen.md", "AutoGen", "Microsoft framework for message driven multi agent applications"),
    ("wiki/concepts/Message Driven Agents.md", "Message Driven Agents", "agents communicating through messages rather than shared memory"),
    ("wiki/concepts/Multi-Agent Orchestration.md", "Multi-Agent Orchestration", "coordinate behavior and data flow among multiple autonomous agents"),
    ("wiki/concepts/agent-checkpointing.md", "Agent Checkpointing", "persist agent state snapshots for recovery and auditing"),
    ("wiki/concepts/agent-evaluation.md", "Agent Evaluation", "evaluate whether agent behavior is safe useful and reproducible"),
    ("wiki/concepts/agent-guardrails.md", "Agent Guardrails", "validation boundaries for unsafe inputs malformed outputs and tool misuse"),
    ("wiki/concepts/agent-interoperability.md", "Agent Interoperability", "independent agents exchange tasks state and messages across boundaries"),
    ("wiki/concepts/agent-observability.md", "Agent Observability", "inspect debug and evaluate agent behavior beyond final answers"),
    ("wiki/concepts/agent-regression-testing.md", "Agent Regression Testing", "rerun representative tasks to detect behavior changes"),
    ("wiki/concepts/agent-security.md", "Agent Security", "security controls for agents that can call tools files or networks"),
    ("wiki/concepts/agent-state-graph.md", "Agent State Graph", "directed graph representation of agent states actions and transitions"),
    ("wiki/concepts/agent-tracing.md", "Agent Tracing", "structured trace records for model calls tool calls handoffs and guardrails"),
    ("wiki/concepts/agent2agent-protocol.md", "Agent2Agent Protocol", "A2A protocol for secure discoverable communication between autonomous agents"),
    ("wiki/concepts/coordinator-agent.md", "Coordinator Agent", "agent role that delegates subtasks aggregates results and enforces order"),
    ("wiki/concepts/durable-agent-execution.md", "Durable Agent Execution", "agent survives interruptions by persisting state and resuming from checkpoints"),
    ("wiki/concepts/fan-out-gather-pattern.md", "Fan Out Gather Pattern", "parallel subtasks distributed then collected and synthesized"),
    ("wiki/concepts/human-in-the-loop.md", "Human in the Loop", "workflow pauses for human input review or approval"),
    ("wiki/concepts/idempotent-tool-calls.md", "Idempotent Tool Calls", "safe retryable tool operations with same observable result"),
    ("wiki/concepts/input-guardrails.md", "Input Guardrails", "validate user input source content or workflow state before agent execution"),
    ("wiki/concepts/least-privilege.md", "Least Privilege", "grant an agent only the permissions needed for the current task"),
    ("wiki/concepts/mcp-prompts.md", "MCP Prompts", "reusable interaction templates and structured instructions in Model Context Protocol"),
    ("wiki/concepts/mcp-resources.md", "MCP Resources", "contextual data exposed without necessarily performing actions"),
    ("wiki/concepts/mcp-tools.md", "MCP Tools", "invocable actions exposed by Model Context Protocol"),
    ("wiki/concepts/mcp-vs-a2a.md", "MCP vs A2A", "compare Model Context Protocol with Agent2Agent interoperability"),
    ("wiki/concepts/model-context-protocol.md", "Model Context Protocol", "standard interface for tools resources and prompts"),
    ("wiki/concepts/multi-agent-systems.md", "Multi-Agent Systems", "architectures where multiple autonomous agents collaborate on tasks"),
    ("wiki/concepts/output-guardrails.md", "Output Guardrails", "validate generated results before returning storing or using downstream"),
    ("wiki/concepts/planner-executor-pattern.md", "Planner Executor Pattern", "planner creates actions and executor carries them out"),
    ("wiki/concepts/prompt-injection.md", "Prompt Injection", "untrusted source text tries to override agent instructions"),
    ("wiki/concepts/protocol-boundary.md", "Protocol Boundary", "interface layer enforcing authentication authorization schemas and trust assumptions"),
    ("wiki/concepts/replayable-agent-runs.md", "Replayable Agent Runs", "preserve run context to inspect or reproduce agent behavior later"),
    ("wiki/concepts/reviewer-agent.md", "Reviewer Agent", "agent that critiques validates correctness and triggers revision"),
    ("wiki/concepts/sensitive-data-exposure.md", "Sensitive Data Exposure", "secrets or private information leaking through prompts traces or logs"),
    ("wiki/concepts/tool-abuse.md", "Tool Abuse", "model controlled actions misused or triggered unsafely"),
    ("wiki/concepts/tool-call-logs.md", "Tool Call Logs", "records of tool invocations results and failures during an agent run"),
    ("wiki/concepts/tool-safety.md", "Tool Safety", "constraints around actions that an agent can invoke"),
]


SOURCE_CASES: list[tuple[str, str, str]] = [
    ("wiki/sources/01-openai-agents-guardrails-87ce73bd.md", "OpenAI Agents SDK Guardrails source", "source card for OpenAI guardrails documentation"),
    ("wiki/sources/02-openai-agents-tracing-ea05beb6.md", "OpenAI Agents SDK Tracing source", "source card for OpenAI tracing observability documentation"),
    ("wiki/sources/03-mcp-tools-resources-prompts-420d2910.md", "Model Context Protocol tools resources prompts source", "source card for MCP concepts documentation"),
    ("wiki/sources/04-langgraph-durable-execution-2b964c83.md", "LangGraph Durable Execution source", "source card for LangGraph persistence durable execution and human in the loop"),
    ("wiki/sources/05-google-adk-multi-agent-patterns-78ef6d88.md", "Google ADK Multi-Agent Systems source", "source card for Google ADK multi agent architecture patterns"),
    ("wiki/sources/06-autogen-agent-and-multi-agent-applications-8cb555fe.md", "AutoGen Agent and Multi-Agent Applications source", "source card for Microsoft AutoGen multi agent application design"),
    ("wiki/sources/07-a2a-agent-interoperability-fc58e8a2.md", "Agent2Agent Protocol source", "source card for A2A interoperability protocol boundaries"),
    ("wiki/sources/08-owasp-llm-agent-security-9253bc51.md", "OWASP LLM Application Security source", "source card for OWASP prompt injection data exposure and tool abuse"),
]


ANALYSIS_CASES: list[tuple[str, str, str]] = [
    ("wiki/analyses/agent-development-knowledge-map.md", "Agent Development Knowledge Map", "map connecting guardrails tracing MCP durable execution multi agent and security sources"),
    ("wiki/analyses/agent-development-knowledge-map.md", "initial agent development source map", "cross cutting threads for safety reliability coordination and protocol design"),
]


CROSS_CUTTING_CASES: list[tuple[str, list[str], str]] = [
    ("how should llmw validate generated wiki pages before writing files", ["wiki/concepts/agent-guardrails.md", "wiki/concepts/output-guardrails.md", "wiki/concepts/tool-safety.md"], "cross-cutting"),
    ("how to debug and replay failed agent runs", ["wiki/concepts/agent-tracing.md", "wiki/concepts/replayable-agent-runs.md", "wiki/concepts/agent-observability.md"], "cross-cutting"),
    ("what helps long running agents recover after interruption", ["wiki/concepts/durable-agent-execution.md", "wiki/concepts/agent-checkpointing.md", "wiki/concepts/agent-state-graph.md"], "cross-cutting"),
    ("which pattern sends work to several agents in parallel then combines answers", ["wiki/concepts/fan-out-gather-pattern.md", "wiki/concepts/coordinator-agent.md", "wiki/concepts/multi-agent-systems.md"], "cross-cutting"),
    ("difference between MCP tools and agent to agent protocol", ["wiki/concepts/mcp-vs-a2a.md", "wiki/concepts/model-context-protocol.md", "wiki/concepts/agent2agent-protocol.md"], "cross-cutting"),
    ("how to reduce prompt injection risk in tool using agents", ["wiki/concepts/prompt-injection.md", "wiki/concepts/agent-security.md", "wiki/concepts/tool-safety.md", "wiki/concepts/least-privilege.md"], "cross-cutting"),
    ("what data should not be stored in traces or logs", ["wiki/concepts/sensitive-data-exposure.md", "wiki/concepts/agent-tracing.md", "wiki/concepts/tool-call-logs.md"], "cross-cutting"),
    ("how should agents coordinate reviewer planner executor and human approval roles", ["wiki/concepts/Multi-Agent Orchestration.md", "wiki/concepts/planner-executor-pattern.md", "wiki/concepts/reviewer-agent.md", "wiki/concepts/human-in-the-loop.md"], "cross-cutting"),
]


def load_cases() -> list[QueryCase]:
    cases: list[QueryCase] = []
    for index, (path, title_query, paraphrase_query) in enumerate(CONCEPT_CASES, start=1):
        cases.append(QueryCase(f"concept-{index:03d}-title", title_query, [path], "concept-title"))
        cases.append(QueryCase(f"concept-{index:03d}-paraphrase", paraphrase_query, [path], "concept-paraphrase"))
    for index, (path, title_query, paraphrase_query) in enumerate(SOURCE_CASES, start=1):
        cases.append(QueryCase(f"source-{index:03d}-title", title_query, [path], "source-title"))
        cases.append(QueryCase(f"source-{index:03d}-paraphrase", paraphrase_query, [path], "source-paraphrase"))
    for index, (path, title_query, paraphrase_query) in enumerate(ANALYSIS_CASES, start=1):
        cases.append(QueryCase(f"analysis-{index:03d}-title", title_query, [path], "analysis-title"))
        cases.append(QueryCase(f"analysis-{index:03d}-paraphrase", paraphrase_query, [path], "analysis-paraphrase"))
    for index, (query, relevant, category) in enumerate(CROSS_CUTTING_CASES, start=1):
        cases.append(QueryCase(f"cross-{index:03d}", query, relevant, category))
    if len(cases) != 102:
        raise AssertionError(f"expected 102 benchmark cases, got {len(cases)}")
    return cases


def missing_references(root: Path) -> list[str]:
    missing: list[str] = []
    for case in load_cases():
        for path in case.relevant:
            if not (root / path).exists():
                missing.append(f"{case.id}: {path}")
    return missing


def evaluate(cases: list[QueryCase], searcher: Callable[[str, int], list[str]], *, top_k: int) -> tuple[dict, list[QueryScore]]:
    scores: list[QueryScore] = []
    for case in cases:
        relevant = list(dict.fromkeys(case.relevant))
        retrieved = list(dict.fromkeys(searcher(case.query, top_k)))[:top_k]
        relevant_set = set(relevant)
        hits = sum(1 for path in retrieved if path in relevant_set)
        precision = hits / top_k if top_k else 0.0
        recall = hits / len(relevant) if relevant else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0
        scores.append(
            QueryScore(
                id=case.id,
                query=case.query,
                category=case.category,
                relevant=relevant,
                retrieved=retrieved,
                hits=hits,
                precision=precision,
                recall=recall,
                f1=f1,
                reciprocal_rank=_reciprocal_rank(retrieved, relevant_set),
            )
        )
    return summarize(scores, top_k=top_k), scores


def summarize(scores: list[QueryScore], *, top_k: int) -> dict:
    by_category: dict[str, list[QueryScore]] = defaultdict(list)
    for score in scores:
        by_category[score.category].append(score)
    summary = {
        "queries": len(scores),
        "top_k": top_k,
        "precision_at_k": _avg(score.precision for score in scores),
        "precision_at_k_ceiling": _avg(min(top_k, len(score.relevant)) / top_k for score in scores),
        "recall_at_k": _avg(score.recall for score in scores),
        "f1_at_k": _avg(score.f1 for score in scores),
        "hit_rate_at_k": _avg(1.0 if score.hits else 0.0 for score in scores),
        "mrr_at_k": _avg(score.reciprocal_rank for score in scores),
        "by_category": {},
    }
    for category, category_scores in sorted(by_category.items()):
        summary["by_category"][category] = {
            "queries": len(category_scores),
            "precision_at_k": _avg(score.precision for score in category_scores),
            "recall_at_k": _avg(score.recall for score in category_scores),
            "f1_at_k": _avg(score.f1 for score in category_scores),
            "hit_rate_at_k": _avg(1.0 if score.hits else 0.0 for score in category_scores),
            "mrr_at_k": _avg(score.reciprocal_rank for score in category_scores),
        }
    return summary


def run_search_benchmark(
    paths: WikiPaths,
    *,
    provider: str = "python",
    top_k: int = 5,
    include_special: bool = False,
) -> dict:
    missing = missing_references(paths.root)
    if missing:
        raise FileNotFoundError("Benchmark references missing wiki pages:\n" + "\n".join(f"- {item}" for item in missing))
    searcher = build_searcher(provider, paths, content_only=not include_special)
    summary, scores = evaluate(load_cases(), searcher, top_k=top_k)
    return {
        "provider": provider,
        "content_only": not include_special,
        "summary": summary,
        "worst_queries": [asdict(score) for score in sorted(scores, key=lambda item: (item.f1, item.hits, item.id))[:10]],
        "queries": [asdict(score) for score in scores],
    }


def build_searcher(provider: str, paths: WikiPaths, *, content_only: bool) -> Callable[[str, int], list[str]]:
    if provider == "python":
        search_provider = RgSearchProvider(paths, executable="", include_special=not content_only)
        return lambda query, top_k: [result.path for result in search_provider.search(query, limit=top_k)]
    if provider == "rg":
        search_provider = RgSearchProvider(paths)
        return lambda query, top_k: [result.path for result in search_provider.search(query, limit=top_k)]
    if provider == "llmw":
        service = SearchService(QmdSearchProvider(paths, "llmwiki"), RgSearchProvider(paths))
        return lambda query, top_k: [result.path for result in service.search(query, limit=top_k, deep=True)[0]]
    if provider == "qmd":
        return build_qmd_searcher(paths, content_only=content_only)
    raise ValueError(f"unknown provider: {provider}")


def build_qmd_searcher(paths: WikiPaths, *, content_only: bool) -> Callable[[str, int], list[str]]:
    try:
        import qmd
    except ImportError as exc:
        raise RuntimeError("qmd is not installed; run `uv sync --extra search`") from exc
    temp_dir = tempfile.TemporaryDirectory(prefix="llmw-qmd-benchmark-")
    db_path = Path(temp_dir.name) / "qmd.sqlite"
    client = qmd.connect(db_path, config_overrides={"embedding": {"batch_size": 16}})
    collection = client.collection("llmwiki-benchmark")
    collection.add_documents(
        [
            {"document_id": doc["path"], "markdown": doc["text"], "metadata": {"path": doc["path"]}}
            for doc in _load_documents(paths, content_only=content_only)
        ]
    )

    def search(query: str, top_k: int) -> list[str]:
        seen: set[str] = set()
        ranked: list[str] = []
        try:
            results = collection.hybrid_search(query, top_k=max(top_k * 3, top_k), rerank=False)
        except sqlite3.OperationalError:
            results = collection.hybrid_search(_qmd_phrase_query(query), top_k=max(top_k * 3, top_k), rerank=False)
        for result in results:
            path = result.chunk_ref.document_id
            if path in seen:
                continue
            seen.add(path)
            ranked.append(path)
            if len(ranked) >= top_k:
                break
        return ranked

    search._benchmark_temp_dir = temp_dir  # type: ignore[attr-defined]
    search._benchmark_client = client  # type: ignore[attr-defined]
    return search


def format_benchmark_summary(payload: dict) -> str:
    summary = payload["summary"]
    top_k = summary["top_k"]
    lines = [
        f"Provider: {payload['provider']}",
        f"Queries: {summary['queries']}",
        f"Top-k: {top_k}",
        f"Content only: {payload['content_only']}",
        f"Precision@{top_k}: {summary['precision_at_k']:.4f}",
        f"Precision ceiling@{top_k}: {summary['precision_at_k_ceiling']:.4f}",
        f"Recall@{top_k}: {summary['recall_at_k']:.4f}",
        f"F1@{top_k}: {summary['f1_at_k']:.4f}",
        f"HitRate@{top_k}: {summary['hit_rate_at_k']:.4f}",
        f"MRR@{top_k}: {summary['mrr_at_k']:.4f}",
        "By category:",
    ]
    for category, values in summary["by_category"].items():
        lines.append(f"- {category}: n={values['queries']} F1@{top_k}={values['f1_at_k']:.4f} Recall@{top_k}={values['recall_at_k']:.4f}")
    return "\n".join(lines)


def assert_benchmark_gates(
    summary: dict,
    *,
    fail_under_f1: float | None = None,
    fail_under_recall: float | None = None,
    fail_under_hit_rate: float | None = None,
) -> None:
    failures: list[str] = []
    if fail_under_f1 is not None and summary["f1_at_k"] < fail_under_f1:
        failures.append(f"F1@{summary['top_k']} {summary['f1_at_k']:.4f} < {fail_under_f1:.4f}")
    if fail_under_recall is not None and summary["recall_at_k"] < fail_under_recall:
        failures.append(f"Recall@{summary['top_k']} {summary['recall_at_k']:.4f} < {fail_under_recall:.4f}")
    if fail_under_hit_rate is not None and summary["hit_rate_at_k"] < fail_under_hit_rate:
        failures.append(f"HitRate@{summary['top_k']} {summary['hit_rate_at_k']:.4f} < {fail_under_hit_rate:.4f}")
    if failures:
        raise AssertionError("; ".join(failures))


def payload_to_json(payload: dict) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False)


def _load_documents(paths: WikiPaths, *, content_only: bool) -> list[dict[str, str]]:
    pages = load_pages(paths, include_special=not content_only)
    documents: list[dict[str, str]] = []
    for page in pages:
        rel_path = page.path.resolve().relative_to(paths.root.resolve()).as_posix()
        documents.append({"path": rel_path, "title": page.title, "text": page.path.read_text(encoding="utf-8", errors="replace")})
    return documents


def _reciprocal_rank(retrieved: list[str], relevant: set[str]) -> float:
    for index, path in enumerate(retrieved, start=1):
        if path in relevant:
            return 1 / index
    return 0.0


def _avg(values: Iterable[float]) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def _qmd_phrase_query(query: str) -> str:
    return f'"{query.replace(chr(34), chr(34) + chr(34))}"'
