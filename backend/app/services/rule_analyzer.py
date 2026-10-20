"""Deterministic change-risk rules. These run without an LLM and are the baseline for the agent workflow."""

from pathlib import PurePosixPath

from app.domain.analysis import SEVERITY_WEIGHTS, Finding, Severity
from app.domain.models import ChangeSet, ChangeType

DEPENDENCY_MANIFESTS = frozenset(
    {
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
        "package.json",
        "package-lock.json",
        "requirements.txt",
        "pyproject.toml",
        "pipfile",
        "go.mod",
        "go.sum",
        "cargo.toml",
    }
)
SOURCE_SUFFIXES = frozenset({".java", ".kt", ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".cs", ".rb", ".rs", ".scala"})
SENSITIVE_HINTS = ("secret", "credential", "password", "private-key", "keystore", ".pem", ".p12", ".key")
CONFIG_SUFFIXES = frozenset({".yml", ".yaml", ".properties", ".json"})


def score_findings(findings: list[Finding]) -> int:
    return min(100, sum(SEVERITY_WEIGHTS[finding.severity] for finding in findings))


def _is_configuration(name: str) -> bool:
    if name == "dockerfile" or name.startswith((".env", "docker-compose")):
        return True
    stem, _, suffix = name.rpartition(".")
    return bool(stem) and name.startswith(("application", "appsettings")) and f".{suffix}" in CONFIG_SUFFIXES


def is_test_path(path: str) -> bool:
    pure = PurePosixPath(path.lower())
    name = pure.name
    in_test_dir = any(part in ("test", "tests", "__tests__") for part in pure.parts[:-1])
    return (
        in_test_dir
        or name.startswith("test_")
        or ".test." in name
        or ".spec." in name
        or name.endswith(("_test.py", "_test.go", "test.java", "tests.java"))
    )


class RuleBasedAnalyzer:
    def __init__(self, *, large_file_threshold: int = 25, large_line_threshold: int = 500) -> None:
        self._large_file_threshold = large_file_threshold
        self._large_line_threshold = large_line_threshold

    def analyze(self, change_set: ChangeSet) -> list[Finding]:
        findings: dict[str, Finding] = {}

        def add(finding: Finding) -> None:
            findings.setdefault(finding.finding_id, finding)

        source_changed = False
        tests_changed = False
        for change in change_set.files:
            path = change.path
            pure = PurePosixPath(path)
            name = pure.name.lower()

            if change.change_type is ChangeType.DELETED:
                add(
                    Finding(
                        finding_id=f"deleted_file:{path}",
                        category="deleted_file",
                        severity=Severity.MEDIUM,
                        title=f"File deleted: {path}",
                        file=path,
                    )
                )
            if name in DEPENDENCY_MANIFESTS:
                add(
                    Finding(
                        finding_id=f"dependency_change:{path}",
                        category="dependency_change",
                        severity=Severity.MEDIUM,
                        title=f"Dependency manifest changed: {path}",
                        file=path,
                    )
                )
            if _is_configuration(name):
                add(
                    Finding(
                        finding_id=f"configuration_change:{path}",
                        category="configuration_change",
                        severity=Severity.HIGH,
                        title=f"Configuration changed: {path}",
                        file=path,
                    )
                )
            if any(hint in path.lower() for hint in SENSITIVE_HINTS):
                add(
                    Finding(
                        finding_id=f"sensitive_file:{path}",
                        category="sensitive_file",
                        severity=Severity.HIGH,
                        title=f"Sensitive-looking file changed: {path}",
                        file=path,
                    )
                )

            if is_test_path(path):
                tests_changed = True
            elif pure.suffix.lower() in SOURCE_SUFFIXES:
                source_changed = True

        totals = change_set.totals
        changed_lines = totals["added_lines"] + totals["deleted_lines"] + totals["modified_lines"]
        if totals["files_changed"] >= self._large_file_threshold or changed_lines >= self._large_line_threshold:
            add(
                Finding(
                    finding_id="large_change",
                    category="large_change",
                    severity=Severity.MEDIUM,
                    title="Large change set",
                    detail=f"{totals['files_changed']} files and {changed_lines} changed lines",
                )
            )
        if source_changed and not tests_changed:
            add(
                Finding(
                    finding_id="missing_tests",
                    category="missing_tests",
                    severity=Severity.LOW,
                    title="Source changed without accompanying test changes",
                )
            )
        return list(findings.values())
