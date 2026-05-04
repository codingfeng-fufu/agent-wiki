---
title: "08 owasp llm agent security"
type: source
status: draft
sources: ["08-owasp-llm-agent-security-9253bc51"]
tags: []
---

# OWASP LLM Application Security

This source card points to the OWASP Top 10 for LLM Applications. It is useful for a security-focused wiki section on [[Prompt Injection]], [[Sensitive Data Exposure]], [[Tool Abuse]], and agentic risk.

## Why This Matters

Agent systems increase security risk because model outputs can trigger tools, file writes, network calls, or data disclosure. Security has to be designed into the workflow instead of added after the fact.

## Key Ideas To Extract

- Prompt Injection as a core LLM application risk.
- Sensitive Data Exposure in prompts, traces, and logs.
- Tool Abuse when model output controls actions.
- Supply chain and model/tool dependency risks — relevant to [[Agent Runtime]] and [[Protocol Boundary]].

## Related Wiki Pages

- [[Agent Security]]
- [[Least Privilege]]
- [[Prompt Injection]]
- [[Sensitive Data Exposure]]
- [[Tool Abuse]]

## Related Map

- [[Agent Development Knowledge Map]]
