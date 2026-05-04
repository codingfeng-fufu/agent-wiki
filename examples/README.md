# Examples

This repository includes a small working example wiki about agent development.
It is meant to show the kind of maintained knowledge layer LLM Wiki can produce,
not to be a complete reference corpus.

The repository also includes small synthetic raw sources under
[`raw/examples/`](../raw/examples/README.md). They show the expected evidence
shape without requiring private documents.

## Example Knowledge Map

Start here:

- [Agent development knowledge map](../wiki/analyses/agent-development-knowledge-map.md)

Useful concept pages:

- [Prompt injection](../wiki/concepts/prompt-injection.md)
- [Tool safety](../wiki/concepts/tool-safety.md)
- [Model Context Protocol](../wiki/concepts/model-context-protocol.md)
- [MCP vs A2A](../wiki/concepts/mcp-vs-a2a.md)
- [Durable agent execution](../wiki/concepts/durable-agent-execution.md)

Source cards:

- [OpenAI Agents guardrails](../wiki/sources/01-openai-agents-guardrails-87ce73bd.md)
- [OpenAI Agents tracing](../wiki/sources/02-openai-agents-tracing-ea05beb6.md)
- [MCP tools, resources, and prompts](../wiki/sources/03-mcp-tools-resources-prompts-420d2910.md)
- [OWASP LLM application security](../wiki/sources/08-owasp-llm-agent-security-9253bc51.md)

## Run The Demo

```bash
scripts/demo.sh
```

The demo shows context, search, maintenance planning, safe apply dry-run, and
health verification using the example wiki.

## Try These Queries

```bash
llmw search "prompt injection tool safety" --json
llmw search "MCP tools resources prompts" --json
llmw search "durable execution checkpointing" --json
llmw query "how should agents reduce prompt injection risk?"
```

These queries show why a maintained wiki is useful: the agent can search concept
pages, source cards, and analysis pages instead of repeatedly reconstructing the
same context from raw files.

## Use With An Agent

See [agent-loop.md](agent-loop.md) for a compact MCP instruction block that can
be pasted into an agent runtime.
