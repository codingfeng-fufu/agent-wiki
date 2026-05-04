---
title: Sensitive Data Exposure
type: concept
status: draft
sources: ["08-owasp-llm-agent-security-9253bc51"]
tags: [security, privacy]
---

# Sensitive Data Exposure

Sensitive data exposure is a security risk for LLM and agent systems. The OWASP source card specifically calls out sensitive information disclosure in prompts, traces, and logs.

## Wiki Implications

- Do not store API keys or secrets in wiki pages.
- Redact secrets in [[Agent Tracing]] and [[Tool Call Logs]].
- Treat source excerpts and generated summaries as potentially shareable artifacts.

## Related Sources

- [[08-owasp-llm-agent-security-9253bc51]]
