---
title: Google ADK Multi-Agent Systems
source_url: https://google.github.io/adk-docs/agents/multi-agents/
source_type: official_doc_source_card
topic: multi-agent architecture patterns
tags: [agent-development, google-adk, multi-agent, architecture]
---

# Google ADK Multi-Agent Systems

This source card points to the Google Agent Development Kit documentation on multi-agent systems.

## Why This Matters

Multi-agent systems require explicit coordination patterns. A single agent can become too broad; separating planner, executor, reviewer, and specialist roles can improve cohesion.

## Key Ideas To Extract

- Coordinator and hierarchical decomposition patterns.
- Sequential pipeline and parallel fan-out/gather patterns.
- Reviewer or critique agents for quality control.
- Human-in-the-loop as a coordination boundary.

## Wiki Pages This Should Inform

- [[Multi-Agent Systems]]
- [[Coordinator Agent]]
- [[Planner Executor Pattern]]
- [[Reviewer Agent]]
- [[Fan Out Gather Pattern]]

## Questions For Ingest

- Which parts of LLM Wiki should remain a single workflow versus multiple agents?
- Should ingestion have separate reader, writer, linker, and reviewer roles?
- What pattern best fits source ingestion and wiki health repair?

