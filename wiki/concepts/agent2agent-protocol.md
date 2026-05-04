---
title: Agent2Agent Protocol
type: concept
status: draft
sources: ["07-a2a-agent-interoperability-fc58e8a2"]
tags: [interoperability, protocol]
---

# Agent2Agent Protocol

The Agent2Agent (A2A) Protocol is a specification for enabling structured, secure, and discoverable communication between autonomous agents across runtime boundaries, organizations, or frameworks.

It defines message schemas, capability discovery mechanisms, delegation semantics, and trust negotiation patterns — distinct from tool- or context-exposure protocols like [[MCP Tools]] or [[MCP Resources]].

## Relationship to Other Concepts

- Contrasts with [[MCP vs A2A]]: A2A governs *agent-to-agent* coordination; MCP governs *model-to-context/tool* integration.
- Enables [[Multi-Agent Orchestration]] across heterogeneous environments.
- Requires explicit handling of [[Protocol Boundary]] concerns: auth, identity, message integrity, and capability negotiation.
- Supports patterns such as [[Fan Out Gather Pattern]] and [[Planner Executor Pattern]] when spanning agent deployments.

## Open Questions

- Would LLM Wiki ever need to expose itself as an agent, not just a tool?
- What is the difference between delegating to another agent and calling a local tool?
- How should protocol trust affect file-writing permissions?
