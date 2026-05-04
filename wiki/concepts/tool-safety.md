---
title: Tool Safety
type: concept
status: draft
sources:
  - "01-openai-agents-guardrails-87ce73bd"
  - "08-owasp-llm-agent-security-9253bc51"
tags: [agent-development, tools, safety]
---

# Tool Safety

Tool safety is the design of constraints around actions that an agent can invoke. The guardrails source card connects guardrails to tool permissions, while the OWASP source card highlights risk when model output controls actions.

## Design Concerns

- Use [[Least Privilege]] for tool permissions.
- Treat raw source text as evidence, not executable instruction.
- Log tool activity through [[Tool Call Logs]] when actions affect files or external systems.
- Consider [[Idempotent Tool Calls]] for retryable workflows.

## Related Sources

- [[01-openai-agents-guardrails-87ce73bd]]
- [[08-owasp-llm-agent-security-9253bc51]]
