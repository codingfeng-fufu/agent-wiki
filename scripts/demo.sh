#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
LLMW="${LLMW:-"$ROOT/.venv/bin/llmw"}"

if [[ ! -x "$LLMW" ]]; then
  echo "error: llmw executable not found at $LLMW" >&2
  echo "run: uv sync --extra dev" >&2
  exit 1
fi

cd "$ROOT"

run() {
  printf '\n$ %s\n' "$*"
  "$@"
}

echo "LLM Wiki demo"
echo "Root: $ROOT"
echo
echo "This demo is read-only. It shows the agent-facing loop: context, search,"
echo "maintenance planning, plan dry-run, and health verification."

run "$LLMW" context --json
run "$LLMW" search "prompt injection tool safety" --limit 5 --json
run "$LLMW" maintain --no-audit --no-save-plan --json

PLAN_OUTPUT="$(mktemp -t llmw-demo-plan-output.XXXXXX.json)"
trap 'rm -f "$PLAN_OUTPUT"' EXIT

printf '\n$ %s\n' "$LLMW plan \"rebuild index before publishing\" --json --save --preview"
"$LLMW" plan "rebuild index before publishing" --json --save --preview | tee "$PLAN_OUTPUT"
SAVED_PLAN="$(sed -n 's/.*"saved_plan": "\([^"]*\)".*/\1/p' "$PLAN_OUTPUT" | head -1)"

if [[ -n "$SAVED_PLAN" ]]; then
  run "$LLMW" apply "$SAVED_PLAN" --dry-run --json
else
  echo "warning: no saved plan found; skipping apply dry-run" >&2
fi

run "$LLMW" health check --json
