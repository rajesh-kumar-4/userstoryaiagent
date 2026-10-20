"""Ollama chat provider (`POST {base_url}/api/chat`, non-streaming)."""

from collections.abc import Sequence

import httpx

from app.core.http import validate_base_url
from app.core.llm.base_provider import ChatMessage, LLMProvider, LLMResponse, response_from_content

OLLAMA_DEFAULT_BASE_URL = "http://localhost:11434"


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(
        self,
        *,
        model: str,
        base_url: str = OLLAMA_DEFAULT_BASE_URL,
        timeout_seconds: float = 60.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        super().__init__(model=model, timeout_seconds=timeout_seconds, transport=transport)
        self._base_url = validate_base_url(base_url)

    def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 512,
    ) -> LLMResponse:
        body = {
            "model": self.model,
            "messages": self._serialize(messages),
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        payload = self._post_json(f"{self._base_url}/api/chat", body, {})
        message = payload.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        return response_from_content(
            provider=self.name,
            model=self.model,
            content=content,
            prompt_tokens=payload.get("prompt_eval_count"),
            completion_tokens=payload.get("eval_count"),
        )
