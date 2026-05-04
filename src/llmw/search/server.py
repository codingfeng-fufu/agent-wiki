from __future__ import annotations

import json
import sys
from typing import TextIO

from llmw.core.config import load_config
from llmw.core.paths import WikiPaths
from llmw.search.providers import build_search_service, recommend_search_strategy


def serve_search_lines(
    paths: WikiPaths,
    *,
    input_stream: TextIO = sys.stdin,
    output_stream: TextIO = sys.stdout,
    deep: bool = False,
    default_limit: int = 5,
) -> None:
    config = load_config(paths)
    service = build_search_service(paths, config.qmd_collection, use_qmd=deep)
    _write_line(output_stream, {"ok": True, "ready": True, "deep": deep, "protocol": "llmw-search-ndjson-v1"})
    for raw_line in input_stream:
        line = raw_line.strip()
        if not line:
            continue
        try:
            request = _parse_request(line)
            action = str(request.get("action") or "search")
            if action == "ping":
                _write_line(output_stream, {"ok": True, "pong": True})
                continue
            if action in {"exit", "quit"}:
                _write_line(output_stream, {"ok": True, "bye": True})
                break
            query = str(request.get("query") or "").strip()
            if not query:
                raise ValueError("request.query must not be empty")
            limit = int(request.get("limit") or default_limit)
            request_deep = bool(request.get("deep", deep))
            results, warning = service.search(query, limit=limit, deep=request_deep)
            _write_line(
                output_stream,
                {
                    "ok": True,
                    "query": query,
                    "warning": warning,
                    "strategy": recommend_search_strategy(query, deep=request_deep),
                    "results": [result.model_dump() for result in results],
                },
            )
        except Exception as exc:
            _write_line(output_stream, {"ok": False, "error": {"code": "search-server-failed", "message": str(exc)}})


def _parse_request(line: str) -> dict:
    if line.startswith("{"):
        parsed = json.loads(line)
        if not isinstance(parsed, dict):
            raise ValueError("JSON request must be an object")
        return parsed
    return {"query": line}


def _write_line(output_stream: TextIO, payload: dict) -> None:
    output_stream.write(json.dumps(payload, ensure_ascii=False) + "\n")
    output_stream.flush()
