"""Common contract for external security scanners."""

from abc import ABC, abstractmethod
from typing import Any

import httpx
from pydantic import BaseModel

from app.core.exceptions import SecurityIntegrationError
from app.core.http import validate_base_url
from app.domain.analysis import Severity


class SecurityFinding(BaseModel):
    source: str
    severity: Severity
    title: str
    file: str | None = None
    line: int | None = None
    rule: str | None = None


def clip(value: object, limit: int = 300) -> str:
    return str(value or "")[:limit]


def optional_int(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None


class SecurityScanner(ABC):
    name: str = "scanner"

    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._base_url = validate_base_url(base_url)
        self._client = httpx.Client(timeout=timeout_seconds, transport=transport)

    def close(self) -> None:
        self._client.close()

    @abstractmethod
    def fetch_findings(self, project_key: str) -> list[SecurityFinding]:
        """Return open findings for the project. Raises SecurityIntegrationError on failure."""

    def _request_json(
        self,
        method: str,
        url: str,
        *,
        auth: tuple[str, str] | None = None,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        data: dict[str, str] | None = None,
    ) -> Any:
        try:
            response = self._client.request(method, url, auth=auth, headers=headers, params=params, data=data)
        except httpx.HTTPError as exc:
            raise SecurityIntegrationError(f"{self.name} is unreachable: {type(exc).__name__}") from exc
        if response.status_code >= 400:
            raise SecurityIntegrationError(f"{self.name} returned HTTP {response.status_code}")
        try:
            return response.json()
        except ValueError as exc:
            raise SecurityIntegrationError(f"{self.name} returned a non-JSON body") from exc
