from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

_MAX_MANIFEST_BYTES = 512 * 1024
Detector = Callable[[Path], bool]


def _has_file(*names: str) -> Detector:
    return lambda root: any((root / name).is_file() for name in names)


def _manifest_contains(names: tuple[str, ...], needle: str) -> Detector:
    def check(root: Path) -> bool:
        for name in names:
            path = root / name
            try:
                if not path.is_file() or path.stat().st_size > _MAX_MANIFEST_BYTES:
                    continue
                if needle in path.read_text(encoding="utf-8", errors="ignore"):
                    return True
            except OSError:
                continue
        return False

    return check


def _has_top_level_glob(*patterns: str) -> Detector:
    return lambda root: any(next(root.glob(pattern), None) is not None for pattern in patterns)


@dataclass(frozen=True)
class TechnologyDetector:
    tag: str
    detect: Detector


JVM_MANIFESTS = ("pom.xml", "build.gradle", "build.gradle.kts")

DEFAULT_DETECTORS: tuple[TechnologyDetector, ...] = (
    TechnologyDetector("java", _has_file(*JVM_MANIFESTS)),
    TechnologyDetector("maven", _has_file("pom.xml")),
    TechnologyDetector("gradle", _has_file("build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts")),
    TechnologyDetector("spring-boot", _manifest_contains(JVM_MANIFESTS, "spring-boot")),
    TechnologyDetector("nodejs", _has_file("package.json")),
    TechnologyDetector("react", _manifest_contains(("package.json",), '"react"')),
    TechnologyDetector("angular", _has_file("angular.json")),
    TechnologyDetector("python", _has_file("pyproject.toml", "requirements.txt", "setup.py", "setup.cfg")),
    TechnologyDetector("dotnet", _has_top_level_glob("*.csproj", "*.sln")),
    TechnologyDetector("go", _has_file("go.mod")),
)


def detect_technologies(root: Path, detectors: Sequence[TechnologyDetector] = DEFAULT_DETECTORS) -> list[str]:
    return sorted(detector.tag for detector in detectors if detector.detect(root))
