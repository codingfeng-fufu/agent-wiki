# Roadmap

LLM Wiki is alpha-stage software. The current goal is to make the local
agent-facing knowledge loop reliable before broadening integrations.

## 0.1: Public Alpha

- MCP server for context, search, query, maintenance planning, and safe apply.
- Codex integration helpers and local plugin template.
- Source registry, ingest packets, wiki index/log, and health checks.
- Fast local search with optional qmd deep search and daemon reuse.
- Release checks, package audits, CI, and a runnable read-only demo.

## 0.2: Better Agent Onboarding

- More example projects that show different knowledge-base shapes.
- Sharper starter templates for `AGENTS.md`, source pages, and concept pages.
- Improved demo recording assets for README and launch posts.
- More MCP prompt examples for ingest, query, audit, and maintenance workflows.
- Better docs for running LLM Wiki with multiple agent runtimes.

## 0.3: Retrieval And Maintenance Quality

- Expanded retrieval benchmark coverage.
- Better guidance for when to use fast search, deep search, and daemon search.
- More precise semantic audit workflows.
- Safer plan/apply previews for common wiki maintenance edits.
- More regression tests around MCP contracts and package contents.

## Later

- Plugin packaging and distribution strategy.
- Hosted documentation site if the project outgrows Markdown docs.
- Optional richer UI for local maintenance.
- More provider examples beyond the current OpenAI-compatible path.

## Non-Goals For Now

- Hosted SaaS.
- Replacing Obsidian or Markdown editors.
- Editing raw source evidence.
- Treating arbitrary model output as trusted instructions.
