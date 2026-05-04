---
title: Multi-Agent Systems
type: concept
status: draft
sources: ["05-google-adk-multi-agent-patterns-78ef6d88"]
tags: [multi-agent]
---

# Multi-Agent Systems

Multi-agent systems (MAS) are architectures in which multiple autonomous agents interact to solve tasks that are beyond the capability of any single agent.

## Coordination Patterns

Per [[05-google-adk-multi-agent-patterns-78ef6d88]], key coordination patterns include:

- [[Coordinator Agent]]-driven hierarchical decomposition
- Sequential Pipeline Pattern
- [[Fan Out Gather Pattern]]
- [[Reviewer Agent]]-mediated quality control
- [[Human in the Loop]] as an explicit coordination boundary

## Design Rationale

Separating roles — such as planner, executor, reviewer, and specialist — improves cohesion and maintainability compared to monolithic agents.
