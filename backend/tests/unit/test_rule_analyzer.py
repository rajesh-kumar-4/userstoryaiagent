from app.domain.analysis import Finding, Severity
from app.domain.models import AnalysisMode, ChangeArea, ChangedFile, ChangeSet, ChangeType
from app.services.rule_analyzer import RuleBasedAnalyzer, score_findings


def _file(path: str, change_type: ChangeType = ChangeType.MODIFIED, added: int = 1) -> ChangedFile:
    return ChangedFile(
        path=path,
        change_type=change_type,
        area=ChangeArea.UNSTAGED,
        added_lines=added,
    )


def _change_set(*files: ChangedFile) -> ChangeSet:
    return ChangeSet(repository="billing-service", analysis_mode=AnalysisMode.PRE_COMMIT, files=list(files))


def _categories(findings: list[Finding]) -> dict[str, Finding]:
    return {finding.category: finding for finding in findings}


def test_empty_change_set_has_no_findings():
    assert RuleBasedAnalyzer().analyze(_change_set()) == []


def test_configuration_and_dependency_changes_are_flagged():
    findings = RuleBasedAnalyzer().analyze(
        _change_set(_file("pom.xml"), _file("src/main/resources/application.yml"))
    )

    by_category = _categories(findings)
    assert by_category["dependency_change"].severity is Severity.MEDIUM
    assert by_category["configuration_change"].severity is Severity.HIGH


def test_sensitive_looking_file_is_high_severity():
    findings = RuleBasedAnalyzer().analyze(_change_set(_file("config/db-password.txt")))

    assert _categories(findings)["sensitive_file"].severity is Severity.HIGH


def test_deleted_file_is_medium_severity():
    findings = RuleBasedAnalyzer().analyze(_change_set(_file("src/Old.java", ChangeType.DELETED)))

    assert _categories(findings)["deleted_file"].severity is Severity.MEDIUM


def test_source_change_without_tests_is_flagged_and_cleared_by_test_change():
    analyzer = RuleBasedAnalyzer()

    without_tests = analyzer.analyze(_change_set(_file("src/main/App.java")))
    with_tests = analyzer.analyze(_change_set(_file("src/main/App.java"), _file("src/test/AppTest.java")))

    assert "missing_tests" in _categories(without_tests)
    assert "missing_tests" not in _categories(with_tests)


def test_large_change_threshold_is_configurable():
    change_set = _change_set(_file("docs/a.md"), _file("docs/b.md"))

    assert "large_change" not in _categories(RuleBasedAnalyzer().analyze(change_set))
    assert "large_change" in _categories(RuleBasedAnalyzer(large_file_threshold=2).analyze(change_set))


def test_score_is_capped_at_one_hundred():
    findings = [
        Finding(finding_id=f"f{index}", category="security", severity=Severity.CRITICAL, title="t")
        for index in range(5)
    ]

    assert score_findings(findings) == 100
    assert score_findings([]) == 0
