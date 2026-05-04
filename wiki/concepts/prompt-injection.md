---
title: Prompt Injection
type: concept
status: draft
sources: ["08-owasp-llm-agent-security-9253bc51"]
tags: [security, prompt-injection]
---

# Prompt Injection

Prompt injection is a core LLM application risk identified by the OWASP source card. In this wiki context, the immediate concern is raw source text that may contain instructions the agent should treat as evidence rather than commands.

## Wiki Implications

- Raw sources should not override system or project instructions.
- [[Input Guardrails]] should help distinguish evidence from executable instructions.
- [[Tool Safety]] should limit what injected text can cause the agent to do.

## Related Sources

- [[08-owasp-llm-agent-security-9253bc51]]
