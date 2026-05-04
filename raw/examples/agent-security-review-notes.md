# Agent Security Review Notes

Date: 2026-05-04
Source type: synthetic review notes

## Review Scope

The review covers an agent-facing local wiki tool that exposes search, query,
maintenance planning, and safe apply operations through CLI and MCP interfaces.

## Observations

- Raw evidence should not be rewritten by agents.
- Generated wiki edits need provenance back to source documents.
- Tool calls that mutate files should be constrained to known safe actions.
- Dry-run previews help users inspect planned writes before applying them.
- Local runtime state may contain sensitive data and should not be packaged.

## Risks

- A raw source can contain prompt injection text that attempts to override agent
  instructions.
- Logs, traces, or saved answers may accidentally include sensitive data.
- A broad write primitive could let an agent modify files outside the intended
  wiki boundary.

## Suggested Controls

- Keep `raw/` read-only for agent workflows.
- Restrict automated writes to `wiki/` and approved project metadata.
- Audit package artifacts for `.env`, `.llmw/`, raw private data, and wiki
  content that should stay local.
- Run structural health checks before considering maintenance complete.
