"""Checkmarx One client: refresh-token exchange, then `api/results` for a project.

Assumption: the endpoints and response shape follow the Checkmarx One REST API
(IAM token exchange plus `/api/results?project-id=`). Validate against the tenant before use.
"""

from typing import Any
from urllib.parse import quote

import httpx

from app.core.exceptions import SecurityIntegrationError
from app.core.http import validate_base_url
from app.domain.analysis import Severity
from app.integrations.security.base import SecurityFinding, SecurityScanner, clip, optional_int

_SEVERITY_MAP = {
    "CRITICAL": Severity.CRITICAL,
    "HIGH": Severity.HIGH,
    "MEDIUM": Severity.MEDIUM,
    "LOW": Severity.LOW,
    "INFO": Severity.LOW,
}


class CheckmarxScanner(SecurityScanner):
    name = "checkmarx"

    def __init__(
        self,
        *,
        base_url: str,
        tenant: str,
        refresh_token: str,
        iam_url: str | None = None,
        timeout_seconds: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not tenant or not refresh_token:
            raise ValueError("tenant and refresh_token are required")
        super().__init__(base_url=base_url, timeout_seconds=timeout_seconds, transport=transport)
        self._iam_url = validate_base_url(iam_url or base_url)
        self._tenant = tenant
        self._refresh_token = refresh_token

    def fetch_findings(self, project_key: str) -> list[SecurityFinding]:
        access_token = self._access_token()
        payload = self._request_json(
            "GET",
            f"{self._base_url}/api/results",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"project-id": project_key, "limit": "500"},
        )
        items: Any = payload.get("results") if isinstance(payload, dict) else payload
        if not isinstance(items, list):
            raise SecurityIntegrationError("checkmarx response is missing 'results'")

        findings: list[SecurityFinding] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            file_name, line = _first_location(item)
            findings.append(
                SecurityFinding(
                    source=self.name,
                    severity=_SEVERITY_MAP.get(str(item.get("severity", "")).upper(), Severity.LOW),
                    title=clip(item.get("queryName") or item.get("description")) or "Checkmarx finding",
                    file=file_name,
                    line=line,
                    rule=clip(item.get("queryId"), 120) or None,
                )
            )
        return findings

    def _access_token(self) -> str:
        payload = self._request_json(
            "POST",
            f"{self._iam_url}/auth/realms/{quote(self._tenant, safe='')}/protocol/openid-connect/token",
            data={
                "grant_type": "refresh_token",
                "client_id": "ast-app",
                "refresh_token": self._refresh_token,
            },
        )
        token = payload.get("access_token") if isinstance(payload, dict) else None
        if not isinstance(token, str) or not token:
            raise SecurityIntegrationError("checkmarx token exchange returned no access token")
        return token


def _first_location(item: dict[str, Any]) -> tuple[str | None, int | None]:
    data = item.get("data")
    nodes = data.get("nodes") if isinstance(data, dict) else None
    if isinstance(nodes, list) and nodes and isinstance(nodes[0], dict):
        file_name = clip(nodes[0].get("fileName"), 500) or None
        return file_name, optional_int(nodes[0].get("line"))
    return None, None
