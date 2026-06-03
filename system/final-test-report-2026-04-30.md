# Final Test Report — 2026-04-30

## Verdict

PASS.

The project is in release-candidate condition for local agent use. Core CLI, JSON contract, MCP stdio, warm search daemon, safe plan/apply, retrieval benchmark, provider connectivity, and structural health checks all passed final validation.

## Environment

- Project root: `/path/to/agent-wiki`
- Tool version: `llmw 0.1.0`
- Python: `3.11.5`
- LLM provider: `qwen_plus`
- Model: `qwen-plus`
- Wiki state: 48 pages, 8 registered sources, 8 ingested sources
- Index state: current
- Structural health: 0 errors, 0 warnings, 0 infos

## Test Scope

### 1. Full Automated Test Suite

Command:

```bash
./.venv/bin/pytest -q
```

Result:

- Status: PASS
- Tests: 95 passed
- Duration: 43.37s

Coverage included:

- source registration and ingest records
- wiki health checks
- query and health audit prompt wiring
- search providers and fallback logic
- benchmark harness
- agent session routing
- plan/apply safety behavior
- MCP stdio server behavior
- search daemon lifecycle
- release packaging checks
- subprocess-level integration contracts

### 2. Release Gate

Command:

```bash
scripts/release_check.sh
```

Result:

- Status: PASS
- Embedded pytest: 95 passed
- Offline health: no issues
- CLI smoke: passed
- Search daemon smoke: passed
- Default search benchmark gate: passed

Default search benchmark:

- Provider: `python`
- Queries: 102
- Top-k: 5
- Precision@5: 0.1412
- Precision ceiling@5: 0.2353
- Recall@5: 0.6863
- F1@5: 0.2328
- HitRate@5: 0.7059
- MRR@5: 0.5129

Interpretation:

- Precision is low in absolute terms because most benchmark cases have one expected relevant page and top-k is fixed at 5.
- Precision is therefore bounded by the benchmark design; Recall, HitRate, and MRR are more useful for release gating.
- Default fast search is acceptable for low-latency lookup.

### 3. Deep Retrieval Gate

Command:

```bash
./.venv/bin/llmw benchmark search \
  --root . \
  --provider llmw \
  --top-k 5 \
  --fail-under-f1 0.34 \
  --fail-under-recall 0.95 \
  --fail-under-hit-rate 0.95
```

Result:

- Status: PASS
- Provider: `llmw`
- Queries: 102
- Top-k: 5
- Precision@5: 0.2235
- Precision ceiling@5: 0.2353
- Recall@5: 0.9820
- F1@5: 0.3546
- HitRate@5: 1.0000
- MRR@5: 0.9355

Notes:

- qmd loaded the local `Qwen/Qwen3-Embedding-0.6B` model successfully.
- Runtime emitted a CUDA driver warning, then continued successfully on the available backend.
- Deep retrieval is strong enough for release gating and should be preferred for recall-sensitive agent tasks.

### 4. LLM Provider Smoke

Command:

```bash
./.venv/bin/llmw llm check --root .
```

Result:

- Status: PASS
- Provider: `qwen_plus`
- Model: `qwen-plus`
- Response: `OK`

Query smoke:

```bash
LLMW_DISABLE_QMD=1 ./.venv/bin/llmw query guardrails --root . --limit 3 --json
```

Result:

- Status: PASS
- Provider/model path worked end-to-end
- Evidence pages returned:
  - `wiki/concepts/agent-guardrails.md`
  - `wiki/concepts/input-guardrails.md`
  - `wiki/concepts/output-guardrails.md`
- Output was valid JSON with `ok: true`
- Usage: 973 total tokens

### 5. Semantic Health Audit Smoke

Command:

```bash
./.venv/bin/llmw health audit --root . --max-pages 8 --max-page-chars 1200 --json
```

Result:

- Status: PASS
- Model: `qwen-plus`
- Reviewed pages: 8
- Saved page: none
- Usage: 7708 total tokens
- Output was valid JSON with `ok: true`

Audit notes:

- The audit produced advisory semantic maintenance suggestions.
- Structured `issues` contained 3 low-severity follow-up source gaps.
- No structural health blocker was found.
- These recommendations are maintenance backlog items, not release blockers.

### 6. Integration Contracts

Integration tests were included in the full pytest run.

Covered contracts:

- Real subprocess CLI flow: `init → source add → ingest packet → manual wiki pages → ingest record → context → health → search → maintain`
- Safe apply flow: `apply --dry-run` preview, real apply, raw-path rejection
- Search daemon flow: `start → status → query → stop`
- MCP stdio flow: `initialize → tools/list → tools/call`

Important issue found and fixed:

- Long temporary project paths can exceed Unix socket path limits.
- The daemon socket now uses `/tmp/llmw-search-<hash>.sock`, while metadata/logs remain under `.llmw/search-server/`.

## Known Non-Blocking Notes

- The repository currently has staged and untracked changes because this is an uncommitted working tree, not a committed release branch.
- Deep search may show a CUDA driver warning on this machine, but the benchmark completes successfully.
- Semantic audit may surface ongoing wiki-maintenance suggestions. These should feed future maintenance plans, not block the current release candidate.

## Final Assessment

The implementation is ready for local agent integration testing as a v1 release candidate.

The strongest validated usage path is:

1. Agent reads `AGENTS.md`.
2. Agent runs `llmw context --json`.
3. Agent uses `llmw search` for fast lookup.
4. Agent uses `llmw search-daemon start --deep` or `llmw mcp --root .` for repeated high-recall use.
5. Agent uses `llmw plan --preview` and `llmw apply --dry-run` before any write.
6. Release gate remains `scripts/release_check.sh` plus optional deep benchmark and LLM smoke.
