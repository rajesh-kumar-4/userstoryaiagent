"""Builds security scanners from settings. A scanner is enabled only when its URL and credentials are set."""

from app.config import Settings
from app.integrations.security.base import SecurityScanner
from app.integrations.security.checkmarx import CheckmarxScanner
from app.integrations.security.sonarqube import SonarQubeScanner
from app.integrations.security.sonatype import SonatypeScanner


def build_security_scanners(settings: Settings) -> list[SecurityScanner]:
    timeout = settings.security_timeout_seconds
    scanners: list[SecurityScanner] = []
    if settings.sonarqube_url and settings.sonarqube_token:
        scanners.append(
            SonarQubeScanner(
                base_url=settings.sonarqube_url,
                token=settings.sonarqube_token.get_secret_value(),
                timeout_seconds=timeout,
            )
        )
    if settings.checkmarx_url and settings.checkmarx_tenant and settings.checkmarx_refresh_token:
        scanners.append(
            CheckmarxScanner(
                base_url=settings.checkmarx_url,
                tenant=settings.checkmarx_tenant,
                refresh_token=settings.checkmarx_refresh_token.get_secret_value(),
                iam_url=settings.checkmarx_iam_url,
                timeout_seconds=timeout,
            )
        )
    if settings.sonatype_url and settings.sonatype_username and settings.sonatype_token:
        scanners.append(
            SonatypeScanner(
                base_url=settings.sonatype_url,
                username=settings.sonatype_username,
                token=settings.sonatype_token.get_secret_value(),
                timeout_seconds=timeout,
            )
        )
    return scanners
