---
title: Context Boundary
type: concept
status: draft
sources:
  - "03-mcp-tools-resources-prompts-420d2910"
  - "08-owasp-llm-agent-security-9253bc51"
tags: [agent-development, context, security]
---

# Context Boundary

A context boundary is the trust and permission boundary between a model or host and the external context it can access. It determines what data is exposed, what actions are permitted, and how capabilities are discovered, mediated, and validated.

Per [[03-mcp-tools-resources-prompts-420d2910]], MCP tools, resources, and prompts sit behind a host/client/server boundary where permissioning and trust must be explicit. Per [[08-owasp-llm-agent-security-9253bc51]], agent systems need this boundary because untrusted context can influence model-controlled actions and data disclosure.

## Boundary Questions

- Which [[MCP Resources]] are safe to expose as context?
- Which [[MCP Tools]] can produce side effects, and who authorizes them?
- Which prompt or resource content is untrusted and needs [[Prompt Injection]] controls?
- How should [[Least Privilege]] apply to tool access, file writes, network calls, and traces?

## Related Concepts

- [[Agent Tool Interface]]
- [[MCP Tools]]
- [[MCP Resources]]
- [[Agent Security]]
- [[Protocol Boundary]]
- [[Tool Safety]]
