---
title: AutoGen
type: concept
status: draft
sources: ["06-autogen-agent-and-multi-agent-applications-8cb555fe"]
tags: [autogen, microsoft]
---

# AutoGen

AutoGen is a Microsoft framework for building multi-agent applications using message-driven, role-based agents.

## Core Characteristics

- Agents are defined by their ability to send and receive messages.
- Multi-agent applications are structured as coordinated conversations or workflows.
- Roles (e.g., planner, executor, reviewer) are explicitly separated and composable.
- Runtime and orchestration are first-class concerns — distinct from model inference alone.

## Relationship to Other Concepts

- Contrasts with file-driven workflows like the LLM Wiki by prioritizing conversation state over filesystem state.
- Complements [[Multi-Agent Systems]] through concrete implementation patterns.
- Supports patterns such as [[Planner Executor Pattern]] and [[Fan Out Gather Pattern]] via role composition.
- Aligns with [[Coordinator Agent]] and [[Reviewer Agent]] as role instantiations.

## Open Questions

- How do AutoGen's message-passing semantics compare with [[Agent State Graph]] transitions?
- What mechanisms does AutoGen provide for [[Durable Agent Execution]] or [[Agent Checkpointing]]?
