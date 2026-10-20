"""Sonatype Nexus IQ client: latest application report, policy violations mapped by threat level.

Assumption: the report contains a `policyViolations` list with `threatLevel` (0-10).
Validate the path and payload against the IQ Server version in use before production use.
"""

from urllib.parse import quote

import httpx

from app.core.exceptions import SecurityIntegrationError
from app.domain.analysis import Severity
from app.integrations.security.base import SecurityFinding, SecurityScanner, clip, optional_int


def _severity_for_threat(level: int | None) -> Severity:
    if level is None:
        return Severity.LOW
    if level >= 9:
        return Severity.CRITICAL
    if level >= 7:
        return Severity.HIGH
    if level >= 4:
        return Severity.MEDIUM
    return Severity.LOW


class SonatypeScanner(SecurityScanner):
    name = "sonatype"

    def __init__(
        self,
        *,
        base_url: str,
        username: str,
        token: str,
        timeout_seconds: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not username or not token:
            raise ValueError("username and token are required")
        super().__init__(base_url=base_url, timeout_seconds=timeout_seconds, transport=transport)
        self._auth = (username, token)

    def fetch_findings(self, project_key: str) -> list[SecurityFinding]:
        payload = self._request_json(
            "GET",
            f"{self._base_url}/api/v2/applications/{quote(project_key, safe='')}/reports/latest",
            auth=self._auth,
        )
        violations = payload.get("policyViolations") if isinstance(payload, dict) else None
        if not isinstance(violations, list):
            raise SecurityIntegrationError("sonatype response is missing 'policyViolations'")

        findings: list[SecurityFinding] = []
        for violation in violations:
            if not isinstance(violation, dict):
                continue
            policy = clip(violation.get("policyName"), 120) or "Policy violation"
            component = clip(violation.get("componentName"), 200) or "component"
            findings.append(
                SecurityFinding(
                    source=self.name,
                    severity=_severity_for_threat(optional_int(violation.get("threatLevel"))),
                    title=f"{policy}: {component}",
                    rule=policy,
                )
            )
        return findings
