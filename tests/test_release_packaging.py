from __future__ import annotations

import json
import shutil
import subprocess
import tarfile
from pathlib import Path

import pytest

from llmw.release import _secret_value_violations


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
        assert not _secret_value_violations(path, content)


def test_secret_value_scan_flags_common_provider_keys() -> None:
    openai_env = "OPENAI" + "_API_KEY"
    anthropic_env = "ANTHROPIC" + "_API_KEY"
    openai_key = "sk-" + "live-secret"
    anthropic_key = "real-" + "secret-value"
    assert _secret_value_violations("config.txt", f'{openai_env}="{openai_key}"\n')
    assert _secret_value_violations("config.txt", f'{anthropic_env}: "{anthropic_key}"\n')
    assert not _secret_value_violations("config.txt", "DASHSCOPE_API_KEY=your-dashscope-api-key\n")
    assert not _secret_value_violations("test.py", 'env["MOCK_LLM_API_KEY"] = "mock-placeholder-key"\n')


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
