---
title: Model Context Protocol Concepts
source_url:
  - https://modelcontextprotocol.io/docs/concepts/tools
  - https://modelcontextprotocol.io/docs/concepts/resources
  - https://modelcontextprotocol.io/docs/concepts/prompts
source_type: official_doc_source_card
topic: tool and context protocol
tags: [agent-development, mcp, tools, resources, prompts]
---

# Model Context Protocol Concepts

This source card points to the MCP concepts documentation for tools, resources, and prompts. It is useful for comparing local CLI tools with protocol-native agent capabilities.

## Why This Matters

MCP separates capabilities into different concepts: tools for actions, resources for contextual data, and prompts for reusable interaction templates. This separation maps well to high-cohesion, low-coupling agent architecture.

## Key Ideas To Extract

- Tools expose actions that a model or host can invoke.
- Resources expose contextual data without necessarily performing actions.
- Prompts expose reusable workflows or instructions.
- The host/client/server boundary affects permissioning and trust.

## Wiki Pages This Should Inform

- [[Model Context Protocol]]
- [[MCP Tools]]
- [[MCP Resources]]
- [[MCP Prompts]]
- [[Agent Tool Interface]]
- [[Context Boundary]]

## Questions For Ingest

- Should `llmw` eventually expose search, source registry, and health checks through MCP?
- Which current `llmw` commands are tools, and which files are resources?
- How should prompts in `system/prompts/` map to MCP prompt concepts?

