# Quickstart

This guide assumes you are using LLM Wiki from a local GitHub clone. The first
public version is intentionally clone-first; PyPI installation is a later
publishing step.

## Install

```bash
git clone https://github.com/codingfeng-fufu/agent-wiki.git
cd agent-wiki
uv sync --extra dev
```

Optional deep search support:

```bash
uv sync --extra dev --extra search
```

The examples below use `uv run llmw`. After `uv sync`, the local executable is
also available as `.venv/bin/llmw`.

## Check The Included Wiki

This repository includes a maintained example wiki about agent development.
Start by checking project state:

```bash
uv run llmw context --root . --json
```

Search the maintained wiki:

```bash
uv run llmw search "prompt injection tool safety" --root . --limit 3 --json
```

Run offline structural validation:

```bash
uv run llmw health check --root . --json
```

Run the read-only proof demo:

```bash
scripts/demo.sh
```

The demo does not edit tracked wiki content. It writes only ignored local state
under `.llmw/plans/` while previewing safe apply behavior.

A successful first run should show project context, search results, a saved
plan preview, an apply dry-run, and a final health check with no issues.

## Create A Fresh Wiki

To try the pattern in a new directory:

```bash
mkdir /tmp/my-llm-wiki
cd /tmp/my-llm-wiki
uv run --project /path/to/llm-wiki llmw init --root .
uv run --project /path/to/llm-wiki llmw doctor --root . --json
```

If you are working inside this repository, `llmw init --root .` is already done.
Use it only for a new workspace or when intentionally regenerating missing
project files.

## Add A Source

Place Markdown, text, or PDF source material under `raw/inbox/`, then register
it:

```bash
uv run llmw source add raw/inbox/example.md --root . --json
uv run llmw source list --root . --json
```

For a public sample, copy one synthetic source from `raw/examples/` into
`raw/inbox/` first. Chinese samples are available under `raw/examples/zh-CN/`.

Create an ingest packet:

```bash
uv run llmw ingest packet <source_id> --root .
```

The packet gives an agent the source text, expected wiki edits, and operating
rules. After the agent writes the related wiki pages, record the result:

```bash
uv run llmw ingest record <source_id> \
  --page wiki/sources/<source_id>.md \
  --root . \
  --json
```

Rebuild and verify:

```bash
uv run llmw index rebuild --root . --json
uv run llmw health check --root . --json
```

## Search And Query

Search is local and works without an LLM provider:

```bash
uv run llmw search "agent memory" --root . --json
uv run llmw search "how should agents handle prompt injection?" --root . --json
```

LLM-backed query requires a configured provider:

```bash
uv run llmw query "what does this wiki say about agent memory?" --root .
uv run llmw query "compare MCP and A2A" --root . --save
```

For a deterministic demo without a live provider:

```bash
uv run llmw query "Agent guardrails 主要解决什么问题？" \
  --root . \
  --provider-config reports/qa-demo/mock-provider.json \
  --limit 3 \
  --max-page-chars 1600
```

## Use MCP

Start the MCP server:

```bash
uv run llmw mcp --root .
```

Agent runtimes should use MCP tools first and CLI commands as fallback/debug
paths. The normal tool loop is:

```text
llmw_context -> llmw_search -> llmw_plan -> llmw_apply dry_run=true -> llmw_health_check
```

See [MCP integration](mcp.md) and
[agent-loop.md](../examples/agent-loop.md).

## Configure An LLM Provider

LLM-backed ingest, query, and semantic audit flows use provider configuration
under `system/providers/` and local secrets from the environment or `.llmw/.env`.
The default project configuration expects:

```bash
export DASHSCOPE_API_KEY=your-dashscope-api-key
uv run llmw llm check --root . --json
```

Keep `.llmw/.env` private. It is intentionally ignored by git.

Provider setup is optional for the public-alpha local path. `context`, `search`,
`health check`, `plan`, `apply --dry-run`, and `scripts/demo.sh` all work
without an API key.

## Release-Readiness Check

Before publishing or opening a substantial pull request, run:

```bash
uv run llmw release check --root . --sdist --no-codex --no-strict --json
```

This composes doctor, health, tests, search benchmark, and source distribution
audit. A provider-key warning is acceptable unless you are testing LLM-backed
query, ingest, or semantic audit flows.
