from __future__ import annotations

import re
import json
import shutil
import subprocess
import tarfile
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ALLOWED_RAW_PLACEHOLDERS = {
    "raw/assets/.gitkeep",
    "raw/inbox/.gitkeep",
    "raw/processed/.gitkeep",
}
ALLOWED_WIKI_TEMPLATES = {
    "wiki/index.md",
    "wiki/log.md",
}


def test_sdist_excludes_local_state_and_ingested_content(tmp_path) -> None:
    if shutil.which("uv") is None:
        pytest.skip("uv is required for release packaging checks")

    subprocess.run(
        ["uv", "build", "--sdist", "--out-dir", str(tmp_path)],
        cwd=PROJECT_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    sdist = next(tmp_path.glob("*.tar.gz"))
    members = _sdist_members(sdist)

    assert not [path for path in members if path.startswith(".llmw/")]
    assert not [path for path in members if path.startswith("raw/") and path not in ALLOWED_RAW_PLACEHOLDERS]
    assert not [path for path in members if path.startswith("wiki/") and path not in ALLOWED_WIKI_TEMPLATES]

    contents = _sdist_text_contents(sdist)
    if "wiki/index.md" in contents:
        assert "Generated from `0` wiki pages." in contents["wiki/index.md"]
    if "wiki/log.md" in contents:
        assert contents["wiki/log.md"].strip() == "# Log"


def test_sdist_does_not_ship_env_files_or_real_api_keys(tmp_path) -> None:
    if shutil.which("uv") is None:
        pytest.skip("uv is required for release packaging checks")

    subprocess.run(
        ["uv", "build", "--sdist", "--out-dir", str(tmp_path)],
        cwd=PROJECT_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    sdist = next(tmp_path.glob("*.tar.gz"))
    members = _sdist_members(sdist)
    contents = _sdist_text_contents(sdist)

    assert not [path for path in members if path.endswith(".env") or "/.env" in path]
    for path, content in contents.items():
        for match in re.finditer(r"DASHSCOPE_API_KEY\s*=\s*['\"]?([^'\"\s]+)", content):
            value = match.group(1).removesuffix("\\n")
            assert value in {"your-dashscope-api-key", "from-file"}, f"unexpected key-like value in {path}"


def test_plugin_manifest_points_to_llmw_mcp() -> None:
    manifest = json.loads((PROJECT_ROOT / "plugins" / "llm-wiki" / ".codex-plugin" / "plugin.json").read_text())
    mcp = json.loads((PROJECT_ROOT / "plugins" / "llm-wiki" / ".mcp.json").read_text())

    assert manifest["name"] == "llm-wiki"
    assert manifest["mcpServers"] == "./.mcp.json"
    assert mcp["mcpServers"]["llm-wiki"]["command"] == "./.venv/bin/llmw"
    assert mcp["mcpServers"]["llm-wiki"]["args"] == ["mcp", "--root", "."]
    assert mcp["mcpServers"]["llm-wiki"]["default_tools_approval_mode"] == "approve"


def _sdist_members(sdist: Path) -> set[str]:
    with tarfile.open(sdist) as archive:
        return {_strip_sdist_prefix(member.name) for member in archive.getmembers() if member.isfile()}


def _sdist_text_contents(sdist: Path) -> dict[str, str]:
    contents: dict[str, str] = {}
    with tarfile.open(sdist) as archive:
        for member in archive.getmembers():
            if not member.isfile():
                continue
            extracted = archive.extractfile(member)
            if extracted is None:
                continue
            data = extracted.read()
            try:
                contents[_strip_sdist_prefix(member.name)] = data.decode("utf-8")
            except UnicodeDecodeError:
                continue
    return contents


def _strip_sdist_prefix(path: str) -> str:
    return path.split("/", 1)[1] if "/" in path else path
