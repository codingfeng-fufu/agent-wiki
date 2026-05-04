---
title: Agent Interoperability
type: concept
status: draft
sources: ["07-a2a-agent-interoperability-fc58e8a2"]
tags: [interoperability]
---

# Agent Interoperability

Agent interoperability is the ability of independently developed, deployed, or governed agents to collaborate meaningfully — exchanging tasks, state, or messages — while respecting autonomy, security boundaries, and semantic compatibility.

## Core Requirements

- Capability discovery and description
- Structured message formats (e.g., task requests, status updates, results)
- Authentication, authorization, and trust negotiation
- Error handling and fallback semantics across network or runtime failures

## Related Patterns & Protocols

- [[Agent2Agent Protocol]] provides one concrete specification.
- Contrasts with [[MCP Tools]] and [[MCP Resources]], which focus on model-context binding through an [[Agent Tool Interface]] and [[Context Boundary]] rather than agent-agent coordination.
- Underpins [[Multi-Agent Systems]] operating across organizational or infrastructural boundaries.

## Open Questions

- What distinguishes delegation to a remote agent from invocation of a local MCP Tool?
- How does interoperability impact [[Agent Runtime]] design — especially around [[Agent State Graph]] persistence and [[Durable Agent Execution]] guarantees?
