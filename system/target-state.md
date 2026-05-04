# LLM Wiki Target State

## 1. Positioning

LLM Wiki is an agent-native local knowledge compiler and long-term memory tool layer.

It is not a consumer note-taking product, a RAG chat box, or a SaaS knowledge base. Its primary users are coding and research agents such as Codex, Claude Code, OpenCode, and similar local agent runtimes.

The user provides source material, asks questions, reviews outcomes, and decides direction. The agent uses `llmw` to compile raw sources into a maintained, linked, source-backed Markdown wiki.

## 2. Core Promise

Traditional RAG retrieves raw chunks at question time. LLM Wiki compiles knowledge once and keeps the compiled layer maintained.

The maintained wiki becomes the agent's durable working memory:

- concepts are already extracted;
- relationships are already linked;
- contradictions can be audited;
- useful answers can be archived;
- source traceability is preserved;
- search quality can be benchmarked over time.

## 3. User Experience

The intended workflow is:

1. Put raw material under `raw/inbox/`.
2. Register sources with `llmw source add <path>`.
3. Generate an ingest packet with `llmw ingest packet <source_id>`.
4. Let the agent update `wiki/` pages.
5. Record completed work with `llmw ingest record <source_id> --page <path>`.
6. Ask questions through `llmw search`, `llmw query`, or an agent using those commands.
7. Run `llmw maintain`, `llmw health check`, `llmw health audit`, and `llmw benchmark search` to keep the wiki healthy.

The user should not need to manually maintain cross-links, index entries, logs, or source registry state.

## 4. Agent Contract

LLM Wiki must be easy and safe for agents to call.

Required contract:

- Core commands support `--json`.
- Successful JSON output uses `{"ok": true, ...}`.
- Failed JSON output uses `{"ok": false, "error": {"code": "...", "message": "..."}}`.
- Raw sources are read-only.
- Wiki writes are source-backed.
- Index, log, and source registry are updated after maintenance work.
- High-risk write operations are planned before they are applied.
- Arbitrary shell writes are outside the `llmw` apply contract.

The `AGENTS.md` file is the local operating protocol. A new agent should be able to enter the repo, run `llmw context --json`, read `AGENTS.md`, and safely continue maintenance.

## 5. Knowledge Structure

The final workspace structure is:

- `raw/`: immutable evidence layer.
- `.llmw/sources.json`: source ledger.
- `wiki/sources/`: source cards.
- `wiki/concepts/`: durable concept pages.
- `wiki/entities/`: entity pages when the domain needs them.
- `wiki/analyses/`: synthesis and comparison pages.
- `wiki/outputs/`: saved answers, audits, and generated outputs.
- `wiki/index.md`: navigable content index.
- `wiki/log.md`: chronological maintenance log.
- `system/`: prompts, providers, templates, architecture rules, and target-state documents.
- `.llmw/`: local state, qmd cache, plans, and sessions.

Pages should be small, linked, and source-backed. Large unlinked summaries are a failure mode.

## 6. Retrieval Layer

Search must support both low-latency agent lookup and high-recall knowledge discovery.

Target behavior:

- `llmw search <query> --json` is the default fast path.
- Fast search uses `rg` or Python scanning and should return in roughly one second on small-to-medium wikis.
- JSON search output includes a `strategy` field that tells the agent when deep search is recommended.
- `llmw search --deep` uses qmd hybrid retrieval for higher recall.
- `llmw search-server --deep` keeps the retrieval backend warm for repeated agent calls.
- `llmw search-daemon start --deep` provides start/status/stop lifecycle management for a warm local search backend.
- `llmw benchmark search` measures Precision, Recall, F1, HitRate, and MRR against a fixed query set.

Agent guidance:

- Use fast search for exact lookup, title lookup, and simple follow-up questions.
- Use deep search for cross-cutting, multi-concept, or recall-sensitive questions.
- Use `search-server --deep` when the agent can hold an NDJSON stdio process.
- Use `search-daemon start --deep` when the agent needs a background warm service.

## 7. Maintenance Loop

The core maintenance loop is:

1. `llmw context --json`
2. `llmw next --json` or `llmw maintain --json`
3. perform source-backed wiki edits
4. `llmw ingest record ...`
5. `llmw health check`
6. `llmw benchmark search`
7. optionally `llmw health audit`

`maintain` should become the agent's routine entry point. It should summarize state, detect obvious pending work, run structural checks, optionally run semantic audit, and produce a safe plan.

Semantic audit findings should become structured maintenance plan steps rather than only Markdown prose. Low-confidence semantic suggestions should remain review-only until a human or higher-level agent converts them into concrete `wiki_patch` steps.

## 8. Safety Model

Safety is part of the product boundary.

Rules:

- Never rewrite `raw/`.
- Never commit secrets.
- Do not put real API keys in wiki, logs, or packaged distributions.
- Validate LLM-generated pages before writing.
- Use path allowlists for automated write operations.
- Preview automated writes with dry-run diffs before applying them.
- Keep source IDs in frontmatter or body citations for factual claims.
- Keep logs concise but sufficient for reconstructing maintenance history.
- Prefer planned writes over implicit large rewrites.

The system should make safe agent behavior the default path, not a convention that depends on memory.

## 9. Quality Gates

A release-quality workspace must pass:

- unit tests;
- packaging tests;
- `llmw health check`;
- `llmw benchmark search`;
- optional deep search benchmark;
- optional LLM smoke tests;
- source registry consistency checks;
- sdist checks that exclude `.llmw/`, private raw content, and real API keys.

Search quality should not be judged by feel. It should be tracked by benchmark metrics and gate thresholds.

## 10. Final Components

The final form should include:

- CLI commands for humans and agents.
- Product-facing doctor command for readiness diagnostics.
- Machine-readable release check command for CI and handoff.
- Audited package build command for local distribution artifacts.
- Product-facing agent runtime install commands.
- JSON contract for reliable parsing.
- NDJSON search server for warm high-frequency retrieval.
- Search daemon lifecycle management for background warm retrieval.
- MCP server for native agent integration.
- MCP resources for project state, operating protocol, index, logs, and wiki page reading.
- MCP prompts for repeatable ingest, query, health-audit, routing, and maintenance workflows.
- Codex setup helpers for status, config installation, and MCP probing.
- Planner/apply workflow for safe writes.
- Health checks for structural integrity.
- LLM semantic audit for maintenance recommendations.
- Benchmark harness for retrieval quality.
- Performance benchmark harness for agent-facing latency.
- Prompt, provider, and template configuration under `system/`.

The CLI is the first interface. MCP/plugin integration is the final agent-native interface.

## 11. Non-Goals

LLM Wiki should not become:

- a full consumer note-taking app;
- a proprietary hosted service by default;
- a generic vector database wrapper;
- a chat-only RAG interface;
- a UI-first product that hides the underlying Markdown wiki;
- a system that requires users to manually maintain indexes, logs, links, or source records.

Markdown files remain the source of maintained knowledge because they are transparent, diffable, reviewable, and portable.

## 12. Success Criteria

The target state is reached when:

- an agent can understand the workspace from `AGENTS.md` and `llmw context --json`;
- a new source can be registered, ingested, linked, logged, indexed, and checked without manual bookkeeping;
- ordinary lookup is fast and high-recall lookup has a warm server path;
- semantic maintenance issues are discoverable and can be turned into plans;
- release checks prove that health and retrieval quality have not regressed;
- the tool can be installed as a local plugin for agent runtimes.
- MCP tools, resources, prompts, and plugin templates let agents call the wiki without scraping human CLI output.

In one sentence:

> LLM Wiki is a local knowledge compiler for agents: it turns raw sources into a maintained, source-backed Markdown knowledge graph and exposes that graph through safe, testable, agent-native tools.
