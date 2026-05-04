# Demo

This demo is meant to show the project in the way a GitHub visitor should
understand it: LLM Wiki is an agent-facing local knowledge layer with MCP-ready
context, search, maintenance planning, safe apply previews, and health checks.

## Run The Demo

```bash
uv sync --extra dev
scripts/demo.sh
```

The script is read-only for wiki content. It runs:

1. `llmw context --json`
2. `llmw search "prompt injection tool safety" --limit 5 --json`
3. `llmw maintain --no-audit --no-save-plan --json`
4. `llmw plan "rebuild index before publishing" --json --save --preview`
5. `llmw apply <saved_plan> --dry-run --json`
6. `llmw health check --json`

The `plan --save` command writes a local plan file under `.llmw/plans/`, which is
ignored by git. The apply step is a dry run.

## What The Demo Proves

- The project can report its current wiki/source/provider state.
- Search works without starting an external service.
- Maintenance planning can run without LLM audit calls.
- Planned writes can be previewed before applying.
- Structural health checks pass at the end of the loop.

## Record A Terminal Demo

After the first public release, record the script as a short terminal GIF or
asciinema cast:

```bash
scripts/record_demo.sh
```

For a README GIF, keep the recording under 40 seconds and trim the output to the
main loop: context, search, plan dry-run, health. The goal is to prove that the
agent workflow is real, not to show every command in the project.

## Agent-Facing Demo Prompt

If your agent runtime has the LLM Wiki MCP server configured, use:

```text
Use the llm_wiki MCP server.
Call llmw_context, then llmw_search for "prompt injection tool safety".
Create a safe plan for rebuilding the wiki index before publishing.
Dry-run the plan with llmw_apply.
Finish by calling llmw_health_check.
Do not edit raw sources.
```
