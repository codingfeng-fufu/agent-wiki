---
title: Message Driven Agents
type: concept
status: draft
sources: ["06-autogen-agent-and-multi-agent-applications-8cb555fe"]
tags: [messaging, runtime]
---

# Message Driven Agents

Message-driven agents interact primarily through asynchronous or synchronous message passing rather than direct function calls or shared memory.

## Key Properties

- Each agent encapsulates behavior and state, exposing only a message interface.
- Communication is explicit, auditable, and often serializable — enabling replay, tracing, and debugging.
- Enables loose coupling and dynamic topology changes in [[Multi-Agent Systems]].

## Relation to Other Concepts

- Underpins [[AutoGen]]'s agent model.
- Contrasts with [[MCP Tools]] and [[MCP Resources]], which rely on protocol-defined capability invocation rather than peer-to-peer messaging.
- Differs from [[MCP vs A2A]]: MCP binds models to context, [[Agent2Agent Protocol]] binds agents to peer agents, while message-driven agents describe the communication style used inside or across those systems.
- Supports [[Human in the Loop]] by allowing human-injected messages into the flow.
- May require [[Idempotent Tool Calls]] when messages trigger side effects.
