---
title: "07 a2a agent interoperability"
type: source
status: draft
sources: ["07-a2a-agent-interoperability-fc58e8a2"]
tags: []
---

# Agent2Agent Protocol

This source card points to the Agent2Agent protocol documentation. It is useful for a wiki section on cross-agent interoperability and protocol boundaries.

## Why This Matters

As agent systems mature, agents may need to discover each other, delegate tasks, exchange structured messages, and interoperate across organizations or runtimes.

## Key Ideas To Extract

- How agents expose capabilities to other agents.
- What task or message abstractions are used for interoperability.
- Where authentication, authorization, and trust boundaries appear.
- How A2A differs from MCP: agent-to-agent coordination versus tool/context exposure.

## Wiki Pages This Should Inform

- [[Agent2Agent Protocol]]
- [[Agent Interoperability]]
- [[Protocol Boundary]]
- [[MCP vs A2A]]

## Questions For Ingest

- Would LLM Wiki ever need to expose itself as an agent, not just a tool?
- What is the difference between delegating to another agent and calling a local tool?
- How should protocol trust affect file-writing permissions?
