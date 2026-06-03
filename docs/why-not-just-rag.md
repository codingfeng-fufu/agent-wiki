# Why Not Just RAG?

RAG is useful when a model needs to retrieve raw evidence at question time. LLM
Wiki is useful when the same body of knowledge must improve across many
sessions.

## Query-Time RAG

A typical RAG flow looks like this:

```text
question -> retrieve raw chunks -> synthesize answer
```

That works well for one-off lookup. The tradeoff is that each new question asks
the model to rediscover structure from raw documents again. Cross-links,
comparisons, decisions, contradictions, and useful answers often disappear back
into chat history.

## LLM Wiki

LLM Wiki uses a compile-first flow:

```text
raw sources -> maintained wiki -> search/query/agent tools
```

The agent turns evidence into durable Markdown pages: source cards, concept
pages, comparisons, analysis notes, and links. Future questions search the
maintained wiki first, not only the original raw documents.

## Why It Helps

- Knowledge compounds across sessions.
- The wiki is inspectable, editable, and versionable in Git.
- Source material stays separate from agent-written synthesis.
- Related ideas can be linked once and reused many times.
- Saved answers can become new wiki pages instead of transient chat output.
- Health checks can detect broken links, stale indexes, and maintenance gaps.

## When RAG Is Enough

Plain RAG may be the better fit when:

- the user needs one answer from a small document set
- there is no long-running project memory to maintain
- source material changes constantly and no one wants a curated synthesis layer
- the output does not need to be reviewed as Markdown

## Practical Rule

Use RAG for quick retrieval. Use LLM Wiki when the agent keeps returning to the
same project, research topic, or domain context and the work should get better
over time.
