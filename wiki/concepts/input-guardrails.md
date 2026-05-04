---
title: Input Guardrails
type: concept
status: draft
sources: ["01-openai-agents-guardrails-87ce73bd"]
tags: [agent-development, guardrails, safety]
---

# Input Guardrails

Input guardrails validate or classify user input, source content, or workflow state before an agent proceeds. The guardrails source card distinguishes them from [[Output Guardrails]] as a separate point in the agent lifecycle.

## Uses

- Detect unsafe or irrelevant requests before model execution.
- Separate evidence content from instructions embedded in raw sources.
- Decide whether a request needs [[Human in the Loop]] review.

## Related Sources

- [[01-openai-agents-guardrails-87ce73bd]]
