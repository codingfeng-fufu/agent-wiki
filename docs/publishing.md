# Publishing Checklist

Use this checklist before turning a local LLM Wiki workspace into a public
GitHub repository.

The first public version is GitHub-clone-first. PyPI publishing is intentionally
reserved for a later release after the public repository, docs, demo, and CI
have stabilized.

## Repository Identity

- Use `agent-wiki` as the public repository name under `codingfeng-fufu`.
- Keep GitHub links pointed at `https://github.com/codingfeng-fufu/agent-wiki`.
- Keep the package name `llm-wiki` and CLI command `llmw`.
- Keep the project origin clear: this is an independent implementation of
  Andrej Karpathy's LLM Wiki idea, not an official project from any referenced
  runtime, protocol, provider, or editor.
- Add repository topics such as `agents`, `mcp`, `markdown`, `wiki`,
  `retrieval`, `knowledge-base`, `local-first`, `codex`, and `llm`.
- Use this GitHub description:

```text
Local, source-backed Markdown memory for coding agents.
```

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

The checked-in `raw/examples/` files are intentionally public synthetic
examples. Keep any real private evidence outside public commits.

## GitHub Presentation

- Keep README focused on the Karpathy LLM Wiki pattern and a 10-minute local
  success path.
- Use `git clone` + `uv sync --extra dev` as the primary install route.
- Do not present PyPI, pip, or pipx installation as the current default.
- Link deeper concept material from `docs/`, especially
  [Karpathy Pattern Compatibility](karpathy-pattern.md) and
  [Why Not Just RAG?](why-not-just-rag.md).
- Show the MCP-first agent workflow clearly.
- Keep issue templates and contribution guidance small and practical.
- Use `assets/social-preview.png` as the GitHub social preview image.
- Reuse [Launch notes](launch.md) for the first public post.

## Reports And Proof Assets

Keep reports as supporting proof, not as the main user path.

- README should link only a small number of proof materials, if any.
- `reports/` can remain for historical validation artifacts.
- Do not require users to read reports before they can run the demo.
- If the repository becomes too heavy, move old report screenshots to release
  assets instead of keeping every recording in the main branch.

## Project Quality

Run:

```bash
uv run --extra dev pytest -q
uv run llmw health check --root . --json
uv run llmw benchmark search --root . --provider python --top-k 5 --json
uv run llmw release check --root . --sdist --no-codex --no-strict --json
uv run llmw package build --root . --no-strict --json
```

The public-alpha release gate should pass with tests, structural health, search
benchmark, and source distribution audit all green. A missing provider key is
acceptable for GitHub alpha because search, context, health checks, planning,
and the demo do not require an LLM provider.

For MCP confidence:

```bash
uv run llmw integration codex test --root . --json
```

## GitHub Release Artifacts

The current release workflow builds local artifacts and uploads `dist/` as a
GitHub Actions artifact. Before attaching artifacts to a GitHub release, check
that the package does not include local knowledge-base data:

```bash
uv run llmw release check --root . --sdist --no-codex --no-strict --json
```

## Public Alpha Release Steps

1. Confirm the repository metadata:
   - description: `Local, source-backed Markdown memory for coding agents.`
   - topics: `agents`, `mcp`, `markdown`, `wiki`, `retrieval`,
     `knowledge-base`, `local-first`, `codex`, `llm`
   - social preview: `assets/social-preview.png`
2. Run the quality commands above from a clean checkout.
3. Run `scripts/demo.sh` and confirm it only writes ignored local plan state.
4. Review `raw/`, `wiki/`, `.llmw/`, logs, reports, and generated outputs for
   secrets or private source material.
5. Create the `v0.1.0` tag after the release workflow is green.
6. Use `CHANGELOG.md` and [Launch notes](launch.md) as the source for the
   GitHub release description.

## Troubleshooting

- If `uv sync --extra dev` fails, confirm Python 3.11+ is installed and retry
  from the repository root.
- If `llmw doctor` warns about `DASHSCOPE_API_KEY`, ignore it for local search
  and demo flows; set the key only for LLM-backed query, ingest, or audit.
- If deep search is skipped, install optional qmd support with
  `uv sync --extra dev --extra search`.
- If Codex MCP probing fails, first verify `uv run llmw mcp --root .` starts
  and then run `uv run llmw integration codex test --root . --json`.

## PyPI Reserved Step

When the project is ready for PyPI:

- Add a publish job to `.github/workflows/release.yml`.
- Use PyPI Trusted Publishing instead of storing a long-lived PyPI token.
- Update README with `uv tool install llm-wiki` or `pipx install llm-wiki` only
  after the published package has been tested from a clean environment.
- Confirm package data behavior for prompts, templates, docs, and example
  assets before advertising global installation.
- Keep GitHub clone instructions available for contributors and users who want
  the included example wiki.
