# Architecture

This project is a local, agent-driven Markdown wiki.

## Layers

- `raw/`: immutable source material. Agents can read these files but should not rewrite them.
- `wiki/`: maintained knowledge pages owned by the LLM agent.
- `system/`: templates and operating rules.
- `.llmw/`: tool state, including config, source registry, and qmd cache.

## Module Boundaries

- `core`: paths, config, frontmatter helpers, and shared data models.
- `sources`: source registration and ingest packet generation.
- `wiki`: page scanning, index generation, link parsing, and log updates.
- `search`: qmd search adapter with rg/Python fallback.
- `mcp`: stdio MCP tools for native agent runtime integration.
- `agent`: context, next-task discovery, maintenance planning, safe apply, and interactive agent sessions.
- `llm`: provider config, LLM-backed ingest, query, and semantic health audit workflows.
- `health`: consistency checks over wiki pages, links, logs, and sources.
- `cli`: Typer command layer only; no business logic should live here.

## Operating Rule

The CLI provides structure, search, validation, indexing, logging, and optional
LLM-backed workflows so an agent can maintain the wiki consistently.

Agent-native integrations build on the same primitives:

- `llmw doctor` provides a product-facing readiness check across project
  structure, health, provider config, search availability, Codex config, and
  optional MCP probing.
- `llmw release check` composes doctor, health, pytest, benchmark gates, and
  optional sdist audit into a machine-readable release readiness report.
- `llmw benchmark perf` records latency for core agent paths and optional deep
  search runs so performance regressions are visible.
- `llmw package build` turns release-ready workspaces into audited wheel/sdist
  artifacts and writes a package report.
- `llmw install-agent codex` provides a product-facing shortcut for installing
  and testing the Codex MCP integration.
- `llmw mcp --root .` exposes context, search, query, maintenance, benchmark,
  plan, and apply tools over stdio MCP.
- MCP deep search runs through a time-limited subprocess and falls back to fast
  search when qmd cold-start exceeds the agent-facing timeout budget.
- The MCP server also exposes resources for project context, operating
  protocol, target-state docs, index/log files, and maintained wiki pages.
- MCP prompts expose repeatable agent workflows for routing, ingest, query,
  semantic audit, and routine maintenance.
- `llmw integration codex status|install|test` checks, writes, and probes the
  Codex MCP configuration from the project CLI.
- `llmw search-server --deep` provides a foreground NDJSON search process.
- `llmw search-daemon start --deep` provides a background warm search service
  with `status`, `query`, and `stop` lifecycle commands.
- `llmw apply --dry-run` previews safe plan writes before mutating files.
