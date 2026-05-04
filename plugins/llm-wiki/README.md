# LLM Wiki Plugin

This local plugin is agent-facing. Its primary interface is the MCP server exposed by `llmw mcp --root .`; CLI commands are mainly setup, diagnostics, and fallback paths.

Expected runtime:

- install the package in the workspace virtualenv;
- keep `./.venv/bin/llmw` available;
- launch the MCP server from the project root.
- keep `default_tools_approval_mode = "approve"` for non-interactive Codex calls.
- for repeated high-recall searches, pre-warm `llmw search-daemon start --deep`; MCP deep search reuses it when available.

Codex direct configuration:

```toml
[mcp_servers.llm_wiki]
command = "/path/to/LLM_wiki/.venv/bin/llmw"
args = ["mcp", "--root", "/path/to/LLM_wiki"]
default_tools_approval_mode = "approve"
```

Use `default_tools_approval_mode = "approve"` for non-interactive `codex exec`; otherwise Codex can discover the tools but cancel the call while waiting for approval.

Codex setup helpers:

```bash
llmw integration codex status --json
llmw integration codex install --json
llmw integration codex test --json
```

`status` checks the expected command, args, and approval mode. `install` updates `~/.codex/config.toml` with a backup. `test` performs a direct MCP handshake and reads `llmw://context`.

Primary MCP tools:

- `llmw_context`
- `llmw_search`
- `llmw_query`
- `llmw_next`
- `llmw_maintain`
- `llmw_benchmark_search`
- `llmw_health_check`
- `llmw_plan`
- `llmw_apply`

Recommended agent loop:

1. Call `llmw_context`.
2. Call `llmw_next` or `llmw_maintain`.
3. Call `llmw_search` before answering or editing.
4. Use `deep: true` only when recall matters; use a warm deep daemon for repeated deep search.
5. For writes, call `llmw_plan`, then `llmw_apply` with `dry_run: true`, then real `llmw_apply`.
6. Finish with `llmw_health_check`; after search changes, run `llmw_benchmark_search`.

Primary MCP resources:

- `llmw://context`
- `llmw://project/agents`
- `llmw://project/readme`
- `llmw://system/target-state`
- `llmw://system/architecture`
- `llmw://wiki/index`
- `llmw://wiki/log`
- `llmw://wiki/page/{path}`

Primary MCP prompts:

- `llmw_agent_router`
- `llmw_ingest`
- `llmw_query`
- `llmw_health_audit`
- `llmw_maintain_runbook`

Write safety:

- read tools execute directly;
- write tools should use `llmw_plan` followed by `llmw_apply` with `dry_run: true`;
- `wiki_patch` can only write under `wiki/` or `system/`.
