---
title: Fan Out Gather Pattern
type: concept
status: draft
sources: ["05-google-adk-multi-agent-patterns-78ef6d88"]
tags: [multi-agent, parallelism]
---

# Fan Out Gather Pattern

A concurrency pattern in multi-agent systems where a coordinator agent distributes independent subtasks to multiple agents in parallel (fan out), then collects and synthesizes their responses (gather).

## Characteristics

- Requires idempotent or isolated subtasks to avoid race conditions
- Benefits from [[Durable Agent Execution]] for fault tolerance
- Often paired with [[Reviewer Agent]] for post-aggregation validation

## Source Attribution

Described in [[05-google-adk-multi-agent-patterns-78ef6d88]] as a core architectural pattern for scalable agent collaboration.
