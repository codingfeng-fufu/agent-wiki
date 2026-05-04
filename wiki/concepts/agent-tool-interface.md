---
title: Agent Tool Interface
type: concept
status: draft
sources: ["03-mcp-tools-resources-prompts-420d2910"]
tags: [agent-development, mcp, tools]
---

# Agent Tool Interface

An agent tool interface is the abstraction layer where a model, agent, or host interacts with external capabilities. It defines how capabilities are described, invoked, validated, and constrained before a model-controlled workflow can use them.

Per [[03-mcp-tools-resources-prompts-420d2910]], MCP separates external capabilities into [[MCP Tools]], [[MCP Resources]], and [[MCP Prompts]]. The tool interface is the broader contract around those capabilities: invocation semantics, schema validation, permission checks, error handling, and trust delegation.

## Responsibilities

- Describe capabilities in a way the model or host can select safely.
- Validate arguments and outputs before side effects occur.
- Enforce [[Least Privilege]] and runtime permission boundaries.
- Preserve tool-call evidence for [[Agent Tracing]] and [[Tool Call Logs]].
- Separate passive context access from action-oriented tool execution.

## Related Concepts

- [[MCP Tools]]
- [[MCP Resources]]
- [[MCP Prompts]]
- [[Context Boundary]]
- [[Protocol Boundary]]
- [[Tool Safety]]
