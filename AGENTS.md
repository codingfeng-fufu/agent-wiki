# LLM Wiki Agent Guide

You maintain `wiki/`; raw sources under `raw/` are read-only evidence.

Agent-native workflow:
1. Prefer the MCP server: launch `llmw mcp --root .` and use the exposed `llmw_*` tools instead of repeatedly spawning CLI commands.
2. Start with `llmw_context` to understand project state.
3. Use `llmw_maintain` for routine maintenance planning, or `llmw_next` for lightweight task discovery.
4. Use `llmw_search` for lookup before answering or editing; inspect the `strategy` field to decide whether `deep: true` is warranted.
5. For repeated high-recall retrieval, pre-warm `llmw search-daemon start --deep`; MCP/CLI deep search will reuse the running daemon when available.
6. CLI commands such as `llmw context --json`, `llmw search <query> --json`, and `llmw maintain --json` are fallback/debug paths when MCP is unavailable.
7. Run `llmw_benchmark_search` or `llmw benchmark search --json` after search changes.
8. For write operations that can be planned, use `llmw_plan`, inspect the plan, then prefer `llmw_apply` with `dry_run: true` before a real apply.
9. Never run arbitrary shell edits through this tool; use the documented `llmw` primitives.

Workflow:
1. Use `llmw source add <path>` to register new Markdown/Text/PDF sources.
2. Use `llmw ingest packet <source_id>` before editing wiki pages.
3. Create or update source, entity, concept, and analysis pages with Obsidian `[[links]]`.
4. Keep `source_id` references in frontmatter or citations for factual claims.
5. Run `llmw ingest record <source_id> --page <path>` after edits.
6. Use `llmw health check` before considering work complete.

Do not rewrite raw sources. Prefer small, connected pages over large unlinked summaries.
