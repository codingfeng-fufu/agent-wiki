#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

LLMW="${LLMW:-./.venv/bin/llmw}"
PYTHON="${PYTHON:-./.venv/bin/python}"
PYTEST="${PYTEST:-./.venv/bin/pytest}"
RUN_LLM_SMOKE="${RUN_LLM_SMOKE:-0}"
RUN_SEARCH_BENCHMARK="${RUN_SEARCH_BENCHMARK:-1}"
SEARCH_PROVIDER="${SEARCH_PROVIDER:-python}"
SEARCH_TOP_K="${SEARCH_TOP_K:-5}"
SEARCH_FAIL_UNDER_F1="${SEARCH_FAIL_UNDER_F1:-0.20}"
SEARCH_FAIL_UNDER_RECALL="${SEARCH_FAIL_UNDER_RECALL:-0.60}"
SEARCH_FAIL_UNDER_HIT_RATE="${SEARCH_FAIL_UNDER_HIT_RATE:-0.60}"
RUN_DEEP_SEARCH_BENCHMARK="${RUN_DEEP_SEARCH_BENCHMARK:-0}"
DEEP_SEARCH_PROVIDER="${DEEP_SEARCH_PROVIDER:-llmw}"
DEEP_SEARCH_FAIL_UNDER_F1="${DEEP_SEARCH_FAIL_UNDER_F1:-0.34}"
DEEP_SEARCH_FAIL_UNDER_RECALL="${DEEP_SEARCH_FAIL_UNDER_RECALL:-0.95}"
DEEP_SEARCH_FAIL_UNDER_HIT_RATE="${DEEP_SEARCH_FAIL_UNDER_HIT_RATE:-0.95}"
LLM_SMOKE_QUERY="${LLM_SMOKE_QUERY:-guardrails}"
LLM_SMOKE_DISABLE_QMD="${LLM_SMOKE_DISABLE_QMD:-1}"

section() {
  printf '\n== %s ==\n' "$1"
}

require_executable() {
  if [[ ! -x "$1" ]]; then
    printf 'Missing executable: %s\n' "$1" >&2
    exit 1
  fi
}

section "Tooling"
require_executable "$LLMW"
require_executable "$PYTHON"
require_executable "$PYTEST"
trap '"$LLMW" search-daemon stop --root . --json >/dev/null 2>&1 || true' EXIT
"$LLMW" --version
"$PYTHON" --version

section "Tests"
"$PYTEST" -q

section "Offline Health"
"$LLMW" health check --root .

section "CLI Smoke"
"$LLMW" --help >/dev/null
"$LLMW" context --help >/dev/null
"$LLMW" doctor --help >/dev/null
"$LLMW" next --help >/dev/null
"$LLMW" plan --help >/dev/null
"$LLMW" apply --help >/dev/null
"$LLMW" maintain --help >/dev/null
"$LLMW" source --help >/dev/null
"$LLMW" ingest --help >/dev/null
"$LLMW" search --help >/dev/null
"$LLMW" search-server --help >/dev/null
"$LLMW" search-daemon --help >/dev/null
"$LLMW" mcp --help >/dev/null
"$LLMW" query --help >/dev/null
"$LLMW" agent --help >/dev/null
"$LLMW" health audit --help >/dev/null
"$LLMW" benchmark search --help >/dev/null
"$LLMW" benchmark perf --help >/dev/null
"$LLMW" release --help >/dev/null
"$LLMW" release check --help >/dev/null
"$LLMW" package --help >/dev/null
"$LLMW" package build --help >/dev/null
"$LLMW" install-agent --help >/dev/null
"$LLMW" install-agent codex --help >/dev/null

section "Search Daemon Smoke"
LLMW_DISABLE_QMD=1 "$LLMW" search-daemon start --root . --limit 2 --json >/dev/null
"$LLMW" search-daemon status --root . --json >/dev/null
"$LLMW" search-daemon query guardrails --root . --limit 2 --json >/dev/null
"$LLMW" search-daemon stop --root . --json >/dev/null

section "Doctor Smoke"
"$LLMW" doctor --root . --no-codex --json >/dev/null

section "Release Command Smoke"
"$LLMW" release check --root . --no-tests --no-benchmark --no-sdist --no-codex --json >/dev/null

if [[ "$RUN_SEARCH_BENCHMARK" == "1" ]]; then
  section "Search Benchmark"
  "$LLMW" benchmark search \
    --root . \
    --provider "$SEARCH_PROVIDER" \
    --top-k "$SEARCH_TOP_K" \
    --fail-under-f1 "$SEARCH_FAIL_UNDER_F1" \
    --fail-under-recall "$SEARCH_FAIL_UNDER_RECALL" \
    --fail-under-hit-rate "$SEARCH_FAIL_UNDER_HIT_RATE"
else
  section "Search Benchmark"
  printf 'Skipped because RUN_SEARCH_BENCHMARK=%s\n' "$RUN_SEARCH_BENCHMARK"
fi

if [[ "$RUN_DEEP_SEARCH_BENCHMARK" == "1" ]]; then
  section "Deep Search Benchmark"
  "$LLMW" benchmark search \
    --root . \
    --provider "$DEEP_SEARCH_PROVIDER" \
    --top-k "$SEARCH_TOP_K" \
    --fail-under-f1 "$DEEP_SEARCH_FAIL_UNDER_F1" \
    --fail-under-recall "$DEEP_SEARCH_FAIL_UNDER_RECALL" \
    --fail-under-hit-rate "$DEEP_SEARCH_FAIL_UNDER_HIT_RATE"
else
  section "Deep Search Benchmark"
  printf 'Skipped because RUN_DEEP_SEARCH_BENCHMARK=%s. Set RUN_DEEP_SEARCH_BENCHMARK=1 to run qmd/llmw gates.\n' "$RUN_DEEP_SEARCH_BENCHMARK"
fi

if [[ "$RUN_LLM_SMOKE" == "1" ]]; then
  section "LLM Smoke"
  "$LLMW" llm check --root .
  LLMW_DISABLE_QMD="$LLM_SMOKE_DISABLE_QMD" "$LLMW" query "$LLM_SMOKE_QUERY" --root . --limit 3 --json >/dev/null
  "$LLMW" health audit --root . --max-pages 8 --max-page-chars 1200 --json >/dev/null
else
  section "LLM Smoke"
  printf 'Skipped because RUN_LLM_SMOKE=%s. Set RUN_LLM_SMOKE=1 to call the configured provider.\n' "$RUN_LLM_SMOKE"
fi

section "Done"
printf 'Release checks passed.\n'
