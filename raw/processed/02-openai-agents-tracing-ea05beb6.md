---
title: OpenAI Agents SDK Tracing
source_url: https://openai.github.io/openai-agents-python/tracing/
source_type: official_doc_source_card
topic: agent observability
tags: [agent-development, tracing, observability, openai]
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

## Questions For Ingest

- What trace fields should `llmw ingest run` log for reproducibility?
- Should source ingestion store model name, provider, token usage, and generated page paths?
- How can traces support later evaluation of agent quality?

