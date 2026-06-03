# Launch Notes

Use this page when preparing the first public GitHub release or social post.

## One-Line Positioning

Local, source-backed Markdown memory for coding agents.

## Origin Statement

```text
LLM Wiki is my implementation of Andrej Karpathy's LLM Wiki pattern:
https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f

It turns the pattern into a local developer tool: raw sources stay immutable,
the agent maintains the wiki, and planned writes go through safe reviewable
flows. It is an independent project, not an official project from any referenced
agent runtime, protocol, model provider, or editor.
```

## GitHub Description

```text
Local, source-backed Markdown memory for coding agents.
```

## Useful Because

```text
This is useful when a coding agent keeps re-reading the same docs, design notes,
or research sources across sessions. LLM Wiki gives it maintained Markdown
memory: source pages, concept pages, links, provenance, search, safe plans,
dry-run apply, and health checks.
```

## Suggested Topics

```text
agents, mcp, markdown, wiki, knowledge-base, retrieval, local-first, codex, llm
```

## Short Announcement

```text
I built LLM Wiki: local, source-backed Markdown memory for coding agents.

Instead of searching raw docs from scratch on every question, an agent maintains
a source-backed Markdown wiki: summaries, concept pages, links, provenance,
safe plans, dry-run apply, and health checks.

It is my implementation of Karpathy's LLM Wiki pattern, adapted into a local
tool with CLI and MCP support.

Demo: scripts/demo.sh
```

## Longer Announcement

```text
LLM Wiki is a local-first knowledge layer for coding agents.

The idea is simple: raw sources are immutable evidence, but the agent maintains
a Markdown wiki in front of them. It can add source summaries, update concept
pages, connect Obsidian-style links, preserve provenance, and answer future
questions through MCP tools instead of rediscovering the same files every time.

The repo includes:

- MCP server for context, search, query, maintenance plans, and safe apply
- fast local search plus optional qmd deep search
- source registry and ingest packets
- health checks, search benchmarks, and release/package audits
- Codex integration helpers
- a runnable read-only demo: scripts/demo.sh
```

## Audience

```text
Useful for agent developers, MCP users, local-first Markdown/Obsidian users,
researchers, and teams that want source-backed project memory without a hosted
knowledge-base dependency.
```

## README Hook

```text
Before: your agent searches raw docs again and again.
After: your agent maintains a source-backed wiki and reuses it through MCP.
```

## Visual Asset

Use `assets/social-preview.png` as the GitHub social preview image.
