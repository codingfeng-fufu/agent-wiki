# Agent Memory Design Note

Date: 2026-05-04
Source type: synthetic design note

## Context

A coding agent working on a long-running repository repeatedly needs the same
background: project goals, prior decisions, safety constraints, release process,
and known performance bottlenecks. If that context only lives in chat history,
each new session spends time rediscovering it.

## Proposal

Use a local Markdown wiki as the maintained memory layer. Raw documents stay
immutable. The agent creates and updates wiki pages that summarize sources,
connect related concepts, and preserve provenance.

## Requirements

- The agent must search maintained wiki pages before making claims.
- Raw sources must be treated as evidence, not editable working documents.
- Important answers should be saved as wiki pages when they will be reused.
- Writes should be planned and previewed before mutation.
- The project should expose machine-readable context for agent runtimes.

## Open Questions

- Which pages should be considered public examples?
- How should private raw sources be excluded from release artifacts?
- When should deep retrieval be used instead of fast local search?
