# Architecture

LLM Wiki is built around one boundary:

```text
raw/ immutable evidence -> wiki/ maintained Markdown -> MCP tools for agents
```

The project keeps raw source material separate from the maintained knowledge
layer. Agents can read evidence, maintain Markdown pages, query the wiki, and
use safe planned writes without turning the repository into an unbounded shell
automation surface.

## Layers

### raw/

`raw/` contains source material. It is treated as read-only evidence.

Typical paths:

- `raw/inbox/`: new files waiting to be registered.
- `raw/processed/`: registered source copies.
- `raw/assets/`: local source attachments.

Agent workflows should not rewrite raw evidence.

### wiki/

`wiki/` is the maintained Markdown knowledge layer.

Typical page types:

- source pages under `wiki/sources/`
- concept pages under `wiki/concepts/`
- analysis pages under `wiki/analyses/`
- `wiki/index.md` for navigation
- `wiki/log.md` for chronological maintenance history

Pages should preserve provenance through source IDs, citations, and useful
Obsidian-style `[[links]]`.

### .llmw/

`.llmw/` contains local runtime state: project config, source registry, plans,
sessions, caches, qmd databases, and search daemon files. Most of it is local
state and should not be published.

## Agent Interface

The primary integration path is MCP:

```bash
llmw mcp --root .
```

Important MCP tools:

- `llmw_context`: project state and recommended next commands.
- `llmw_search`: fast or deep search over maintained wiki pages.
- `llmw_query`: answer from wiki evidence through the configured provider.
- `llmw_plan`: create a constrained plan for supported write workflows.
- `llmw_apply`: dry-run or apply a saved safe plan.
- `llmw_health_check`: offline structural validation.

CLI commands mirror these flows for debugging, CI, and runtimes without MCP.

## Safe Writes

LLM Wiki deliberately separates planning from mutation.

1. The agent creates a plan with `llmw_plan` or `llmw plan`.
2. The user or agent inspects the plan and expected writes.
3. `llmw_apply` runs with `dry_run: true`.
4. A real apply only executes whitelisted actions.

`wiki_patch` rejects absolute paths, path traversal, and writes outside allowed
project areas. Raw sources are not a valid patch target.

## Retrieval

Default search uses fast local text retrieval so agent calls stay responsive.
Deep search can use qmd when recall matters more than latency. A search daemon
keeps deep retrieval warm for repeated queries:

```bash
llmw search-daemon start --deep
```

MCP deep search reuses the daemon when available.

## Release Boundary

Release checks audit package artifacts so local runtime state and private
knowledge-base data do not ship accidentally. Public packages should include the
tooling, docs, tests, templates, plugin examples, and placeholder raw
directories, not private `.llmw/` caches or local secrets.
