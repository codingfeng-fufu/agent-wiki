from __future__ import annotations

from llmw.core.config import ensure_project_dirs, write_config
from llmw.core.fs import relative_to_root
from llmw.core.markdown import read_markdown
from llmw.core.paths import WikiPaths
from llmw.health.checks import HealthChecker
from llmw.sources.registry import add_source, load_registry, update_source
from llmw.wiki.index import index_is_current, rebuild_index


def test_registry_page_refs_and_page_sources_stay_consistent(tmp_path) -> None:
    paths = WikiPaths.from_root(tmp_path)
    ensure_project_dirs(paths)
    write_config(paths)
    paths.log_path.write_text("# Log\n\n", encoding="utf-8")

    source = paths.raw_inbox / "evidence.md"
    source.write_text("# Evidence\n\nA note about connected wiki pages.", encoding="utf-8")
    record = add_source(paths, source, [".md"])

    source_page = paths.wiki_sources / f"{record.source_id}.md"
    concept_page = paths.wiki_concepts / "connected-concept.md"
    source_page.write_text(
        f"""---
title: Evidence Source
type: source
status: draft
sources: ["{record.source_id}"]
tags: []
---

# Evidence Source

This source informs [[Connected Concept]].
""",
        encoding="utf-8",
    )
    concept_page.write_text(
        f"""---
title: Connected Concept
type: concept
status: draft
sources: ["{record.source_id}"]
tags: []
---

# Connected Concept

This concept is grounded in [[Evidence Source]].
""",
        encoding="utf-8",
    )
    record.status = "ingested"
    record.pages = [
        relative_to_root(source_page, paths.root),
        relative_to_root(concept_page, paths.root),
    ]
    update_source(paths, record)
    rebuild_index(paths)

    assert _registry_integrity_errors(paths) == []
    assert index_is_current(paths)
    assert HealthChecker(paths).run() == []


def test_rebuild_index_strips_trailing_whitespace_from_summaries(tmp_path) -> None:
    paths = WikiPaths.from_root(tmp_path)
    ensure_project_dirs(paths)
    write_config(paths)
    concept_page = paths.wiki_concepts / "trimmed-summary.md"
    content_with_trailing_space = (
        """---
title: Trimmed Summary
type: concept
status: draft
sources: []
tags: []
---

# Trimmed Summary

This summary ends with a comma,"""
        + " \n"
    )
    concept_page.write_text(content_with_trailing_space, encoding="utf-8")

    content = rebuild_index(paths)

    assert "comma, \n" not in content
    assert "comma,\n" in content
    assert index_is_current(paths)


def test_registry_integrity_reports_unknown_page_source_id(tmp_path) -> None:
    paths = WikiPaths.from_root(tmp_path)
    ensure_project_dirs(paths)
    write_config(paths)

    page = paths.wiki_concepts / "orphan-source-id.md"
    page.write_text(
        """---
title: Orphan Source Id
type: concept
status: draft
sources: ["missing-source"]
tags: []
---

# Orphan Source Id
""",
        encoding="utf-8",
    )

    assert _registry_integrity_errors(paths) == [
        "wiki/concepts/orphan-source-id.md references unknown source_id: missing-source"
    ]


def _registry_integrity_errors(paths: WikiPaths) -> list[str]:
    registry = load_registry(paths)
    source_ids = set(registry.sources)
    errors: list[str] = []

    for source_id, record in registry.sources.items():
        if not (paths.root / record.path).exists():
            errors.append(f"{source_id} registered source file is missing: {record.path}")
        for page in record.pages:
            if not (paths.root / page).exists():
                errors.append(f"{source_id} lists missing wiki page: {page}")

    for page in sorted(paths.wiki.rglob("*.md")) if paths.wiki.exists() else []:
        metadata, _ = read_markdown(page)
        page_sources = metadata.get("sources") or []
        if not isinstance(page_sources, list):
            continue
        for source_id in page_sources:
            if source_id not in source_ids:
                errors.append(
                    f"{relative_to_root(page, paths.root)} references unknown source_id: {source_id}"
                )

    return errors
