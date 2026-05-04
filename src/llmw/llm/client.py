from __future__ import annotations

import time
from dataclasses import dataclass

import httpx

from llmw.llm.config import ProviderConfig


@dataclass(frozen=True)
class ChatResult:
    content: str
    model: str
    usage: dict | None = None


class OpenAICompatibleClient:
    def __init__(self, config: ProviderConfig):
        if config.type != "openai_compatible":
            raise ValueError(f"Unsupported provider type: {config.type}")
        self.config = config

    def chat(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        top_p: float | None = None,
        max_tokens: int | None = None,
    ) -> ChatResult:
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        defaults = self.config.generation_defaults
        payload["temperature"] = temperature if temperature is not None else defaults.get("temperature", 0.2)
        payload["top_p"] = top_p if top_p is not None else defaults.get("top_p", 0.8)
        payload["max_tokens"] = max_tokens if max_tokens is not None else defaults.get("max_tokens", 4096)

        return self._post_chat(payload)

    def _post_chat(self, payload: dict) -> ChatResult:
        last_error: Exception | None = None
        url = self.config.base_url.rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.config.api_key()}",
            "Content-Type": "application/json",
        }
        attempts = max(1, self.config.max_retries + 1)
        for attempt in range(attempts):
            try:
                with httpx.Client(timeout=self.config.timeout_seconds) as client:
                    response = client.post(url, headers=headers, json=payload)
                    response.raise_for_status()
                data = response.json()
                choice = data["choices"][0]
                message = choice.get("message") or {}
                content = message.get("content")
                if not isinstance(content, str):
                    raise ValueError("LLM response did not contain choices[0].message.content")
                return ChatResult(content=content, model=str(data.get("model") or self.config.model), usage=data.get("usage"))
            except Exception as exc:
                last_error = exc
                if attempt < attempts - 1:
                    time.sleep(min(2**attempt, 8))
        raise RuntimeError(f"LLM chat request failed: {last_error}") from last_error
