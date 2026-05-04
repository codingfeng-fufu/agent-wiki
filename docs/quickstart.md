# Quickstart

This guide assumes you are working from a local clone of the repository.

## Install

```bash
uv sync --extra dev
```

Optional deep search support:

```bash
uv sync --extra dev --extra search
```

Initialize the project and check the local setup:

```bash
.venv/bin/llmw init
.venv/bin/llmw doctor --json
```

## Start The MCP Server

```bash
.venv/bin/llmw mcp --root .
```

Agent runtimes should call MCP tools first. CLI commands remain useful for CI,
debugging, and runtimes without MCP support.

## Add A Source

Place Markdown, text, or PDF source material under `raw/inbox/`, then register it:

```bash
.venv/bin/llmw source add raw/inbox/example.md
```

For a public sample source, copy one of the synthetic files from `raw/examples/`
into `raw/inbox/` first.

Chinese samples are available under `raw/examples/zh-CN/`.

Create an ingest packet:

```bash
.venv/bin/llmw ingest packet <source_id>
```

The packet gives an agent the evidence path, expected wiki edits, and project
rules. After the agent writes the related wiki pages, record the result:

```bash
.venv/bin/llmw ingest record <source_id> --page wiki/sources/<source_id>.md
```

## Search And Query

```bash
.venv/bin/llmw search "agent memory" --json
.venv/bin/llmw query "what does this wiki say about agent memory?"
```

Save a useful answer back into the wiki:

```bash
.venv/bin/llmw query "compare MCP and A2A" --save
```

## Maintain

```bash
.venv/bin/llmw maintain --json
.venv/bin/llmw health check --json
```

For planned write operations:

```bash
.venv/bin/llmw plan "register all pending inbox sources" --json --save --preview
.venv/bin/llmw apply .llmw/plans/<plan_id>.json --dry-run --json
.venv/bin/llmw apply .llmw/plans/<plan_id>.json --json
```

## Configure An LLM Provider

LLM-backed ingest, query, and semantic audit flows use provider configuration
under `system/providers/` and local secrets from the environment or `.llmw/.env`.
The default project configuration expects:

```bash
export DASHSCOPE_API_KEY=your-dashscope-api-key
.venv/bin/llmw llm check
```

Keep `.llmw/.env` private. It is intentionally ignored by git.
