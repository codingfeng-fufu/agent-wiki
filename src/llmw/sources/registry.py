from __future__ import annotations

import json
import shutil
from pathlib import Path

from llmw.core.fs import ensure_parent, relative_to_root, sha256_file, slugify, utc_now_iso
from llmw.core.models import SourceRecord, SourceRegistry
from llmw.core.paths import WikiPaths
from llmw.sources.extract import media_type_for


def load_registry(paths: WikiPaths) -> SourceRegistry:
    if not paths.source_registry_path.exists():
        return SourceRegistry()
    data = json.loads(paths.source_registry_path.read_text(encoding="utf-8"))
    return SourceRegistry.model_validate(data)


def save_registry(paths: WikiPaths, registry: SourceRegistry) -> None:
    ensure_parent(paths.source_registry_path)
    paths.source_registry_path.write_text(
        json.dumps(registry.model_dump(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def find_by_hash(registry: SourceRegistry, digest: str) -> SourceRecord | None:
    for record in registry.sources.values():
        if record.sha256 == digest:
            return record
    return None


def add_source(paths: WikiPaths, source_path: Path, allowed_extensions: list[str]) -> SourceRecord:
    source_path = source_path.resolve()
    if not source_path.exists() or not source_path.is_file():
        raise FileNotFoundError(source_path)

    suffix = source_path.suffix.lower()
    if suffix not in {ext.lower() for ext in allowed_extensions}:
        raise ValueError(f"Unsupported source extension: {suffix}")

    registry = load_registry(paths)
    digest = sha256_file(source_path)
    duplicate = find_by_hash(registry, digest)
    if duplicate:
        return duplicate

    title = source_path.stem.replace("_", " ").replace("-", " ").strip() or source_path.stem
    source_id = f"{slugify(source_path.stem)}-{digest[:8]}"
    destination = paths.raw_processed / f"{source_id}{source_path.suffix.lower()}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source_path != destination.resolve():
        shutil.copy2(source_path, destination)

    now = utc_now_iso()
    record = SourceRecord(
        source_id=source_id,
        title=title,
        path=relative_to_root(destination, paths.root),
        original_path=relative_to_root(source_path, paths.root),
        media_type=media_type_for(destination),
        sha256=digest,
        size_bytes=destination.stat().st_size,
        status="registered",
        created_at=now,
        updated_at=now,
    )
    registry.sources[record.source_id] = record
    save_registry(paths, registry)
    return record


def get_source(paths: WikiPaths, source_id: str) -> SourceRecord:
    registry = load_registry(paths)
    try:
        return registry.sources[source_id]
    except KeyError as exc:
        raise KeyError(f"Unknown source_id: {source_id}") from exc


def update_source(paths: WikiPaths, record: SourceRecord) -> SourceRecord:
    registry = load_registry(paths)
    record.updated_at = utc_now_iso()
    registry.sources[record.source_id] = record
    save_registry(paths, registry)
    return record
