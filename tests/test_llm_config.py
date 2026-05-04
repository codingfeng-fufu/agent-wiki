import os

import pytest

from llmw.llm.config import ProviderConfig
from llmw.core.config import ensure_project_dirs
from llmw.core.paths import WikiPaths
from llmw.llm.config import load_env_files


def test_provider_rejects_literal_key_in_api_key_env() -> None:
    config = ProviderConfig(
        type="openai_compatible",
        model="qwen-plus",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key_env="sk-not-an-env-var",
    )

    with pytest.raises(ValueError, match="environment variable name"):
        config.api_key()


def test_provider_reads_api_key_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    config = ProviderConfig(
        type="openai_compatible",
        model="qwen-plus",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key_env="DASHSCOPE_API_KEY",
    )

    assert config.api_key() == os.environ["DASHSCOPE_API_KEY"]


def test_load_env_files_reads_state_env(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    paths = WikiPaths.from_root(tmp_path)
    ensure_project_dirs(paths)
    (paths.state / ".env").write_text('DASHSCOPE_API_KEY="from-file"\n', encoding="utf-8")

    load_env_files(paths)

    assert os.environ["DASHSCOPE_API_KEY"] == "from-file"
