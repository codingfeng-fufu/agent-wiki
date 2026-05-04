from llmw.core.markdown import dump_frontmatter, extract_title, extract_wiki_links, split_frontmatter


def test_frontmatter_roundtrip() -> None:
    text = dump_frontmatter({"title": "Alpha", "type": "concept"}, "# Alpha\n\nBody")
    metadata, body = split_frontmatter(text)

    assert metadata["title"] == "Alpha"
    assert metadata["type"] == "concept"
    assert body.startswith("# Alpha")


def test_extract_title_and_wiki_links(tmp_path) -> None:
    path = tmp_path / "alpha-note.md"
    body = "# Heading Title\n\nLinks to [[Beta]] and [[Gamma|label]] and [[Delta#section]]."

    assert extract_title(path, body, {}) == "Heading Title"
    assert extract_wiki_links(body) == ["Beta", "Gamma", "Delta"]


def test_invalid_frontmatter_is_reported_without_raising() -> None:
    metadata, body = split_frontmatter("---\ntitle: [\n---\n\n# Broken")

    assert "_frontmatter_error" in metadata
    assert body.startswith("# Broken")
