import json

import httpx
import pytest

from app.config import Settings
from app.core.exceptions import ConfigurationError, LLMProviderError
from app.core.llm.base_provider import ChatMessage, LLMProviderName
from app.core.llm.openai_provider import AzureOpenAIProvider, GenerativeEngineProvider, OpenAIProvider
from app.core.llm.provider_factory import create_llm_provider

MESSAGES = [
    ChatMessage(role="system", content="You are a reviewer."),
    ChatMessage(role="user", content="Summarize the change."),
]

CHAT_BODY = {
    "choices": [{"message": {"role": "assistant", "content": "  Risk is moderate.  "}}],
    "usage": {"prompt_tokens": 12, "completion_tokens": 4},
}


def _transport(*, status: int = 200, body: object = None, text: str | None = None, seen: list | None = None):
    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        if text is not None:
            return httpx.Response(status, text=text)
        return httpx.Response(status, json=body)

    return httpx.MockTransport(handler)


def test_openai_sends_bearer_auth_and_parses_completion():
    seen: list[httpx.Request] = []
    provider = OpenAIProvider(api_key="sk-test", model="gpt-test", transport=_transport(body=CHAT_BODY, seen=seen))

    response = provider.complete(MESSAGES, temperature=0.1, max_tokens=64)

    request = seen[0]
    assert str(request.url) == "https://api.openai.com/v1/chat/completions"
    assert request.headers["Authorization"] == "Bearer sk-test"
    sent = json.loads(request.content)
    assert sent["model"] == "gpt-test"
    assert sent["messages"][0] == {"role": "system", "content": "You are a reviewer."}
    assert sent["max_tokens"] == 64
    assert response.provider == "openai"
    assert response.content == "Risk is moderate."
    assert response.prompt_tokens == 12
    assert response.completion_tokens == 4


def test_azure_uses_deployment_path_and_api_key_header():
    seen: list[httpx.Request] = []
    provider = AzureOpenAIProvider(
        endpoint="https://contoso.openai.azure.com",
        api_key="az-key",
        deployment="gpt-4o-mini",
        transport=_transport(body=CHAT_BODY, seen=seen),
    )

    provider.complete(MESSAGES)

    request = seen[0]
    assert request.url.path == "/openai/deployments/gpt-4o-mini/chat/completions"
    assert request.url.params["api-version"] == "2024-06-01"
    assert request.headers["api-key"] == "az-key"
    assert "Authorization" not in request.headers


def test_generative_engine_posts_to_chat_completions_under_base_url():
    seen: list[httpx.Request] = []
    provider = GenerativeEngineProvider(
        base_url="https://ge.example.com/api",
        api_key="ge-key",
        model="ge-model",
        transport=_transport(body=CHAT_BODY, seen=seen),
    )

    response = provider.complete(MESSAGES)

    assert str(seen[0].url) == "https://ge.example.com/api/chat/completions"
    assert response.provider == "generative_engine"


def test_http_error_is_raised_without_leaking_the_api_key():
    provider = OpenAIProvider(
        api_key="sk-secret-value",
        model="gpt-test",
        transport=_transport(status=401, body={"error": "invalid"}),
    )

    with pytest.raises(LLMProviderError) as excinfo:
        provider.complete(MESSAGES)

    assert "HTTP 401" in str(excinfo.value)
    assert "sk-secret-value" not in str(excinfo.value)


def test_transport_failure_is_wrapped_without_url_or_credentials():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused for sk-secret-value")

    provider = OpenAIProvider(api_key="sk-secret-value", model="gpt-test", transport=httpx.MockTransport(handler))

    with pytest.raises(LLMProviderError, match="request failed: ConnectError") as excinfo:
        provider.complete(MESSAGES)

    assert "sk-secret-value" not in str(excinfo.value)


def test_non_json_and_empty_completions_are_rejected():
    non_json = OpenAIProvider(api_key="k", model="m", transport=_transport(text="not json"))
    empty = OpenAIProvider(
        api_key="k",
        model="m",
        transport=_transport(body={"choices": [{"message": {"content": "   "}}]}),
    )

    with pytest.raises(LLMProviderError, match="non-JSON"):
        non_json.complete(MESSAGES)
    with pytest.raises(LLMProviderError, match="did not contain a completion"):
        empty.complete(MESSAGES)


def test_constructors_validate_required_values():
    with pytest.raises(ValueError, match="api_key is required"):
        OpenAIProvider(api_key="", model="m")
    with pytest.raises(ValueError, match="deployment is required"):
        AzureOpenAIProvider(endpoint="https://contoso.openai.azure.com", api_key="k", deployment="")
    with pytest.raises(ValueError, match="Base URL must be an absolute"):
        OpenAIProvider(api_key="k", model="m", base_url="ftp://example.com")


def test_factory_returns_none_when_no_provider_is_configured():
    assert create_llm_provider(Settings(_env_file=None, llm_provider=LLMProviderName.NONE)) is None


def test_factory_requires_credentials_for_hosted_providers():
    settings = Settings(_env_file=None, llm_provider=LLMProviderName.OPENAI)

    with pytest.raises(ConfigurationError, match="LLM_API_KEY is required"):
        create_llm_provider(settings)


def test_factory_builds_openai_provider_when_configured():
    settings = Settings(
        _env_file=None,
        llm_provider=LLMProviderName.OPENAI,
        llm_api_key="sk-configured",
        llm_model="gpt-test",
    )

    provider = create_llm_provider(settings)

    assert isinstance(provider, OpenAIProvider)
    assert provider.model == "gpt-test"
    provider.close()
