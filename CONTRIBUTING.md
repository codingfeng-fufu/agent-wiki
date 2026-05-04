# Contributing

LLM Wiki is an agent-facing local Markdown wiki toolkit. Contributions should preserve the core contract: raw sources are read-only evidence, maintained wiki pages are source-backed, and agent write operations go through explicit plan/apply flows.

## Development Setup

```bash
uv sync --extra dev
uv sync --extra dev --extra search  # optional qmd search integration
```

Run the main checks before opening a pull request:

```bash
.venv/bin/pytest -q
.venv/bin/llmw health check --json
.venv/bin/llmw benchmark search --provider python --top-k 5 --json
```

For release-oriented checks:

```bash
scripts/release_check.sh
```

## Contribution Guidelines

- Keep raw source files immutable. Do not rewrite content under `raw/`.
- Prefer MCP tools and documented `llmw` primitives over arbitrary shell workflows in agent-facing changes.
- Add focused tests for CLI contracts, MCP contracts, search behavior, and write safety when changing those areas.
- Keep packaging clean: do not include `.llmw/`, real `.env` files, local qmd databases, sessions, plans, or private knowledge-base content in release artifacts.
- Do not commit secrets, real API keys, local credentials, or private user data.

## Search Changes

Search changes should run:

```bash
.venv/bin/llmw benchmark search --provider python --top-k 5 --json
```

If you change deep qmd behavior, also run the relevant daemon/MCP tests and, when qmd is available:

```bash
RUN_DEEP_SEARCH_BENCHMARK=1 scripts/release_check.sh
```
