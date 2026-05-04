# Security Policy

## Reporting

If you find a security issue, open a private report through GitHub Security Advisories when the repository is hosted, or contact the maintainers privately. Do not publish exploit details before a fix or mitigation is available.

## Sensitive Data

LLM Wiki is designed to run on local knowledge bases. Treat `raw/`, `wiki/`, `.llmw/`, logs, traces, and generated outputs as potentially sensitive unless you intentionally publish them.

Do not commit:

- API keys or provider credentials
- `.env` files
- `.llmw/.env`
- `.llmw/qmd/` databases
- `.llmw/cache/`, `.llmw/sessions/`, `.llmw/plans/`, or `.llmw/search-server/`
- private raw sources or private maintained wiki pages

## Agent Write Safety

Agent-facing writes should use the documented plan/apply workflow. `wiki_patch` is intentionally constrained to `wiki/` and `system/` paths and must reject path traversal, absolute paths, and writes to `raw/`.

MCP tools should preserve the same safety contract as CLI commands.
