---
title: Idempotent Tool Calls
type: concept
status: draft
sources: ["04-langgraph-durable-execution-2b964c83"]
tags: [agent-development, durability, side-effects]
---

# Idempotent Tool Calls

Idempotent tool calls are operations that produce the same observable result when invoked multiple times with the same inputs — critical for safe retries in [[Durable Agent Execution]].

## Why It Matters

- Prevents corruption from duplicate side effects (e.g., double payments, duplicated file writes)
- Enables robust recovery after partial failures (e.g., model succeeds but write fails)
- Supports [[Agent Checkpointing]] and [[Human in the Loop]] resumption logic

## Related Sources

- [[04-langgraph-durable-execution-2b964c83]]
