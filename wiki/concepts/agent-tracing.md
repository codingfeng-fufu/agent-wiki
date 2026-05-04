---
title: Agent Tracing
type: concept
status: draft
sources: ["02-openai-agents-tracing-ea05beb6"]
tags: [agent-development, tracing, observability]
---

# Agent Tracing

Agent tracing records structured information about an agent run. The tracing source card identifies model calls, tool calls, handoffs, guardrails, and workflow steps as trace-worthy events.

## Uses

- Debug failures and latency.
- Support [[Replayable Agent Runs]] when enough context is preserved.
- Feed [[Agent Evaluation]] and [[Agent Regression Testing]].
- Identify sensitive fields that should not be stored in logs.

## Related Sources

- [[02-openai-agents-tracing-ea05beb6]]
