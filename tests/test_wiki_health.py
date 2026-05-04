from llmw.core.config import ensure_project_dirs
from llmw.core.paths import WikiPaths
from llmw.health.checks import HealthChecker
from llmw.sources.registry import add_source
from llmw.wiki.index import rebuild_index


def test_health_reports_bad_links_and_missing_frontmatter(tmp_path) -> None:
    paths = WikiPaths.from_root(tmp_path)
    ensure_project_dirs(paths)
    page_dir = tmp_path / "wiki" / "concepts"
    page_dir.mkdir(parents=True, exist_ok=True)
    (page_dir / "alpha.md").write_text("# Alpha\n\nSee [[Missing Page]].", encoding="utf-8")
    rebuild_index(paths)

    issues = HealthChecker(paths).run()
    codes = {issue.code for issue in issues}

    assert "bad-link" in codes
    assert "missing-frontmatter" in codes


def test_health_accepts_registered_inbox_original(tmp_path) -> None:
    paths = WikiPaths.from_root(tmp_path)
    ensure_project_dirs(paths)
    source = paths.raw_inbox / "note.md"
    source.write_text("# Note\n\nRegistered from inbox.", encoding="utf-8")
    add_source(paths, source, [".md"])
    rebuild_index(paths)

    issues = HealthChecker(paths).run()

    assert "unregistered-inbox-source" not in {issue.code for issue in issues}


def test_health_reports_nested_unregistered_inbox_source(tmp_path) -> None:
    paths = WikiPaths.from_root(tmp_path)
    ensure_project_dirs(paths)
    nested = paths.raw_inbox / "topic" / "note.md"
    nested.parent.mkdir(parents=True)
    nested.write_text("# Note\n\nNested source.", encoding="utf-8")
    rebuild_index(paths)

    issues = HealthChecker(paths).run()

    assert "unregistered-inbox-source" in {issue.code for issue in issues}


def test_health_resolves_special_index_and_log_links(tmp_path) -> None:
    paths = WikiPaths.from_root(tmp_path)
    ensure_project_dirs(paths)
    paths.index_path.write_text("---\ntitle: Index\ntype: index\n---\n\n# Index\n", encoding="utf-8")
    paths.log_path.write_text("# Log\n\n", encoding="utf-8")
    page = paths.wiki_concepts / "links.md"
    page.write_text(
        "---\ntitle: Links\ntype: concept\n---\n\n# Links\n\nSee [[Index]] and [[Log]].",
        encoding="utf-8",
    )

    issues = HealthChecker(paths).run()

    bad_link_messages = [issue.message for issue in issues if issue.code == "bad-link"]
    assert all("[[Index]]" not in message and "[[Log]]" not in message for message in bad_link_messages)


def test_health_reports_invalid_frontmatter_without_crashing(tmp_path) -> None:
    paths = WikiPaths.from_root(tmp_path)
    ensure_project_dirs(paths)
    page = paths.wiki_concepts / "broken.md"
    page.write_text("---\ntitle: [\n---\n\n# Broken\n", encoding="utf-8")

    issues = HealthChecker(paths).run()

    assert "invalid-frontmatter" in {issue.code for issue in issues}


def test_health_reports_duplicate_canonical_pages(tmp_path) -> None:
    paths = WikiPaths.from_root(tmp_path)
    ensure_project_dirs(paths)
    paths.wiki_concepts.mkdir(parents=True, exist_ok=True)
    content = "---\ntitle: Coding Agent\ntype: concept\nstatus: draft\nsources: []\ntags: []\n---\n\n# Coding Agent\n"
    (paths.wiki_concepts / "coding-agent.md").write_text(content, encoding="utf-8")
    (paths.wiki_concepts / "Coding_Agent.md").write_text(content, encoding="utf-8")

    issues = HealthChecker(paths).run()
    duplicate_issues = [issue for issue in issues if issue.code == "duplicate-canonical-page"]

    assert duplicate_issues
    assert duplicate_issues[0].severity == "warning"
    assert "wiki/concepts/Coding_Agent.md" in duplicate_issues[0].message
    assert "wiki/concepts/coding-agent.md" in duplicate_issues[0].message
