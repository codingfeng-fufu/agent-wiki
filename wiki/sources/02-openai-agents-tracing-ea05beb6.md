---
title: "02 openai agents tracing"
type: source
status: draft
sources: ["02-openai-agents-tracing-ea05beb6"]
tags: []
---

# OpenAI Agents SDK Tracing

This source card points to the OpenAI Agents SDK tracing documentation. It is useful for a wiki section on how to debug, replay, and evaluate agent behavior.

## Why This Matters

Agent behavior is difficult to debug from final answers alone. Tracing provides a structured record of model calls, tool calls, handoffs, guardrails, and workflow steps.

## Key Ideas To Extract

- What should be captured as trace spans in an agent run.
- How traces help debug tool calls, latency, and failures.
- How tracing connects to evaluation and regression testing.
- Which trace data is safe to store, and which data may contain secrets or user content.

## Wiki Pages This Should Inform

- [[Agent Tracing]]
- [[Agent Observability]]
- [[Tool Call Logs]]
- [[Agent Regression Testing]]
- [[Replayable Agent Runs]]

## Related Map

- [[Agent Development Knowledge Map]]
