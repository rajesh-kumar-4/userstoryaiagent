from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.llm.base_provider import LLMProviderName
from app.core.security.rbac import Role
from app.domain.models import MonitorMode

PLATFORM_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_IGNORED_DIRECTORIES = [
    "node_modules",
    "target",
    "build",
    "dist",
    "out",
    "bin",
    "obj",
    "venv",
    "__pycache__",
    ".gradle",
    ".mvn",
]

DEFAULT_WATCH_PATTERNS = [
    "src/**",
    "**/pom.xml",
    "**/build.gradle",
    "**/build.gradle.kts",
    "**/package.json",
    "**/application*.yml",
    "**/application*.yaml",
    "**/application*.properties",
    "**/requirements*.txt",
    "**/pyproject.toml",
    "**/go.mod",
]


def _default_workspace_root() -> Path:
    return PLATFORM_ROOT.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    workspace_root: Path = Field(default_factory=_default_workspace_root)
    platform_root: Path = Field(default=PLATFORM_ROOT)
    max_discovery_depth: int = Field(default=2, ge=1, le=8)
    ignored_directories: list[str] = Field(default_factory=lambda: list(DEFAULT_IGNORED_DIRECTORIES))
    watch_patterns: list[str] = Field(default_factory=lambda: list(DEFAULT_WATCH_PATTERNS))
    monitor_mode: MonitorMode = MonitorMode.MANUAL
    monitor_interval_seconds: float = Field(default=30.0, ge=1.0)
    monitor_debounce_seconds: float = Field(default=5.0, ge=0.0)
    event_history_size: int = Field(default=500, ge=10)
    log_level: str = "INFO"

    # Authentication and RBAC. When disabled (local development), every request runs as ADMIN.
    # API_KEYS is a JSON object of key -> role, for example {"key-abc": "ANALYST"}.
    auth_enabled: bool = False
    api_keys: dict[str, Role] = Field(default_factory=dict)

    # Analysis
    analysis_history_size: int = Field(default=1000, ge=10)

    # LLM provider. NONE disables narrative generation and uses rule-based summaries.
    llm_provider: LLMProviderName = LLMProviderName.NONE
    llm_model: str | None = None
    llm_base_url: str | None = None
    llm_api_key: SecretStr | None = None
    llm_timeout_seconds: float = Field(default=30.0, ge=1.0, le=300.0)
    llm_azure_deployment: str | None = None
    llm_azure_api_version: str = "2024-06-01"

    # Security integrations. Each scanner is enabled only when its URL and credentials are set.
    security_timeout_seconds: float = Field(default=10.0, ge=1.0, le=120.0)
    security_project_keys: dict[str, str] = Field(default_factory=dict)
    sonarqube_url: str | None = None
    sonarqube_token: SecretStr | None = None
    checkmarx_url: str | None = None
    checkmarx_iam_url: str | None = None
    checkmarx_tenant: str | None = None
    checkmarx_refresh_token: SecretStr | None = None
    sonatype_url: str | None = None
    sonatype_username: str | None = None
    sonatype_token: SecretStr | None = None

    # OpenTelemetry
    telemetry_enabled: bool = False
    otel_service_name: str = "userstoryai-platform"
    otel_exporter_otlp_endpoint: str | None = None

    # RAG and agents. Chroma runs in-process (PersistentClient) unless CHROMA_HOST is set.
    chroma_path: Path | None = None
    chroma_host: str | None = None
    chroma_port: int = Field(default=8000, ge=1, le=65535)
    rag_sources_dir: Path | None = None
    agent_run_history_size: int = Field(default=200, ge=10)


@lru_cache
def get_settings() -> Settings:
    return Settings()
