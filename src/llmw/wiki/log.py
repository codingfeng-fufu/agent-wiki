from __future__ import annotations

import re
from pathlib import Path

from llmw.core.fs import today_iso
from llmw.core.paths import WikiPaths


LOG_HEADING_RE = re.compile(r"^## \[\d{4}-\d{2}-\d{2}\] .+ \| .+")


def format_log_entry(kind: str, title: str, note: str = "") -> str:
    body = note.strip()
    lines = [f"## [{today_iso()}] {kind.strip()} | {title.strip()}", ""]
    if body:
        lines.extend([body, ""])
    return "\n".join(lines)


def append_log(paths: WikiPaths, kind: str, title: str, note: str = "") -> str:
    paths.log_path.parent.mkdir(parents=True, exist_ok=True)
    entry = format_log_entry(kind, title, note)
    if not paths.log_path.exists():
        paths.log_path.write_text("# Log\n\n", encoding="utf-8")
    existing = paths.log_path.read_text(encoding="utf-8", errors="replace")
    separator = "" if existing.endswith("\n\n") else "\n"
    paths.log_path.write_text(existing + separator + entry, encoding="utf-8")
    return entry


def malformed_log_headings(path: Path) -> list[int]:
    if not path.exists():
        return []
    bad: list[int] = []
    for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        if line.startswith("## ") and not LOG_HEADING_RE.match(line):
            bad.append(number)
    return bad
