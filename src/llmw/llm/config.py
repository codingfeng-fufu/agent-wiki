from __future__ import annotations

import json
import os
import re
from pathlib import Path

from pydantic import BaseModel, Field

from llmw.core.paths import WikiPaths


ENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class UsageConfig(BaseModel):
    system_prompt_file: str
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None


class ProviderConfig(BaseModel):
    type: str
    vendor: str = ""
    model: str
    base_url: str
    api_key_env: str
    timeout_seconds: float = 120
    max_retries: int = 2
    generation_defaults: dict[str, float | int] = Field(default_factory=dict)
    usage: dict[str, UsageConfig] = Field(default_factory=dict)

    def api_key(self) -> str:
        if not ENV_NAME_RE.match(self.api_key_env):
            raise ValueError(
                "`api_key_env` must be an environment variable name, not a literal API key."
            )
        key = os.environ.get(self.api_key_env)
        if not key:
            raise ValueError(f"Missing environment variable: {self.api_key_env}")
        return key


class ProviderRegistry(BaseModel):
    default_provider: str
    providers: dict[str, ProviderConfig]

    def get(self, name: str | None = None) -> ProviderConfig:
        provider_name = name or self.default_provider
        try:
            return self.providers[provider_name]
        except KeyError as exc:
            raise KeyError(f"Unknown provider: {provider_name}") from exc


def default_provider_config_path(paths: WikiPaths) -> Path:
    return paths.system / "providers" / "qwen-plus.json"


def load_provider_registry(paths: WikiPaths, config_path: Path | None = None) -> ProviderRegistry:
    load_env_files(paths)
    path = config_path or default_provider_config_path(paths)
    if not path.exists():
        raise FileNotFoundError(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    return ProviderRegistry.model_validate(data)


def load_system_prompt(paths: WikiPaths, usage: UsageConfig) -> str:
    prompt_path = paths.root / usage.system_prompt_file
    if not prompt_path.exists():
        raise FileNotFoundError(prompt_path)
    return prompt_path.read_text(encoding="utf-8")


def load_env_files(paths: WikiPaths) -> None:
    for env_path in [paths.root / ".env", paths.state / ".env"]:
        if not env_path.exists():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            key = key.strip()
            if not ENV_NAME_RE.match(key):
                continue
            os.environ.setdefault(key, _clean_env_value(value.strip()))


def _clean_env_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value
