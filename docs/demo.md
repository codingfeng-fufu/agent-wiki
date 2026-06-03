# Demo

LLM Wiki has two demo layers:

- a short proof demo for GitHub visitors
- the checked-in agent-development wiki as a fuller example corpus

## Short Proof Demo

```bash
uv sync --extra dev
scripts/demo.sh
```

The script prints:

1. `llmw context --json`
2. `llmw search "prompt injection tool safety" --limit 5 --json`
3. `llmw maintain --no-audit --no-save-plan --json`
4. `llmw plan "rebuild index before publishing" --json --save --preview`
5. `llmw apply <saved_plan> --dry-run --json`
6. `llmw health check --json`

The demo does not edit tracked wiki content. The `plan --save` step writes an
ignored local plan file under `.llmw/plans/`, and the apply step is a dry-run.

## What The Demo Proves

- Project context is machine-readable for agents.
- Search works locally without an external service or model provider.
- Maintenance planning can run without an LLM audit call.
- Planned writes can be previewed before applying.
- Structural health checks pass at the end of the agent loop.

Expected success signals:

- `context` reports the included wiki, ingested sources, and current index.
- `search` returns maintained wiki pages such as Prompt Injection or Tool
  Safety.
- `plan --preview` shows the intended write target before any apply step.
- `apply --dry-run` returns `dry_run: true`.
- `health check` returns an empty issue list.

The only local side effect is an ignored plan file under `.llmw/plans/`. No
tracked `raw/` or `wiki/` content should change after running the script.

## Full Example Wiki

The repository also includes a maintained wiki about agent development. It
contains source pages, concept pages, and an analysis map covering guardrails,
MCP, tracing, durable execution, multi-agent orchestration, interoperability,
and security.

Start here:

- [Examples](../examples/README.md)
- [Agent development knowledge map](../wiki/analyses/agent-development-knowledge-map.md)
- [Prompt Injection](../wiki/concepts/prompt-injection.md)
- [Model Context Protocol](../wiki/concepts/model-context-protocol.md)

Try:

```bash
uv run llmw search "MCP tools resources prompts" --root . --json
uv run llmw search "durable execution checkpointing" --root . --json
uv run llmw benchmark search --root . --provider python --top-k 5 --json
```

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

## Record A Terminal Demo

After the first public release, record the script as a short terminal GIF or
asciinema cast:

```bash
scripts/record_demo.sh
```

For a README GIF, keep the recording under 40 seconds and trim the output to the
main loop: context, search, plan dry-run, health. The goal is to prove that the
agent workflow is real, not to show every command in the project.

## Troubleshooting

- If the script cannot find `.venv/bin/llmw`, run `uv sync --extra dev`.
- If a provider warning appears, it is not a demo failure; the demo does not
  require `DASHSCOPE_API_KEY`.
- If a saved plan is left behind, it is under ignored local state and can be
  removed with `rm -f .llmw/plans/*.json`.
