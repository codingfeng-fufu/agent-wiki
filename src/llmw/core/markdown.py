from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml


FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.DOTALL)
WIKI_LINK_RE = re.compile(r"(?<!!)\[\[([^\]\n]+)\]\]")
HEADING_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
YAML_SAFE_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
YAML_SAFE_DUMPER = getattr(yaml, "CSafeDumper", yaml.SafeDumper)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    raw = match.group(1).strip()
    try:
        data = yaml.load(raw, Loader=YAML_SAFE_LOADER) if raw else {}
    except yaml.YAMLError as exc:
        return {"_frontmatter_error": str(exc)}, text[match.end() :]
    if not isinstance(data, dict):
        data = {}
    return data, text[match.end() :]


def dump_frontmatter(data: dict[str, Any], body: str) -> str:
    yaml_text = yaml.dump(data, Dumper=YAML_SAFE_DUMPER, allow_unicode=True, sort_keys=False).strip()
    return f"---\n{yaml_text}\n---\n\n{body.lstrip()}"


def read_markdown(path: Path) -> tuple[dict[str, Any], str]:
    return split_frontmatter(read_text(path))


def extract_title(path: Path, text: str, metadata: dict[str, Any] | None = None) -> str:
    metadata = metadata or {}
    title = metadata.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    match = HEADING_RE.search(text)
    if match:
        return match.group(1).strip()
    return path.stem.replace("-", " ").replace("_", " ").strip().title() or path.stem


def extract_summary(body: str, *, max_chars: int = 180) -> str:
    for paragraph in re.split(r"\n\s*\n", body):
        cleaned = " ".join(line.strip() for line in paragraph.splitlines()).strip()
        if cleaned and not cleaned.startswith("#"):
            return cleaned[:max_chars]
    return ""


def extract_wiki_links(text: str) -> list[str]:
    links: list[str] = []
    for raw in WIKI_LINK_RE.findall(text):
        target = raw.split("|", 1)[0].split("#", 1)[0].strip()
        if target and target not in links:
            links.append(target)
    return links
