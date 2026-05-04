---
title: Least Privilege
type: concept
status: draft
sources: ["08-owasp-llm-agent-security-9253bc51"]
tags: [security, permissions]
---

# Least Privilege

Least privilege means granting an agent or tool only the permissions needed for the current task. The OWASP source card lists it as a relevant security concept for agentic risk.

## Wiki Implications

- Separate read-only evidence access from write-capable wiki editing.
- Prefer narrow tool scopes for source registration, ingestion, and health checks.
- Combine with [[Tool Safety]] and [[Agent Security]] for file-writing workflows.

## Related Sources

- [[08-owasp-llm-agent-security-9253bc51]]
