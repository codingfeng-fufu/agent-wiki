---
title: Agent Guardrails
type: concept
status: draft
sources: ["01-openai-agents-guardrails-87ce73bd"]
tags: [agent-development, guardrails, safety]
---

# Agent Guardrails

Agent guardrails are validation boundaries around an agent workflow. The OpenAI Agents SDK guardrails source card frames them as mechanisms for constraining unsafe inputs, malformed outputs, policy violations, and tool misuse.

## Lifecycle Position

- [[Input Guardrails]] run before or near the start of an agent run.
- [[Output Guardrails]] validate generated results before they are returned or used downstream.
- [[Tool Safety]] applies when model output can trigger actions.

## Related Questions

- What guardrails should run before an agent writes files?
- Which failures should stop execution versus request [[Human in the Loop]] review?
- How should [[Agent Evaluation]] test guardrail behavior over time?

## Related Sources

- [[01-openai-agents-guardrails-87ce73bd]]
