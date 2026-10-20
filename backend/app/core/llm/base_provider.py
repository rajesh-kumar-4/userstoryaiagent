"""Provider-neutral contract for chat-completion LLM backends."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from enum import Enum
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field

from app.core.exceptions import LLMProviderError


class LLMProviderName(str, Enum):
    NONE = "none"
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    OLLAMA = "ollama"
    GENERATIVE_ENGINE = "generative_engine"


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1)


class LLMResponse(BaseModel):
    provider: str
    model: str
    content: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


class LLMProvider(ABC):
    """Base class for chat-completion providers. Subclasses implement complete()."""

    name: str = "llm"

    def __init__(
        self,
        *,
        model: str,
        timeout_seconds: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not model:
            raise ValueError("model is required")
        self.model = model
        self._client = httpx.Client(timeout=timeout_seconds, transport=transport)

    def close(self) -> None:
        self._client.close()

    @abstractmethod
    def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 512,
    ) -> LLMResponse:
        """Return one completion for the given chat messages."""

    def _post_json(self, url: str, body: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
        try:
            response = self._client.post(url, json=body, headers=headers)
        except httpx.HTTPError as exc:
            # The URL and headers are deliberately omitted: they may carry credentials.
            raise LLMProviderError(f"{self.name} request failed: {type(exc).__name__}") from exc
        if response.status_code >= 400:
            raise LLMProviderError(f"{self.name} returned HTTP {response.status_code}")
        try:
            payload = response.json()
        except ValueError as exc:
            raise LLMProviderError(f"{self.name} returned a non-JSON body") from exc
        if not isinstance(payload, dict):
            raise LLMProviderError(f"{self.name} returned an unexpected payload")
        return payload

    def _serialize(self, messages: Sequence[ChatMessage]) -> list[dict[str, str]]:
        if not messages:
            raise ValueError("at least one chat message is required")
        return [{"role": message.role, "content": message.content} for message in messages]


def int_or_none(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None


def response_from_content(
    *,
    provider: str,
    model: str,
    content: object,
    prompt_tokens: object = None,
    completion_tokens: object = None,
) -> LLMResponse:
    if not isinstance(content, str) or not content.strip():
        raise LLMProviderError(f"{provider} response did not contain a completion")
    return LLMResponse(
        provider=provider,
        model=model,
        content=content.strip(),
        prompt_tokens=int_or_none(prompt_tokens),
        completion_tokens=int_or_none(completion_tokens),
    )
