# Retrieval Maintenance Notes

Date: 2026-05-04
Source type: synthetic maintenance notes

## Problem

Fast retrieval is important for agent loops. If every query rebuilds an index,
loads a heavy model, or spawns a slow external process, agents become reluctant
to search before acting.

## Desired Behavior

- Default search should be fast enough for frequent calls.
- Deep search should be available when recall matters more than latency.
- Repeated deep retrieval should reuse a warm backend.
- Search results should explain whether deep search is recommended.

## Maintenance Signals

Track:

- search latency for common queries
- benchmark recall and hit rate
- stale index warnings
- whether daemon-backed deep search is available
- whether release checks still pass after search changes

## Example Query

```text
prompt injection tool safety
```

This query should surface pages about prompt injection, tool safety, agent
guardrails, and source cards that explain the underlying evidence.
