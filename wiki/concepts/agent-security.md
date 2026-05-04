---
title: Agent Security
type: concept
status: draft
sources:
  - "04-langgraph-durable-execution-2b964c83"
  - "07-a2a-agent-interoperability-fc58e8a2"
  - "08-owasp-llm-agent-security-9253bc51"
tags: [agent-development, security]
---

# Agent Security

Agent security is the design of controls for systems where model outputs can affect tools, files, network calls, or data disclosure. The OWASP source card frames prompt injection, sensitive data exposure, tool abuse, and dependency risk as relevant concerns.

The same controls intersect with durable execution and interoperability. Per [[04-langgraph-durable-execution-2b964c83]], retries and resumable workflows need explicit side-effect handling. Per [[07-a2a-agent-interoperability-fc58e8a2]], cross-agent protocols introduce authentication, authorization, and trust boundaries.

## Core Controls

- [[Prompt Injection]] handling for untrusted content.
- [[Least Privilege]] for tools and runtime permissions.
- [[Tool Safety]] for model-controlled actions.
- Careful handling of secrets in [[Agent Tracing]] and logs.

## Related Sources

- [[08-owasp-llm-agent-security-9253bc51]]
- [[04-langgraph-durable-execution-2b964c83]]
- [[07-a2a-agent-interoperability-fc58e8a2]]
