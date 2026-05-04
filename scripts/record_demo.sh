#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
OUT_DIR="${OUT_DIR:-"$ROOT/dist/demo"}"
CAST_FILE="$OUT_DIR/llm-wiki-demo.cast"
GIF_FILE="$OUT_DIR/llm-wiki-demo.gif"

if ! command -v asciinema >/dev/null 2>&1; then
  echo "error: asciinema is required to record the demo" >&2
  echo "install it, or run scripts/demo.sh directly" >&2
  exit 1
fi

mkdir -p "$OUT_DIR"

asciinema rec "$CAST_FILE" --overwrite -c "$ROOT/scripts/demo.sh"
echo "wrote $CAST_FILE"

if command -v agg >/dev/null 2>&1; then
  agg "$CAST_FILE" "$GIF_FILE"
  echo "wrote $GIF_FILE"
else
  echo "install agg to render a GIF from the cast file" >&2
fi
