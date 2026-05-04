# Project Philosophy

LLM Wiki is based on a simple bet: agents should maintain knowledge, not just
retrieve it.

The project is an implementation of Andrej Karpathy's LLM Wiki idea: use an LLM
agent as the maintainer of a Markdown wiki, while raw sources remain immutable
evidence. The tooling in this repository is my implementation of that pattern,
not an official project from any referenced agent runtime, protocol, model
provider, or editor.

In many LLM document workflows, raw files are searched at answer time. The model
finds relevant chunks, writes a response, and the structure created during that
answer disappears into chat history. The next similar question starts over.

LLM Wiki keeps that structure. Raw sources remain immutable evidence. The wiki
is the maintained intermediate layer where an agent writes summaries, entities,
concepts, comparisons, contradictions, and saved analyses. Future questions use
that maintained layer first.

## The Three Layers

1. `raw/`: source material, treated as read-only evidence.
2. `wiki/`: Markdown pages maintained by the agent.
3. Agent instructions and tools: `AGENTS.md`, MCP tools, health checks, and
   safe plan/apply workflows.

This makes the knowledge base cumulative. New sources can update old claims.
Useful answers can become pages. Links can be maintained. Contradictions can be
recorded instead of rediscovered.

## Human And Agent Roles

Humans should choose sources, judge relevance, ask better questions, and decide
what matters. Agents should handle the repetitive maintenance work: indexing,
summarizing, linking, recording provenance, and keeping pages consistent.

Obsidian is a good companion because it makes the wiki visible. The agent writes
and maintains the Markdown. The human browses the graph, follows links, and
guides the direction.

## Where This Fits

The pattern works for:

- research projects
- personal knowledge systems
- book or course notes
- competitive analysis
- due diligence
- team memory
- long-running agent projects

The important requirement is that knowledge should accumulate over time.
