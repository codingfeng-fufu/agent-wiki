---
title: Tool Call Logs
type: concept
status: draft
sources: ["02-openai-agents-tracing-ea05beb6"]
tags: [agent-development, tools, logs]
---

# Tool Call Logs

Tool call logs record tool invocations, results, and failures during an agent run. The tracing source card identifies tool calls as part of the structured record needed to debug agent behavior.

## Uses

- Audit when an agent reads, writes, or calls external systems.
- Compare tool behavior across [[Replayable Agent Runs]].
- Support [[Tool Safety]] by exposing action history.

## Related Sources

- [[02-openai-agents-tracing-ea05beb6]]
