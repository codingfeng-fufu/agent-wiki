---
title: Coordinator Agent
type: concept
status: draft
sources: ["05-google-adk-multi-agent-patterns-78ef6d88"]
tags: [multi-agent, coordination]
---

# Coordinator Agent

A coordinator agent is a role-based agent responsible for orchestrating interactions among other agents, typically by delegating subtasks, aggregating results, and enforcing execution order or policy.

## Role in Hierarchical Decomposition

As described in [[05-google-adk-multi-agent-patterns-78ef6d88]], coordinators enable hierarchical decomposition — breaking high-level goals into subgoals assigned to specialized agents.

## Relationship to Other Patterns

- Coordinates [[Planner Executor Pattern]] workflows
- May initiate [[Fan Out Gather Pattern]]
- Often interfaces with [[Human in the Loop]] for approval boundaries
