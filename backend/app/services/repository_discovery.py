from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from app.domain.models import RepositoryRecord, utc_now
from app.services.technology_detection import DEFAULT_DETECTORS, TechnologyDetector, detect_technologies
from app.services.workspace_scanner import WorkspaceScanner

CODEOWNERS_LOCATIONS = (".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS")


def read_codeowners(root: Path) -> list[str]:
    for relative in CODEOWNERS_LOCATIONS:
        path = root / relative
        if not path.is_file():
            continue
        owners: list[str] = []
        for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            parts = raw.split()
            if len(parts) > 1 and parts[0] == "*":
                owners = parts[1:]
        return owners
    return []


class RepositoryDiscoveryEngine:
    def __init__(
        self,
        scanner: WorkspaceScanner,
        detectors: Sequence[TechnologyDetector] = DEFAULT_DETECTORS,
    ) -> None:
        self._scanner = scanner
        self._detectors = tuple(detectors)

    @property
    def root(self) -> Path:
        return self._scanner.root

    def discover(self) -> list[RepositoryRecord]:
        return [self.build_record(path) for path in self._scanner.scan()]

    def build_record(self, path: Path) -> RepositoryRecord:
        resolved = path.resolve()
        return RepositoryRecord(
            id=resolved.relative_to(self.root).as_posix(),
            name=resolved.name,
            path=str(resolved),
            technology_tags=detect_technologies(resolved, self._detectors),
            owners=read_codeowners(resolved),
            discovered_at=utc_now(),
        )
