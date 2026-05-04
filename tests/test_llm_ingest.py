import pytest

from llmw.core.config import ensure_project_dirs
from llmw.core.paths import WikiPaths
from llmw.llm.client import ChatResult
from llmw.llm.ingest import (
    GeneratedPage,
    IngestGeneration,
    normalize_generated_pages,
    parse_ingest_generation,
    parse_ingest_generation_with_repair,
    sanitize_generated_links,
    validate_generated_pages,
)


def test_parse_ingest_generation_from_fenced_json() -> None:
    generation = parse_ingest_generation(
        """```json
{"pages": [{"path": "wiki/sources/a.md", "content": "# A"}], "log_note": "done"}
```"""
    )

    assert generation.pages[0].path == "wiki/sources/a.md"
    assert generation.log_note == "done"


def test_parse_ingest_generation_repairs_invalid_json_once(tmp_path) -> None:
    paths = WikiPaths.from_root(tmp_path)
    ensure_project_dirs(paths)
    client = FakeRepairClient(
        '{"pages": [{"path": "wiki/sources/source-1234.md", "content": "# Source"}], "log_note": "done"}'
    )

    generation = parse_ingest_generation_with_repair(
        paths,
        "source-1234",
        "I updated the wiki but forgot JSON.",
        client=client,
        system_prompt="Return JSON.",
        temperature=0.2,
        top_p=0.8,
        max_tokens=512,
    )

    assert generation.log_note == "done"
    assert client.calls == 1
    assert "could not be parsed" in client.last_user_prompt


def test_parse_ingest_generation_writes_diagnostic_when_repair_fails(tmp_path) -> None:
    paths = WikiPaths.from_root(tmp_path)
    ensure_project_dirs(paths)
    client = FakeRepairClient("still not json")

    with pytest.raises(ValueError, match=r"\.llmw/errors/ingest-source-1234"):
        parse_ingest_generation_with_repair(
            paths,
            "source-1234",
            "not json",
            client=client,
            system_prompt="Return JSON.",
            temperature=0.2,
            top_p=0.8,
            max_tokens=512,
        )

    artifacts = list((paths.state / "errors").glob("ingest-source-1234-*.txt"))
    assert len(artifacts) == 1
    assert "raw_response:\nnot json" in artifacts[0].read_text(encoding="utf-8")


def test_build_ingest_prompt_prefers_source_language(tmp_path) -> None:
    from llmw.core.models import SourceRecord, SourceRegistry
    from llmw.sources.registry import save_registry

    paths = WikiPaths.from_root(tmp_path)
    ensure_project_dirs(paths)
    paths.index_path.write_text("# Index\n\n", encoding="utf-8")
    source = paths.raw_processed / "zh-source.md"
    source.write_text("长期记忆层让 agent 少重复读取上下文。", encoding="utf-8")
    save_registry(
        paths,
        SourceRegistry(
            sources={
                "zh-source": SourceRecord(
                    source_id="zh-source",
                    title="中文资料",
                    path="raw/processed/zh-source.md",
                    original_path="raw/processed/zh-source.md",
                    media_type="text/markdown",
                    sha256="abc",
                    size_bytes=source.stat().st_size,
                    created_at="2026-01-01T00:00:00Z",
                    updated_at="2026-01-01T00:00:00Z",
                )
            }
        ),
    )

    from llmw.llm.ingest import build_ingest_prompt

    prompt = build_ingest_prompt(paths, "zh-source")

    assert "Prefer the source language" in prompt
    assert "For Chinese" in prompt


def test_generated_pages_must_stay_under_wiki(tmp_path) -> None:
    paths = WikiPaths.from_root(tmp_path)
    ensure_project_dirs(paths)

    with pytest.raises(ValueError, match="under wiki"):
        validate_generated_pages(paths, [GeneratedPage(path="README.md", content="# Bad")])


def test_generated_pages_require_frontmatter(tmp_path) -> None:
    paths = WikiPaths.from_root(tmp_path)
    ensure_project_dirs(paths)

    with pytest.raises(ValueError, match="missing frontmatter"):
        validate_generated_pages(paths, [GeneratedPage(path="wiki/concepts/a.md", content="# A")])


def test_generated_pages_reject_duplicates_and_require_source_page(tmp_path) -> None:
    paths = WikiPaths.from_root(tmp_path)
    ensure_project_dirs(paths)
    content = "---\ntitle: A\ntype: concept\nstatus: draft\nsources: []\ntags: []\n---\n\n# A\n"

    with pytest.raises(ValueError, match="Duplicate"):
        validate_generated_pages(
            paths,
            [
                GeneratedPage(path="wiki/concepts/a.md", content=content),
                GeneratedPage(path="wiki/concepts/a.md", content=content),
            ],
        )

    with pytest.raises(ValueError, match="must include source page"):
        validate_generated_pages(
            paths,
            [GeneratedPage(path="wiki/concepts/a.md", content=content)],
            source_id="source-1234",
        )


def test_generated_pages_reject_canonical_duplicate_paths(tmp_path) -> None:
    paths = WikiPaths.from_root(tmp_path)
    ensure_project_dirs(paths)
    content = "---\ntitle: Coding Agent\ntype: concept\nstatus: draft\nsources: []\ntags: []\n---\n\n# Coding Agent\n"

    with pytest.raises(ValueError, match="Duplicate canonical"):
        validate_generated_pages(
            paths,
            [
                GeneratedPage(path="wiki/concepts/coding-agent.md", content=content),
                GeneratedPage(path="wiki/concepts/Coding_Agent.md", content=content),
            ],
        )


def test_normalize_generated_pages_reuses_existing_canonical_page(tmp_path) -> None:
    paths = WikiPaths.from_root(tmp_path)
    ensure_project_dirs(paths)
    paths.wiki_concepts.mkdir(parents=True, exist_ok=True)
    (paths.wiki_concepts / "coding-agent.md").write_text(
        "---\ntitle: Coding Agent\ntype: concept\nstatus: draft\nsources: []\ntags: []\n---\n\n# Coding Agent\n",
        encoding="utf-8",
    )
    generation = IngestGeneration(
        pages=[
            GeneratedPage(
                path="wiki/concepts/Coding_Agent.md",
                content=(
                    "---\ntitle: Coding Agent\ntype: concept\nstatus: draft\nsources: []\ntags: []\n---\n\n"
                    "# Coding Agent\n\nUpdated."
                ),
            ),
            GeneratedPage(
                path="wiki/sources/source-1234.md",
                content=(
                    "---\ntitle: Source\ntype: source\nstatus: draft\nsources: [\"source-1234\"]\ntags: []\n---\n\n"
                    "# Source\n"
                ),
            ),
        ]
    )

    normalized = normalize_generated_pages(paths, generation, source_id="source-1234")

    assert [page.path for page in normalized.pages] == [
        "wiki/concepts/coding-agent.md",
        "wiki/sources/source-1234.md",
    ]


def test_normalize_generated_pages_uses_unicode_slug_for_chinese_titles(tmp_path) -> None:
    paths = WikiPaths.from_root(tmp_path)
    ensure_project_dirs(paths)
    generation = IngestGeneration(
        pages=[
            GeneratedPage(
                path="wiki/concepts/Long-Term_Memory_Layer.md",
                content=(
                    "---\ntitle: 长期记忆层\ntype: concept\nstatus: draft\nsources: []\ntags: []\n---\n\n"
                    "# 长期记忆层\n"
                ),
            )
        ]
    )

    normalized = normalize_generated_pages(paths, generation, source_id="source-1234")

    assert normalized.pages[0].path == "wiki/concepts/长期记忆层.md"


def test_sanitize_generated_links_delinks_unknown_targets(tmp_path) -> None:
    paths = WikiPaths.from_root(tmp_path)
    ensure_project_dirs(paths)
    generation = IngestGeneration(
        pages=[
            GeneratedPage(
                path="wiki/concepts/llm-wiki.md",
                content=(
                    "---\ntitle: LLM Wiki\ntype: concept\n---\n\n"
                    "# LLM Wiki\n\n"
                    "Links to [[LLM Wiki]], [[source page]]s, and [[Missing|label]]."
                ),
            )
        ]
    )

    sanitized = sanitize_generated_links(paths, generation)

    assert "[[LLM Wiki]]" in sanitized.pages[0].content
    assert "[[source page]]" not in sanitized.pages[0].content
    assert "source pages" in sanitized.pages[0].content
    assert "[[Missing|label]]" not in sanitized.pages[0].content
    assert "label" in sanitized.pages[0].content


def test_sanitize_generated_links_keeps_canonical_existing_target(tmp_path) -> None:
    paths = WikiPaths.from_root(tmp_path)
    ensure_project_dirs(paths)
    (paths.wiki_concepts / "coding-agent.md").write_text(
        "---\ntitle: Coding Agent\ntype: concept\n---\n\n# Coding Agent\n",
        encoding="utf-8",
    )
    generation = IngestGeneration(
        pages=[
            GeneratedPage(
                path="wiki/concepts/notes.md",
                content="---\ntitle: Notes\ntype: concept\n---\n\nSee [[Coding_Agent]].",
            )
        ]
    )

    sanitized = sanitize_generated_links(paths, generation)

    assert "[[Coding_Agent]]" in sanitized.pages[0].content


class FakeRepairClient:
    def __init__(self, content: str):
        self.content = content
        self.calls = 0
        self.last_user_prompt = ""

    def chat(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        top_p: float | None = None,
        max_tokens: int | None = None,
    ) -> ChatResult:
        self.calls += 1
        self.last_user_prompt = user_prompt
        return ChatResult(content=self.content, model="fake")
