---
title: Human in the Loop
type: concept
status: draft
sources: ["04-langgraph-durable-execution-2b964c83"]
tags: [agent-development, human-in-the-loop]
---

# Human in the Loop

Human-in-the-loop (HITL) refers to agent workflows that intentionally pause execution to await human input, review, or approval before proceeding.

## Design Considerations

- Requires explicit interrupt and resume semantics
- Depends on [[Agent Checkpointing]] for state preservation across pauses
- Often integrated with [[Durable Agent Execution]] to handle timeouts or manual overrides

## Related Sources

- [[04-langgraph-durable-execution-2b964c83]]
