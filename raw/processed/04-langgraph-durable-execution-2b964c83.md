---
title: LangGraph Durable Execution
source_url:
  - https://docs.langchain.com/oss/python/langgraph/durable-execution
  - https://docs.langchain.com/oss/python/langgraph/persistence
  - https://docs.langchain.com/oss/python/langgraph/human-in-the-loop
source_type: official_doc_source_card
topic: long-running and recoverable agents
tags: [agent-development, langgraph, durable-execution, persistence, human-in-the-loop]
---

# LangGraph Durable Execution

This source card points to LangGraph documentation on durable execution, persistence, and human-in-the-loop workflows.

## Why This Matters

Useful agents often run longer than a single model call. They need checkpointing, resumability, interrupt points, human review, and careful handling of side effects.

## Key Ideas To Extract

- Durable execution depends on checkpoints and persisted state.
- Human-in-the-loop workflows need explicit interrupt and resume semantics.
- Side-effectful operations should be designed carefully so retries do not corrupt state.
- Long-running agents benefit from explicit state graphs instead of opaque loops.

## Wiki Pages This Should Inform

- [[Durable Agent Execution]]
- [[Agent Checkpointing]]
- [[Human in the Loop]]
- [[Idempotent Tool Calls]]
- [[Agent State Graph]]

## Questions For Ingest

- What state should `llmw ingest run` persist before and after a provider call?
- How should the system resume if a model call succeeds but file writing fails?
- Which side effects need idempotency guarantees?

