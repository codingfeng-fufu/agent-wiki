from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from llmw.core.paths import WikiPaths
from llmw.search.benchmark import assert_benchmark_gates, evaluate, format_benchmark_summary, payload_to_json, run_search_benchmark


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate LLM Wiki search against the benchmark query set.")
    parser.add_argument("--root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--provider", choices=["python", "rg", "qmd", "llmw"], default="python")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--include-special", action="store_true", help="Include wiki/index.md and wiki/log.md in the searched corpus.")
    parser.add_argument("--json", action="store_true", help="Print full JSON results.")
    parser.add_argument("--fail-under-f1", type=float, default=None)
    parser.add_argument("--fail-under-recall", type=float, default=None)
    parser.add_argument("--fail-under-hit-rate", type=float, default=None)
    args = parser.parse_args(argv)

    try:
        payload = run_search_benchmark(
            WikiPaths.from_root(args.root),
            provider=args.provider,
            top_k=args.top_k,
            include_special=args.include_special,
        )
        assert_benchmark_gates(
            payload["summary"],
            fail_under_f1=args.fail_under_f1,
            fail_under_recall=args.fail_under_recall,
            fail_under_hit_rate=args.fail_under_hit_rate,
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.json:
        print(payload_to_json(payload))
    else:
        print(format_benchmark_summary(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
