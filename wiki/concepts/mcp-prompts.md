---
title: MCP Prompts
type: concept
status: draft
sources: ["03-mcp-tools-resources-prompts-420d2910"]
tags: [mcp, prompts]
---

# MCP Prompts

MCP Prompts represent reusable interaction templates — structured instructions, examples, or system message fragments — that guide model behavior. They are composable and versionable.

Per [[03-mcp-tools-resources-prompts-420d2910]], prompts decouple instruction logic from execution context, enabling portability across hosts and clients.

Prompts participate in the [[Agent Tool Interface]] as reusable instruction capabilities, and they cross the [[Context Boundary]] when a host exposes prompt templates or examples to a model session.

## Related

- [[Model Context Protocol]]
- [[Agent Tool Interface]]
- [[Context Boundary]]
