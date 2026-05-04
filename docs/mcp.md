# MCP Integration

LLM Wiki is primarily designed for agents that can call MCP tools.

## Run The Server

```bash
.venv/bin/llmw mcp --root .
```

The server supports Codex-compatible JSONL stdio framing and
`Content-Length` framing.

## Tools

Common tools exposed through MCP:

- `llmw_context`: project state, health summary, provider status, recommended commands.
- `llmw_next`: lightweight maintenance task discovery.
- `llmw_maintain`: maintenance planning, with optional semantic audit.
- `llmw_health_check`: offline structural health checks.
- `llmw_search`: low-latency wiki search with optional deep mode.
- `llmw_query`: answer from wiki evidence through the configured LLM provider.
- `llmw_plan`: create a safe tool plan.
- `llmw_apply`: dry-run or apply a saved plan.
- `llmw_benchmark_search`: run the retrieval benchmark.

## Resources

The MCP server exposes project context as resources:

- `llmw://context`
- `llmw://project/agents`
- `llmw://project/readme`
- `llmw://system/target-state`
- `llmw://system/architecture`
- `llmw://wiki/index`
- `llmw://wiki/log`
- `llmw://wiki/page/{path}`

## Prompts

Reusable prompts include:

- `llmw_agent_router`
- `llmw_ingest`
- `llmw_query`
- `llmw_health_audit`
- `llmw_maintain_runbook`

## Codex Setup

Install and test the Codex MCP configuration:

```bash
.venv/bin/llmw integration codex install --json
.venv/bin/llmw integration codex test --json
```

Equivalent config:

```toml
[mcp_servers.llm_wiki]
command = "/path/to/LLM_wiki/.venv/bin/llmw"
args = ["mcp", "--root", "/path/to/LLM_wiki"]
default_tools_approval_mode = "approve"
```

For one-off non-interactive execution:

```bash
codex -a never -s read-only exec --ephemeral -C /path/to/LLM_wiki \
  -c 'mcp_servers.llm_wiki.command="/path/to/LLM_wiki/.venv/bin/llmw"' \
  -c 'mcp_servers.llm_wiki.args=["mcp","--root","/path/to/LLM_wiki"]' \
  -c 'mcp_servers.llm_wiki.default_tools_approval_mode="approve"' \
  'Use the llm_wiki MCP server. Call llmw_context and llmw_search for guardrails.'
```

## Agent Contract

Agents should treat MCP tools as the primary interface:

1. Call `llmw_context` before project work.
2. Search with `llmw_search` before answering or editing.
3. Use `deep: true` only when high recall is worth the latency or the returned
   `strategy` recommends it.
4. Use `llmw_plan` and `llmw_apply` for planned write operations.
5. Prefer `llmw_apply` with `dry_run: true` before a real apply.
6. Run `llmw_health_check` before considering maintenance complete.

CLI commands are fallback and debug paths when MCP is unavailable.
