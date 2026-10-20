"""SonarQube client using the `api/issues/search` endpoint (token auth, token as username)."""

import httpx

from app.core.exceptions import SecurityIntegrationError
from app.domain.analysis import Severity
from app.integrations.security.base import SecurityFinding, SecurityScanner, clip, optional_int

_SEVERITY_MAP = {
    "BLOCKER": Severity.CRITICAL,
    "CRITICAL": Severity.HIGH,
    "MAJOR": Severity.MEDIUM,
    "MINOR": Severity.LOW,
    "INFO": Severity.LOW,
}


class SonarQubeScanner(SecurityScanner):
    name = "sonarqube"

    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        timeout_seconds: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not token:
            raise ValueError("token is required")
        super().__init__(base_url=base_url, timeout_seconds=timeout_seconds, transport=transport)
        self._token = token

    def fetch_findings(self, project_key: str) -> list[SecurityFinding]:
        payload = self._request_json(
            "GET",
            f"{self._base_url}/api/issues/search",
            auth=(self._token, ""),
            params={
                "componentKeys": project_key,
                "resolved": "false",
                "types": "BUG,VULNERABILITY",
                "ps": "500",
            },
        )
        issues = payload.get("issues") if isinstance(payload, dict) else None
        if not isinstance(issues, list):
            raise SecurityIntegrationError("sonarqube response is missing 'issues'")

        findings: list[SecurityFinding] = []
        for issue in issues:
            if not isinstance(issue, dict):
                continue
            component = str(issue.get("component") or "")
            path = component.split(":", 1)[1] if ":" in component else (component or None)
            findings.append(
                SecurityFinding(
                    source=self.name,
                    severity=_SEVERITY_MAP.get(str(issue.get("severity", "")).upper(), Severity.LOW),
                    title=clip(issue.get("message")) or "SonarQube issue",
                    file=path,
                    line=optional_int(issue.get("line")),
                    rule=clip(issue.get("rule"), 120) or None,
                )
            )
        return findings
