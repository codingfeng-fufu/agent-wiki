# Karpathy Pattern Compatibility

LLM Wiki implements the local Markdown workflow described in Andrej Karpathy's
[`llm-wiki.md`](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

The important idea is not a specific library. The pattern is to keep source
evidence separate from a maintained wiki, then let an LLM or coding agent keep
that wiki useful over time.

## Pattern Mapping

| Karpathy pattern | This project |
| --- | --- |
| Raw sources | `raw/` stores Markdown, text, and PDF evidence. |
| Wiki | `wiki/` stores maintained source, concept, and analysis pages. |
| Schema / rules | `system/`, `AGENTS.md`, templates, prompts, and health checks. |
| Ingest | `llmw source add`, `llmw ingest packet`, `llmw ingest record`, optional `llmw ingest run`. |
| Query | `llmw search`, `llmw query`, and MCP tools such as `llmw_search` and `llmw_query`. |
| Lint / review | `llmw health check`, `llmw health audit`, search benchmark, release checks. |
| Accumulation | Saved query pages, wiki log, rebuilt index, and source registry state. |

## Design Principles

- Raw evidence is not silently rewritten by the agent.
- Maintained wiki pages are normal Markdown files that can be reviewed in Git.
- Links use Obsidian-style `[[wiki links]]` where useful.
- Claims should keep source traceability through source pages, page metadata, or
  explicit citations.
- Search is local by default, with optional deep search when recall matters.
- Agent writes should be planned, previewed, and health-checked.

## What This Implementation Adds

The original pattern is intentionally lightweight. This repository adds the
tooling needed to use it with modern coding agents:

- MCP tools for context, search, query, planning, apply, maintenance, and health.
- CLI fallbacks for local users, CI, and runtimes without MCP support.
- A source registry and ingest packets so agents know what to maintain.
- Offline structural health checks and optional provider-backed semantic audits.
- Search benchmark and release/package gates for public project quality.
- A checked-in example wiki about agent development.

## Current Limits

This is not a hosted multi-user product. It is a local-first implementation for
agent developers who are comfortable with Markdown, Git, CLI tools, and MCP.

The first public version is also GitHub-clone-first. PyPI publishing is planned
as a later step after the open source packaging story is stable.
