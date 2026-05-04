---
title: Planner Executor Pattern
type: concept
status: draft
sources: ["05-google-adk-multi-agent-patterns-78ef6d88"]
tags: [multi-agent, planning]
---

# Planner Executor Pattern

A multi-agent pattern where one agent (the planner) generates a sequence or structure of actions, and another (the executor) carries them out — often with feedback loops for refinement.

## Origin & Use Case

Cited in [[05-google-adk-multi-agent-patterns-78ef6d88]] as a way to separate reasoning from action, improving modularity and auditability.

## Variants

- One-shot plan → execute
- Iterative plan → execute → critique → revise (involving [[Reviewer Agent]])
- Plan delegation to domain-specialist executors
