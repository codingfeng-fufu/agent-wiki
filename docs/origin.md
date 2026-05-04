# Origin

LLM Wiki is an implementation of Andrej Karpathy's "LLM Wiki" idea:
[`llm-wiki.md`](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

Karpathy's gist describes the core pattern: keep raw sources immutable, let an
LLM incrementally build a persistent Markdown wiki in front of them, and use
that wiki as the maintained knowledge layer instead of re-deriving everything on
every query. This repository turns that pattern into a local developer tool:

- `raw/` stores read-only source evidence.
- `wiki/` stores maintained Markdown pages.
- `llmw` provides CLI and MCP interfaces for agents.
- planned writes go through constrained plan/apply flows.
- health, benchmark, release, and package checks make the workflow repeatable.

## What It Is Not

LLM Wiki is not an official project from OpenAI, Anthropic, the Model Context
Protocol project, qmd, Obsidian, or any other referenced tool or framework. It
is an independent local-first implementation of Karpathy's idea that can
integrate with agent runtimes and OpenAI-compatible model providers.

LLM Wiki is also not a fork of another repository. It is a standalone
implementation of the agent-maintained Markdown wiki workflow.

## Related Implementations

The public ecosystem already has related work. A few examples:

- [`Pratiyush/llm-wiki`](https://github.com/Pratiyush/llm-wiki)
- [`Ss1024sS/LLM-wiki`](https://github.com/Ss1024sS/LLM-wiki)
- [`balukosuri/llm-wiki-karpathy`](https://github.com/balukosuri/llm-wiki-karpathy)

These projects help show that the pattern is useful in practice. This repository
is another implementation of the idea, with its own CLI, MCP surface, release
gates, and example wiki.

## What This Implementation Adds

This repository focuses on making the idea useful to coding agents and
maintainable as an open source tool:

- MCP-first interface for agent runtimes.
- CLI fallback for local users, CI, and runtimes without MCP.
- `context -> search -> query -> plan -> apply` as a concrete agent loop.
- Safe plan/apply workflow with dry-run previews and whitelisted actions.
- Fast local search by default, optional qmd deep search, and daemon reuse.
- Offline health checks, retrieval benchmarks, release checks, and package audits.
- Codex integration helpers and a local plugin template.
- A working example wiki about agent development.

## Why The Example Wiki Is Here

The checked-in example wiki focuses on agent development topics because that is
a useful test domain for this tool itself: guardrails, tracing, MCP, durable
execution, multi-agent patterns, interoperability, and agent security all benefit
from cumulative source-backed notes.

The example content is included to show the shape of a maintained wiki. Users
should review `raw/`, `wiki/`, and `.llmw/` carefully before publishing their own
knowledge-base repositories.
