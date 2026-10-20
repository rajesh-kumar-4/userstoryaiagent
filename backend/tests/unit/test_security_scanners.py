import base64

import httpx
import pytest

from app.config import Settings
from app.core.exceptions import SecurityIntegrationError
from app.domain.analysis import Severity
from app.integrations.security.base import SecurityFinding
from app.integrations.security.factory import build_security_scanners
from app.integrations.security.sonarqube import SonarQubeScanner
from app.services.security_scan_service import SecurityScanService

SONAR_ISSUES = {
    "issues": [
        {
            "component": "billing:src/App.java",
            "severity": "BLOCKER",
            "message": "SQL built from user input",
            "line": 12,
            "rule": "java:S3649",
        },
        {"component": "billing:pom.xml", "severity": "MINOR", "message": "Unused property", "rule": "xml:1"},
    ]
}


def _transport(*, status: int = 200, body: object = None, seen: list | None = None):
    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        return httpx.Response(status, json=body)

    return httpx.MockTransport(handler)


def test_sonarqube_maps_issues_and_uses_token_basic_auth():
    seen: list[httpx.Request] = []
    scanner = SonarQubeScanner(
        base_url="https://sonar.example.com/",
        token="squ_token",
        transport=_transport(body=SONAR_ISSUES, seen=seen),
    )

    findings = scanner.fetch_findings("billing")

    request = seen[0]
    assert request.url.path == "/api/issues/search"
    assert request.url.params["componentKeys"] == "billing"
    expected_auth = "Basic " + base64.b64encode(b"squ_token:").decode()
    assert request.headers["Authorization"] == expected_auth
    assert findings[0].severity is Severity.CRITICAL
    assert findings[0].file == "src/App.java"
    assert findings[0].line == 12
    assert findings[0].rule == "java:S3649"
    assert findings[1].severity is Severity.LOW
    assert findings[1].line is None


def test_sonarqube_http_error_does_not_leak_the_token():
    scanner = SonarQubeScanner(
        base_url="https://sonar.example.com",
        token="squ_secret",
        transport=_transport(status=500, body={}),
    )

    with pytest.raises(SecurityIntegrationError, match="HTTP 500") as excinfo:
        scanner.fetch_findings("billing")

    assert "squ_secret" not in str(excinfo.value)


def test_sonarqube_rejects_payload_without_issues_list():
    scanner = SonarQubeScanner(base_url="https://sonar.example.com", token="t", transport=_transport(body={}))

    with pytest.raises(SecurityIntegrationError, match="missing 'issues'"):
        scanner.fetch_findings("billing")


def test_sonarqube_requires_token_and_absolute_url():
    with pytest.raises(ValueError, match="token is required"):
        SonarQubeScanner(base_url="https://sonar.example.com", token="")
    with pytest.raises(ValueError, match="absolute http"):
        SonarQubeScanner(base_url="sonar.example.com", token="t")


class _StaticScanner:
    name = "static"

    def __init__(self, findings: list[SecurityFinding]) -> None:
        self._findings = findings
        self.project_keys: list[str] = []

    def fetch_findings(self, project_key: str) -> list[SecurityFinding]:
        self.project_keys.append(project_key)
        return self._findings


class _FailingScanner:
    name = "broken"

    def fetch_findings(self, project_key: str) -> list[SecurityFinding]:
        raise SecurityIntegrationError("broken is unreachable")


def test_failing_scanner_becomes_warning_and_others_still_contribute():
    finding = SecurityFinding(source="static", severity=Severity.HIGH, title="Hardcoded secret")
    service = SecurityScanService([_StaticScanner([finding]), _FailingScanner()])

    result = service.collect("billing-service", "billing")

    assert result.sources == ["static"]
    assert result.warnings == ["broken is unreachable"]
    assert result.findings == [finding]


def test_project_key_mapping_overrides_default_key():
    scanner = _StaticScanner([])
    service = SecurityScanService([scanner], project_keys={"billing-service": "PAY-BILLING"})

    service.collect("billing-service", "billing")

    assert scanner.project_keys == ["PAY-BILLING"]


def test_no_scanners_returns_empty_result():
    result = SecurityScanService([]).collect("billing-service", "billing")

    assert result.findings == []
    assert result.sources == []
    assert result.warnings == []


def test_factory_enables_scanner_only_when_url_and_credentials_are_set():
    assert build_security_scanners(Settings(_env_file=None)) == []

    scanners = build_security_scanners(
        Settings(_env_file=None, sonarqube_url="https://sonar.example.com", sonarqube_token="squ_token")
    )

    assert [scanner.name for scanner in scanners] == ["sonarqube"]
    for scanner in scanners:
        scanner.close()
