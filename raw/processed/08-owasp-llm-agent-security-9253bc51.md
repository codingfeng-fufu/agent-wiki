---
title: OWASP LLM Application Security
source_url: https://genai.owasp.org/llm-top-10/
source_type: official_doc_source_card
topic: LLM and agent security risks
tags: [agent-development, security, owasp, prompt-injection]
---

# OWASP LLM Application Security

This source card points to the OWASP Top 10 for LLM Applications. It is useful for a security-focused wiki section on prompt injection, sensitive data exposure, tool abuse, and agentic risk.

## Why This Matters

Agent systems increase security risk because model outputs can trigger tools, file writes, network calls, or data disclosure. Security has to be designed into the workflow instead of added after the fact.

## Key Ideas To Extract

- Prompt injection as a core LLM application risk.
- Sensitive information disclosure in prompts, traces, and logs.
- Tool or plugin misuse when model output controls actions.
- Supply chain and model/tool dependency risks.

## Wiki Pages This Should Inform

- [[Prompt Injection]]
- [[Agent Security]]
- [[Tool Abuse]]
- [[Sensitive Data Exposure]]
- [[Least Privilege]]

## Questions For Ingest

- Which raw sources should be treated as untrusted instructions?
- How should `llmw ingest run` distinguish evidence content from executable instructions?
- What secrets must never appear in traces, logs, or wiki pages?

