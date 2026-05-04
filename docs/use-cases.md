# Use Cases

LLM Wiki is useful when a coding agent repeatedly needs the same project,
research, or domain context and that context should improve over time.

## Long-Running Agent Projects

Use LLM Wiki as the project memory layer for an agent that works across many
sessions.

Useful when:

- the agent keeps re-reading the same design notes, issue threads, or docs
- decisions need to be recorded with source links
- project context should survive chat history loss
- future agents need a fast way to understand prior work

Example workflow:

```bash
llmw_context
llmw_search query="release safety"
llmw_plan goal="update the release notes from current wiki evidence"
llmw_apply dry_run=true
```

## Research And Reading

Use LLM Wiki to turn articles, papers, documentation pages, or reports into a
maintained Markdown knowledge base.

Useful when:

- you are reading a topic over weeks, not minutes
- new sources should update old summaries
- contradictions and changed claims matter
- saved answers should become reusable notes

The agent maintains source pages, concept pages, comparison pages, and analysis
pages while raw sources stay immutable.

## Agent Development Knowledge Base

This repository includes a working example wiki about agent development:

- guardrails
- tracing and observability
- MCP tools, resources, and prompts
- durable execution
- multi-agent orchestration
- interoperability
- security risks

Start with the [example index](../examples/README.md), then try:

```bash
scripts/demo.sh
llmw search "prompt injection tool safety" --json
llmw query "how should agents reduce prompt injection risk?"
```

Public raw examples are available under [`raw/examples/`](../raw/examples/README.md).
They are synthetic source documents that show the evidence shape without adding
private data to the repository.
Chinese samples are available under [`raw/examples/zh-CN/`](../raw/examples/zh-CN/README.md).

## Team Or Project Memory

Use LLM Wiki as a local-first memory layer for meeting notes, design documents,
incident notes, customer calls, or planning documents.

Useful when:

- context is sensitive and should stay local
- the team wants Markdown files rather than a hosted database
- agents should propose edits, not silently mutate source material
- maintainers want health checks and release-style gates around generated notes

## Obsidian Companion

Use Obsidian to browse the graph while the agent maintains the wiki.

The common division of labor is:

- human: choose sources, inspect pages, follow links, judge priorities
- agent: summarize, cross-link, maintain index/log, record source-backed claims
- tooling: search, MCP access, plan/apply, health checks, package audits

## When Not To Use It

LLM Wiki is probably not the right fit if:

- you only need a one-off answer from a small file
- you do not want Markdown files on disk
- you need a hosted multi-user product today
- you want agents to edit raw source evidence directly
- you do not need knowledge to accumulate across sessions
