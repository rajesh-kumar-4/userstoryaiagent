"""OpenAI, Azure OpenAI, and Capgemini Generative Engine chat-completion providers."""

from collections.abc import Sequence
from typing import Any
from urllib.parse import quote

import httpx

from app.core.exceptions import LLMProviderError
from app.core.http import validate_base_url
from app.core.llm.base_provider import ChatMessage, LLMProvider, LLMResponse, response_from_content

OPENAI_DEFAULT_BASE_URL = "https://api.openai.com/v1"
AZURE_DEFAULT_API_VERSION = "2024-06-01"


def _extract_chat_content(payload: dict[str, Any]) -> object:
    choices = payload.get("choices")
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        message = choices[0].get("message")
        if isinstance(message, dict):
            return message.get("content")
    return None


class OpenAIProvider(LLMProvider):
    """OpenAI chat completions (`POST {base_url}/chat/completions`, bearer auth)."""

    name = "openai"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = OPENAI_DEFAULT_BASE_URL,
        timeout_seconds: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("api_key is required")
        super().__init__(model=model, timeout_seconds=timeout_seconds, transport=transport)
        self._api_key = api_key
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
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        payload = self._post_json(self._chat_url(), body, self._headers())
        usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
        return response_from_content(
            provider=self.name,
            model=self.model,
            content=_extract_chat_content(payload),
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
        )

    def _chat_url(self) -> str:
        return f"{self._base_url}/chat/completions"

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}"}


class AzureOpenAIProvider(OpenAIProvider):
    """Azure OpenAI deployments (`POST {endpoint}/openai/deployments/{deployment}/chat/completions`, api-key header)."""

    name = "azure_openai"

    def __init__(
        self,
        *,
        endpoint: str,
        api_key: str,
        deployment: str,
        api_version: str = AZURE_DEFAULT_API_VERSION,
        timeout_seconds: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not deployment:
            raise ValueError("deployment is required")
        super().__init__(
            api_key=api_key,
            model=deployment,
            base_url=endpoint,
            timeout_seconds=timeout_seconds,
            transport=transport,
        )
        self._deployment = deployment
        self._api_version = api_version

    def _chat_url(self) -> str:
        deployment = quote(self._deployment, safe="")
        version = quote(self._api_version, safe="")
        return f"{self._base_url}/openai/deployments/{deployment}/chat/completions?api-version={version}"

    def _headers(self) -> dict[str, str]:
        return {"api-key": self._api_key}


class GenerativeEngineProvider(OpenAIProvider):
    """Capgemini Generative Engine through its OpenAI-compatible chat endpoint.

    Assumption: the tenant exposes `{base_url}/chat/completions` with bearer auth.
    Verify the path and auth scheme against the GE tenant documentation before production use.
    """

    name = "generative_engine"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not base_url:
            raise LLMProviderError("generative_engine requires a base URL")
        super().__init__(
            api_key=api_key,
            model=model,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            transport=transport,
        )
