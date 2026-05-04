from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from llmw.core.config import ensure_project_dirs, load_config
from llmw.core.fs import relative_to_root, utc_now_iso
from llmw.core.models import SearchResult, SourceRecord
from llmw.core.paths import WikiPaths
from llmw.health.checks import HealthChecker
from llmw.llm.client import OpenAICompatibleClient
from llmw.llm.config import ProviderConfig, load_provider_registry, load_system_prompt
from llmw.llm.health import HealthAuditResult, run_health_audit
from llmw.llm.ingest import IngestRunResult, run_ingest
from llmw.llm.query import QueryRunResult, run_query
from llmw.search.providers import build_search_service
from llmw.sources.registry import add_source, load_registry
from llmw.wiki.index import index_is_current
from llmw.wiki.pages import load_pages


ACTION_TYPES = {
    "exit",
    "help",
    "status",
    "source_list",
    "source_register",
    "search",
    "query",
    "query_save",
    "ingest",
    "health_check",
    "health_audit",
    "health_audit_save",
}


@dataclass(frozen=True)
class AgentAction:
    action: str
    text: str = ""
    target: str = ""
    save: bool = False
    deep: bool = False


InputFunc = Callable[[str], str]
OutputFunc = Callable[[str], None]
ClientFactory = Callable[[ProviderConfig], OpenAICompatibleClient]
QueryRunner = Callable[..., QueryRunResult]
IngestRunner = Callable[..., IngestRunResult]
HealthAuditRunner = Callable[..., HealthAuditResult]


class AgentSession:
    def __init__(
        self,
        paths: WikiPaths,
        *,
        provider: str | None = None,
        provider_config: Path | None = None,
        deep: bool = False,
        session_log: bool = True,
        input_func: InputFunc = input,
        output_func: OutputFunc = print,
        client_factory: ClientFactory = OpenAICompatibleClient,
        query_runner: QueryRunner = run_query,
        ingest_runner: IngestRunner = run_ingest,
        health_audit_runner: HealthAuditRunner = run_health_audit,
    ):
        self.paths = paths
        self.provider = provider
        self.provider_config = provider_config
        self.deep = deep
        self.session_log = session_log
        self.input_func = input_func
        self.output_func = output_func
        self.client_factory = client_factory
        self.query_runner = query_runner
        self.ingest_runner = ingest_runner
        self.health_audit_runner = health_audit_runner
        self.session_id = utc_now_iso().replace(":", "").replace("-", "")

    def run(self) -> None:
        ensure_project_dirs(self.paths)
        self.output_func("LLM Wiki agent ready. Type /help for commands, /exit to quit.")
        while True:
            try:
                user_input = self.input_func("llmw> ")
            except EOFError:
                self.output_func("")
                break
            clean_input = user_input.strip()
            if not clean_input:
                continue
            action = route_user_input(
                self.paths,
                clean_input,
                provider=self._maybe_provider(),
                client_factory=self.client_factory,
                default_deep=self.deep,
            )
            if action.action == "exit":
                self._log_turn(clean_input, action, "exit")
                self.output_func("Bye.")
                break
            try:
                summary = self.execute(action)
            except Exception as exc:
                summary = f"error: {exc}"
                self.output_func(f"Error: {exc}")
            self._log_turn(clean_input, action, summary)

    def execute(self, action: AgentAction) -> str:
        if action.action == "help":
            return self._show_help()
        if action.action == "status":
            return self._show_status()
        if action.action == "source_list":
            return self._show_sources()
        if action.action == "source_register":
            return self._register_sources(action.target)
        if action.action == "search":
            return self._search(action.text, deep=action.deep)
        if action.action in {"query", "query_save"}:
            return self._query(action.text, save=action.action == "query_save" or action.save, deep=action.deep)
        if action.action == "ingest":
            return self._ingest(action.target)
        if action.action == "health_check":
            return self._health_check()
        if action.action in {"health_audit", "health_audit_save"}:
            return self._health_audit(save=action.action == "health_audit_save" or action.save)
        self.output_func(f"Unknown action: {action.action}")
        return f"unknown action {action.action}"

    def _show_help(self) -> str:
        text = """Commands:
  /status                    Show wiki, source, and health summary.
  /sources                   List registered and pending sources.
  /search <query>            Search maintained wiki pages.
  /query <question>          Answer from wiki evidence.
  /save <question>           Answer and save under wiki/outputs/.
  /register [all|path]       Register raw/inbox source(s). Requires yes.
  /ingest [all|source_id]    Run LLM ingest. Requires yes.
  /health                    Run offline structural health check.
  /audit                     Run LLM semantic audit.
  /audit --save              Run audit and save output. Requires yes.
  /exit                      Quit.

Natural language input is also supported. Unrecognized input is treated as a query."""
        self.output_func(text)
        return "showed help"

    def _show_status(self) -> str:
        registry = load_registry(self.paths)
        pages = load_pages(self.paths)
        issues = HealthChecker(self.paths).run()
        errors = sum(1 for issue in issues if issue.severity == "error")
        warnings = sum(1 for issue in issues if issue.severity == "warning")
        infos = sum(1 for issue in issues if issue.severity == "info")
        pending = [source for source in registry.sources.values() if source.status != "ingested"]
        lines = [
            f"Root: {self.paths.root}",
            f"Wiki pages: {len(pages)}",
            f"Sources: {len(registry.sources)} ({len(pending)} pending ingest)",
            f"Index: {'current' if index_is_current(self.paths) else 'stale'}",
            f"Health: {errors} error(s), {warnings} warning(s), {infos} info issue(s)",
        ]
        self.output_func("\n".join(lines))
        return "showed status"

    def _show_sources(self) -> str:
        registry = load_registry(self.paths)
        sources = sorted(registry.sources.values(), key=lambda source: (source.status, source.title, source.source_id))
        if not sources:
            self.output_func("No registered sources.")
            return "listed 0 sources"
        for source in sources:
            self.output_func(f"{source.source_id}\t{source.status}\t{source.path}")
        return f"listed {len(sources)} sources"

    def _register_sources(self, target: str) -> str:
        candidates = self._registration_targets(target)
        if not candidates:
            self.output_func("No raw source files to register.")
            return "no sources registered"
        self.output_func("Plan: register source file(s):")
        for path in candidates:
            self.output_func(f"- {relative_to_root(path, self.paths.root)}")
        if not self._confirm("Register these sources?"):
            self.output_func("Skipped registration.")
            return "registration skipped"
        config = load_config(self.paths)
        records = [add_source(self.paths, path, config.source_extensions) for path in candidates]
        for record in records:
            self.output_func(f"Registered {record.source_id} -> {record.path}")
        return f"registered {len(records)} source(s)"

    def _search(self, query: str, *, deep: bool) -> str:
        if not query.strip():
            self.output_func("Search query is empty.")
            return "empty search"
        config = load_config(self.paths)
        service = build_search_service(self.paths, config.qmd_collection, use_qmd=deep or self.deep)
        results, warning = service.search(query, limit=5, deep=deep or self.deep)
        if warning:
            self.output_func(f"Warning: {warning}")
        if not results:
            self.output_func("No results.")
            return "search returned 0 results"
        for result in results:
            score = f" score={result.score}" if result.score is not None else ""
            self.output_func(f"- {result.title or result.path} ({result.path}){score}")
            if result.snippet:
                self.output_func(f"  {result.snippet[:240]}")
        return f"search returned {len(results)} result(s)"

    def _query(self, question: str, *, save: bool, deep: bool) -> str:
        if not question.strip():
            self.output_func("Question is empty.")
            return "empty query"
        if save and not self._confirm("Save this query answer under wiki/outputs/?"):
            self.output_func("Skipped query save.")
            return "query save skipped"
        provider = self._provider()
        config = load_config(self.paths)
        service = build_search_service(self.paths, config.qmd_collection, use_qmd=deep or self.deep)
        result = self.query_runner(
            self.paths,
            question,
            provider=provider,
            limit=5,
            deep=deep or self.deep,
            save=save,
            search_service=service,
        )
        if result.warning:
            self.output_func(f"Warning: {result.warning}")
        self.output_func(result.answer)
        self.output_func("\nEvidence pages:")
        for page in result.pages:
            self.output_func(f"- {page.title} ({page.path})")
        if result.saved_page:
            self.output_func(f"Saved: {result.saved_page}")
        return f"query answered using {len(result.pages)} page(s)"

    def _ingest(self, target: str) -> str:
        sources = self._ingest_targets(target)
        if not sources:
            self.output_func("No source found for ingest.")
            return "no ingest targets"
        self.output_func("Plan: run LLM ingest for source(s):")
        for source in sources:
            self.output_func(f"- {source.source_id} ({source.title})")
        if not self._confirm("Run ingest and write wiki pages?"):
            self.output_func("Skipped ingest.")
            return "ingest skipped"
        provider = self._provider()
        written = 0
        for source in sources:
            result = self.ingest_runner(self.paths, source.source_id, provider=provider, dry_run=False)
            self.output_func(f"Ingested {source.source_id}: {len(result.pages)} page(s)")
            written += len(result.pages)
        return f"ingested {len(sources)} source(s), wrote {written} page(s)"

    def _health_check(self) -> str:
        issues = HealthChecker(self.paths).run()
        if not issues:
            self.output_func("No health issues found.")
            return "health check passed"
        for issue in issues[:30]:
            location = f" {issue.path}" if issue.path else ""
            self.output_func(f"{issue.severity.upper()}\t{issue.code}{location}\t{issue.message}")
        if len(issues) > 30:
            self.output_func(f"... {len(issues) - 30} more issue(s)")
        return f"health check found {len(issues)} issue(s)"

    def _health_audit(self, *, save: bool) -> str:
        if save and not self._confirm("Save this semantic audit under wiki/outputs/?"):
            self.output_func("Skipped audit save.")
            return "audit save skipped"
        result = self.health_audit_runner(
            self.paths,
            provider=self._provider(),
            save=save,
            max_pages=40,
            max_page_chars=2500,
        )
        self.output_func(result.report)
        if result.saved_page:
            self.output_func(f"Saved: {result.saved_page}")
        return f"health audit reviewed {len(result.pages)} page(s)"

    def _confirm(self, message: str) -> bool:
        answer = self.input_func(f"{message} Type yes to continue: ").strip().lower()
        return answer == "yes"

    def _provider(self) -> ProviderConfig:
        registry = load_provider_registry(self.paths, self.provider_config)
        return registry.get(self.provider)

    def _maybe_provider(self) -> ProviderConfig | None:
        try:
            return self._provider()
        except Exception:
            return None

    def _registration_targets(self, target: str) -> list[Path]:
        clean_target = target.strip()
        if clean_target and clean_target.lower() != "all":
            return [self.paths.root / clean_target]
        config = load_config(self.paths)
        allowed = {extension.lower() for extension in config.source_extensions}
        registered = {
            path
            for record in load_registry(self.paths).sources.values()
            for path in [record.path, record.original_path]
            if path
        }
        candidates: list[Path] = []
        for path in sorted(self.paths.raw_inbox.rglob("*")) if self.paths.raw_inbox.exists() else []:
            if not path.is_file() or path.name == ".gitkeep":
                continue
            rel = relative_to_root(path, self.paths.root)
            if path.suffix.lower() in allowed and rel not in registered:
                candidates.append(path)
        return candidates

    def _ingest_targets(self, target: str) -> list[SourceRecord]:
        registry = load_registry(self.paths)
        sources = sorted(registry.sources.values(), key=lambda source: (source.status, source.title, source.source_id))
        clean_target = target.strip()
        if clean_target.lower() == "all":
            return [source for source in sources if source.status != "ingested"]
        if clean_target:
            return [source for source in sources if source.source_id == clean_target]
        pending = [source for source in sources if source.status != "ingested"]
        return pending[:1]

    def _log_turn(self, user_input: str, action: AgentAction, summary: str) -> None:
        if not self.session_log:
            return
        log_dir = self.paths.state / "sessions"
        log_dir.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": utc_now_iso(),
            "input": user_input[:500],
            "action": action.action,
            "target": action.target,
            "text": action.text[:200],
            "summary": summary[:500],
        }
        log_path = log_dir / f"{self.session_id}.jsonl"
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def route_user_input(
    paths: WikiPaths,
    text: str,
    *,
    provider: ProviderConfig | None = None,
    client_factory: ClientFactory = OpenAICompatibleClient,
    default_deep: bool = False,
) -> AgentAction:
    stripped = text.strip()
    if not stripped:
        return AgentAction("help")
    if stripped.startswith("/"):
        return parse_slash_command(stripped, default_deep=default_deep)

    local = route_with_rules(stripped, default_deep=default_deep)
    if local is not None:
        return local
    planned = route_with_llm(paths, stripped, provider=provider, client_factory=client_factory)
    return planned or AgentAction("query", text=stripped, deep=default_deep)


def parse_slash_command(text: str, *, default_deep: bool = False) -> AgentAction:
    body = text[1:].strip()
    if not body:
        return AgentAction("help")
    command, _, rest = body.partition(" ")
    command = command.lower()
    rest = rest.strip()
    deep = default_deep or "--deep" in rest
    rest = rest.replace("--deep", "").strip()
    if command in {"exit", "quit", "q"}:
        return AgentAction("exit")
    if command in {"help", "h"}:
        return AgentAction("help")
    if command in {"status", "stat"}:
        return AgentAction("status")
    if command in {"sources", "source"}:
        return AgentAction("source_list")
    if command in {"register", "add"}:
        return AgentAction("source_register", target=rest or "all")
    if command == "search":
        return AgentAction("search", text=rest, deep=deep)
    if command in {"query", "ask"}:
        return AgentAction("query", text=rest, deep=deep)
    if command in {"save", "query-save"}:
        return AgentAction("query_save", text=rest, save=True, deep=deep)
    if command == "ingest":
        return AgentAction("ingest", target=rest)
    if command in {"health", "check"}:
        return AgentAction("health_check")
    if command == "audit":
        save = "--save" in body
        return AgentAction("health_audit_save" if save else "health_audit", save=save)
    return AgentAction("query", text=body, deep=deep)


def route_with_rules(text: str, *, default_deep: bool = False) -> AgentAction | None:
    lowered = text.lower()
    deep = default_deep or any(token in lowered for token in ["--deep", "qmd", "rerank", "深度"])
    clean = text.replace("--deep", "").strip()

    if lowered in {"exit", "quit", "退出", "再见"}:
        return AgentAction("exit")
    if any(token in lowered for token in ["status", "状态", "概况"]):
        return AgentAction("status")
    if any(token in lowered for token in ["source list", "sources", "源列表", "列出源"]):
        return AgentAction("source_list")
    if any(token in lowered for token in ["register", "source add", "登记", "注册"]):
        target = _last_path_like_token(clean) or ("all" if any(token in lowered for token in ["all", "全部", "所有"]) else "")
        return AgentAction("source_register", target=target or "all")
    if any(token in lowered for token in ["ingest", "摄取", "导入"]):
        target = _last_path_like_token(clean) or ("all" if any(token in lowered for token in ["all", "全部", "所有"]) else "")
        return AgentAction("ingest", target=target)
    if any(token in lowered for token in ["health check", "健康检查", "结构检查"]):
        return AgentAction("health_check")
    if any(token in lowered for token in ["audit", "审计", "语义健康", "校对"]):
        save = any(token in lowered for token in ["save", "保存"])
        return AgentAction("health_audit_save" if save else "health_audit", save=save)
    if lowered.startswith(("search ", "find ", "搜索", "查找")):
        query = _strip_leading_intent(clean, ["search", "find", "搜索", "查找"])
        return AgentAction("search", text=query, deep=deep)
    if any(token in lowered for token in ["save answer", "保存回答", "保存查询"]):
        return AgentAction("query_save", text=clean, save=True, deep=deep)
    if _looks_like_question(lowered):
        return AgentAction("query", text=clean, deep=deep)
    return None


def route_with_llm(
    paths: WikiPaths,
    text: str,
    *,
    provider: ProviderConfig | None,
    client_factory: ClientFactory,
) -> AgentAction | None:
    if provider is None or "agent" not in provider.usage:
        return None
    try:
        usage = provider.usage["agent"]
        system_prompt = load_system_prompt(paths, usage)
        response = client_factory(provider).chat(
            system_prompt=system_prompt,
            user_prompt=build_agent_planner_prompt(text),
            temperature=usage.temperature,
            top_p=usage.top_p,
            max_tokens=usage.max_tokens,
        )
        action = parse_planner_action(response.content)
        if action and action.action in {"query", "query_save", "search"} and not action.text:
            return AgentAction(action.action, text=text, target=action.target, save=action.save, deep=action.deep)
        return action
    except Exception:
        return None


def build_agent_planner_prompt(text: str) -> str:
    return f"""Classify the user request into one safe LLM Wiki action.

Return JSON only:
{{"action": "query", "text": "...", "target": "", "save": false, "deep": false}}

Allowed action values:
{", ".join(sorted(ACTION_TYPES - {"exit", "help"}))}

Rules:
- Use `query` for ordinary questions.
- Use `search` for requests to find pages.
- Use `source_register` for registering raw source files.
- Use `ingest` for source ingestion.
- Use `health_check` for offline structure checks.
- Use `health_audit` or `health_audit_save` for semantic maintenance review.
- Do not invent shell commands or file edits.

User request:
{text}
"""


def parse_planner_action(content: str) -> AgentAction | None:
    raw = content.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.removeprefix("json").strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end >= start:
        raw = raw[start : end + 1]
    data = json.loads(raw)
    action = str(data.get("action") or "").strip()
    if action not in ACTION_TYPES:
        return None
    return AgentAction(
        action=action,
        text=str(data.get("text") or ""),
        target=str(data.get("target") or ""),
        save=bool(data.get("save")),
        deep=bool(data.get("deep")),
    )


def _strip_leading_intent(text: str, prefixes: list[str]) -> str:
    stripped = text.strip()
    lowered = stripped.lower()
    for prefix in prefixes:
        if lowered.startswith(prefix.lower()):
            return stripped[len(prefix) :].strip(" :：")
    return stripped


def _last_path_like_token(text: str) -> str:
    for token in reversed(text.split()):
        if "/" in token or token.endswith((".md", ".txt", ".pdf")):
            return token.strip("`'\"")
    return ""


def _looks_like_question(lowered: str) -> bool:
    if "?" in lowered or "？" in lowered:
        return True
    return lowered.startswith(
        (
            "what ",
            "why ",
            "how ",
            "when ",
            "where ",
            "compare ",
            "explain ",
            "summarize ",
            "什么",
            "为什么",
            "怎么",
            "如何",
            "对比",
            "解释",
            "总结",
        )
    )
