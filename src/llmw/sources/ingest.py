from __future__ import annotations

from pathlib import Path

from llmw.core.paths import WikiPaths
from llmw.sources.extract import extract_source_text
from llmw.sources.registry import get_source


def build_ingest_packet(paths: WikiPaths, source_id: str, *, max_chars: int = 12000) -> str:
    record = get_source(paths, source_id)
    source_path = paths.root / record.path
    text, error = extract_source_text(source_path, max_chars=max_chars)
    source_page = f"wiki/sources/{record.source_id}.md"

    packet = [
        f"# Ingest Packet: {record.title}",
        "",
        "## Source",
        f"- source_id: `{record.source_id}`",
        f"- path: `{record.path}`",
        f"- media_type: `{record.media_type}`",
        f"- sha256: `{record.sha256}`",
        "",
        "## Required Agent Work",
        "1. Read the source excerpt and, when needed, open the full source file.",
        f"2. Create or update `{source_page}` with a source summary.",
        "3. Update related concept/entity/analysis pages using Obsidian wiki links.",
        "4. Keep factual claims tied to `source_id` in frontmatter or citations.",
        "5. Run `llmw ingest record` after edits are complete.",
        "",
        "## Suggested Source Page Frontmatter",
        "```yaml",
        f'title: "{record.title}"',
        "type: source",
        "status: draft",
        f'sources: ["{record.source_id}"]',
        "tags: []",
        "```",
        "",
        "## Extracted Text",
    ]
    if error:
        packet.extend(["", f"> Extraction warning: {error}", ""])
    packet.extend(["", "```text", text or "(No text extracted.)", "```"])
    return "\n".join(packet)
