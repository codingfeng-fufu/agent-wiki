# Agent Loop Example

Use this as a compact instruction block for an agent runtime that has access to
the LLM Wiki MCP server.

```text
Use the llm_wiki MCP server as the primary interface.

Start by calling llmw_context.
Search with llmw_search before answering or editing.
Use llmw_query when the answer should be synthesized from maintained wiki evidence.
For write operations, call llmw_plan, inspect the plan, then call llmw_apply with dry_run: true before applying.
Do not edit raw sources. raw/ is read-only evidence.
Keep wiki claims source-backed and preserve Obsidian [[links]] where useful.
Run llmw_health_check before considering maintenance complete.
```

For repeated high-recall retrieval, pre-warm deep search outside the agent loop:

```bash
.venv/bin/llmw search-daemon start --deep
```

## Demo Prompt

```text
Use the llm_wiki MCP server.
Call llmw_context, then llmw_search for "prompt injection tool safety".
Create a safe plan for rebuilding the wiki index before publishing.
Dry-run the plan with llmw_apply.
Finish by calling llmw_health_check.
Do not edit raw sources.
```
