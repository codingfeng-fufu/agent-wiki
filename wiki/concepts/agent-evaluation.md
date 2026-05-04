---
title: Agent Evaluation
type: concept
status: draft
sources:
  - "01-openai-agents-guardrails-87ce73bd"
  - "02-openai-agents-tracing-ea05beb6"
tags: [agent-development, evaluation]
---

# Agent Evaluation

Agent evaluation checks whether agent behavior remains safe, useful, and reproducible. Per [[01-openai-agents-guardrails-87ce73bd]], guardrails provide validation signals for unsafe inputs and malformed outputs. Per [[02-openai-agents-tracing-ea05beb6]], traces provide evidence for debugging, evaluation, and [[Agent Regression Testing]].

## Evaluation Inputs

- [[Agent Tracing]] data for model calls, tool calls, handoffs, guardrails, and workflow steps.
- [[Output Guardrails]] results for generated artifacts.
- [[Agent Regression Testing]] cases for repeated behavior checks.

## Related Sources

- [[01-openai-agents-guardrails-87ce73bd]]
- [[02-openai-agents-tracing-ea05beb6]]
