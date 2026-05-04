---
title: Reviewer Agent
type: concept
status: draft
sources: ["05-google-adk-multi-agent-patterns-78ef6d88"]
tags: [multi-agent, quality-control]
---

# Reviewer Agent

A reviewer agent is a specialized agent that critiques outputs, validates correctness, checks safety or coherence, and optionally triggers revision or escalation.

## Function

Per [[05-google-adk-multi-agent-patterns-78ef6d88]], reviewer agents serve as quality control gates — especially useful before final output delivery or human handoff.

## Integration Points

- Paired with [[Planner Executor Pattern]] for iterative refinement
- May enforce [[Human in the Loop]] boundaries when confidence falls below threshold
