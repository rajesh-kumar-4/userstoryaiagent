"""Aggregates findings from configured security scanners. A failing scanner becomes a warning, not an error."""

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field

from app.core.exceptions import SecurityIntegrationError
from app.integrations.security.base import SecurityFinding, SecurityScanner

logger = logging.getLogger(__name__)


@dataclass
class SecurityScanResult:
    findings: list[SecurityFinding] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class SecurityScanService:
    def __init__(self, scanners: Sequence[SecurityScanner], project_keys: dict[str, str] | None = None) -> None:
        self._scanners = list(scanners)
        self._project_keys = dict(project_keys or {})

    @property
    def scanner_names(self) -> list[str]:
        return [scanner.name for scanner in self._scanners]

    def collect(self, repository_id: str, default_key: str) -> SecurityScanResult:
        if not self._scanners:
            return SecurityScanResult()
        project_key = self._project_keys.get(repository_id, default_key)
        result = SecurityScanResult()
        for scanner in self._scanners:
            try:
                result.findings.extend(scanner.fetch_findings(project_key))
                result.sources.append(scanner.name)
            except SecurityIntegrationError as exc:
                logger.warning("security scanner %s unavailable: %s", scanner.name, exc)
                result.warnings.append(str(exc))
        return result
