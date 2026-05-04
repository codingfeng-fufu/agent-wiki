# Publishing Checklist

Use this checklist before turning a local LLM Wiki workspace into a public GitHub
repository.

## Repository Identity

- Choose the final GitHub owner and repository name.
- Update `pyproject.toml` project URLs after the repository exists.
- Keep the project origin clear: it is my implementation of Andrej Karpathy's
  LLM Wiki idea, not an official project from any referenced runtime, protocol,
  provider, or editor.
- Add repository topics such as `agents`, `mcp`, `markdown`, `wiki`,
  `retrieval`, `knowledge-base`, `local-first`, `codex`, and `llm`.
- Add a concise GitHub description: `Agent-facing local Markdown wiki with MCP
  tools for source-backed long-term memory.`

## Sensitive Data Review

Treat these paths as potentially private:

- `raw/`
- `wiki/`
- `.llmw/`
- logs and traces
- generated outputs
- provider configuration

Do not publish real API keys, `.env` files, local qmd databases, private source
documents, private maintained wiki pages, sessions, plans, or local caches.

The checked-in `raw/examples/` files are intentionally public synthetic examples.
Keep any real private evidence outside public commits.

## Project Quality

Run:

```bash
.venv/bin/pytest -q
.venv/bin/llmw health check --json
.venv/bin/llmw benchmark search --provider python --top-k 5 --json
.venv/bin/llmw release check --json
.venv/bin/llmw package build --json
```

For MCP confidence:

```bash
.venv/bin/llmw integration codex test --json
```

## GitHub Presentation

- Keep the README short enough for a newcomer to understand the value quickly.
- Put deeper concept material in `docs/`.
- Show the MCP-first agent workflow clearly.
- Make the use cases concrete: long-running agent projects, research notes,
  team memory, and Obsidian/Markdown workflows.
- Include safety boundaries for local data.
- Keep issue templates and contribution guidance small and practical.
- Use `assets/social-preview.svg` as the source artwork for the GitHub social
  preview. Export it to PNG if the hosting surface requires a raster image.
- Record `scripts/demo.sh` with `scripts/record_demo.sh` as a short terminal GIF
  or asciinema cast after the first public release.
- Reuse [launch notes](launch.md) for the first public post.
- Keep [ROADMAP.md](../ROADMAP.md) current enough that visitors can see where the
  project is going.

## Release Artifacts

Before publishing to PyPI or attaching build artifacts to a GitHub release, check
that the package does not include local knowledge-base data:

```bash
.venv/bin/llmw release check --sdist --json
```
