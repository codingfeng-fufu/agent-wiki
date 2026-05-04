---
title: Tool Abuse
type: concept
status: draft
sources: ["08-owasp-llm-agent-security-9253bc51"]
tags: [security, tools]
---

# Tool Abuse

Tool abuse occurs when model-controlled actions are misused or triggered unsafely. The OWASP source card highlights tool or plugin misuse when model output controls actions.

## Mitigations

- Apply [[Least Privilege]] to tool access.
- Use [[Input Guardrails]] and [[Output Guardrails]] around risky actions.
- Keep [[Tool Call Logs]] for auditability.

## Related Sources

- [[08-owasp-llm-agent-security-9253bc51]]
