"""Builds the configured LLM provider from settings. Returns None when no provider is configured."""

from app.config import Settings
from app.core.exceptions import ConfigurationError
from app.core.llm.base_provider import LLMProvider, LLMProviderName
from app.core.llm.ollama_provider import OLLAMA_DEFAULT_BASE_URL, OllamaProvider
from app.core.llm.openai_provider import (
    OPENAI_DEFAULT_BASE_URL,
    AzureOpenAIProvider,
    GenerativeEngineProvider,
    OpenAIProvider,
)


def create_llm_provider(settings: Settings) -> LLMProvider | None:
    name = settings.llm_provider
    if name is LLMProviderName.NONE:
        return None

    api_key = settings.llm_api_key.get_secret_value() if settings.llm_api_key else ""
    timeout = settings.llm_timeout_seconds

    if name is LLMProviderName.OPENAI:
        _require(api_key, "LLM_API_KEY", name)
        _require(settings.llm_model, "LLM_MODEL", name)
        return OpenAIProvider(
            api_key=api_key,
            model=settings.llm_model or "",
            base_url=settings.llm_base_url or OPENAI_DEFAULT_BASE_URL,
            timeout_seconds=timeout,
        )

    if name is LLMProviderName.AZURE_OPENAI:
        _require(api_key, "LLM_API_KEY", name)
        _require(settings.llm_base_url, "LLM_BASE_URL (the Azure endpoint)", name)
        _require(settings.llm_azure_deployment, "LLM_AZURE_DEPLOYMENT", name)
        return AzureOpenAIProvider(
            endpoint=settings.llm_base_url or "",
            api_key=api_key,
            deployment=settings.llm_azure_deployment or "",
            api_version=settings.llm_azure_api_version,
            timeout_seconds=timeout,
        )

    if name is LLMProviderName.OLLAMA:
        _require(settings.llm_model, "LLM_MODEL", name)
        return OllamaProvider(
            model=settings.llm_model or "",
            base_url=settings.llm_base_url or OLLAMA_DEFAULT_BASE_URL,
            timeout_seconds=timeout,
        )

    _require(settings.llm_base_url, "LLM_BASE_URL", name)
    _require(api_key, "LLM_API_KEY", name)
    _require(settings.llm_model, "LLM_MODEL", name)
    return GenerativeEngineProvider(
        base_url=settings.llm_base_url or "",
        api_key=api_key,
        model=settings.llm_model or "",
        timeout_seconds=timeout,
    )


def _require(value: str | None, setting: str, provider: LLMProviderName) -> None:
    if not value:
        raise ConfigurationError(f"{setting} is required when LLM_PROVIDER={provider.value}")
