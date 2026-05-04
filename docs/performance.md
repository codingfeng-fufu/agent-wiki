# Performance Notes

LLM Wiki has two retrieval paths: fast local search and optional deep search.

## Fast Search

Default `llmw search` and `llmw query` use local text retrieval. This path is the
right default for agent loops because it avoids qmd model and vector-index
cold-starts.

```bash
.venv/bin/llmw search "guardrails" --json
```

The JSON response includes a `strategy` field. Use it to decide whether a query
needs deep search.

## Deep Search

Deep search uses qmd when available:

```bash
.venv/bin/llmw search "guardrails" --deep --json
```

For repeated high-recall search, keep the backend warm:

```bash
.venv/bin/llmw search-daemon start --deep
.venv/bin/llmw search-daemon status --json
.venv/bin/llmw search-daemon query "guardrails" --json
```

MCP deep search reuses the daemon when it is running. If no daemon is available,
it falls back to a bounded subprocess and returns a fast fallback on timeout.

## Useful Environment Variables

- `LLMW_DISABLE_QMD=1`: force-disable qmd integration.
- `LLMW_QMD_TIMEOUT_SECONDS=30`: adjust qmd CLI timeout.
- `LLMW_QMD_BACKEND=cli`: force qmd CLI instead of the Python SDK path.
- `LLMW_QMD_RERANK=1`: enable experimental qmd reranking.
- `LLMW_MCP_DEEP_TIMEOUT_SECONDS=35`: adjust MCP deep-search timeout.

## Benchmark

```bash
.venv/bin/llmw benchmark search --provider python --top-k 5 --json
.venv/bin/llmw benchmark search --provider llmw --top-k 5 --json
```

The bundled search benchmark uses fixed queries. Because many queries have only
one relevant page while precision is measured at 5, `Precision@5` has a low
ceiling. Watch `Recall@5`, `HitRate@5`, and `MRR@5` as the main regression
signals.
