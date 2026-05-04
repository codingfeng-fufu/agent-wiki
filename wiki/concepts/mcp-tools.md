---
title: MCP Tools
type: concept
status: draft
sources: ["03-mcp-tools-resources-prompts-420d2910"]
tags: [mcp, tools]
---

# MCP Tools

MCP Tools expose discrete, invocable actions that a model or host can execute. They are distinct from resources and prompts in that they produce side effects or compute results.

Per [[03-mcp-tools-resources-prompts-420d2910]], tools operate within the host/client/server boundary, where permissioning and trust must be explicitly managed.

Tools are one part of the broader [[Agent Tool Interface]]: they expose invocable actions, while [[Context Boundary]] captures the trust and permissioning concerns around exposing those actions to a model-controlled workflow. This differs from [[Agent Interoperability]], which concerns agent-to-agent coordination rather than model-to-context binding.

## Related

- [[Model Context Protocol]]
- [[Agent Tool Interface]]
- [[Context Boundary]]
- [[Agent Interoperability]]
