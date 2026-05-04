---
title: Output Guardrails
type: concept
status: draft
sources: ["01-openai-agents-guardrails-87ce73bd"]
tags: [agent-development, guardrails, validation]
---

# Output Guardrails

Output guardrails validate an agent result before it is returned, stored, or passed to a tool. The guardrails source card highlights malformed outputs, policy violations, and unsafe downstream effects as concerns.

## Uses

- Check that generated wiki pages contain required frontmatter.
- Reject malformed structured output before file writes.
- Pair with [[Agent Regression Testing]] to detect recurring quality issues.

## Related Sources

- [[01-openai-agents-guardrails-87ce73bd]]
