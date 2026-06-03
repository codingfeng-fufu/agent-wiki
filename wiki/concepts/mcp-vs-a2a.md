---
title: MCP vs A2A
type: concept
status: draft
sources: ["07-a2a-agent-interoperability-fc58e8a2"]
tags: [mcp, a2a, comparison]
---

# MCP vs A2A

MCP (Model Context Protocol) and A2A (Agent2Agent Protocol) address complementary but non-overlapping interoperability concerns:

This page is the comparison entry for questions like "compare Model Context Protocol with Agent2Agent interoperability" or "difference between MCP tools and agent-to-agent protocol."

| Dimension | MCP | A2A |
|-----------|-----|-----|
| **Scope** | Model ↔ external context (tools, resources, prompts) | Agent ↔ peer agent |
| **Primary Abstraction** | Capabilities exposed as functions or data endpoints | Capabilities exposed as discoverable, delegable agents |
| **Trust Model** | Host-managed, typically same-process or same-org | Cross-domain, requiring explicit negotiation and delegation semantics |
| **Use Case Focus** | Enhancing model reasoning with external context | Enabling multi-agent collaboration across runtimes or organizations |

## Relationship to Existing Concepts

- MCP underpins [[MCP Tools]], [[MCP Resources]], and [[MCP Prompts]].
- A2A enables [[Coordinator Agent]] and [[Reviewer Agent]] roles to operate across infrastructure boundaries.
- Neither replaces [[Message Driven Agents]], but both rely on message-based interaction.

## Conflict Note

No existing wiki content contradicts this distinction; current [[MCP Tools]] and [[Agent Runtime]] pages assume intra-system integration and do not yet address cross-agent delegation semantics.
