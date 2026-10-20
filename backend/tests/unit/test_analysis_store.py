from datetime import datetime, timezone

from app.domain.analysis import AnalysisReport, Finding, Severity
from app.domain.models import AnalysisMode
from app.services.analysis_store import AnalysisStore
from app.services.similarity import query_coverage, tokenize


def _report(**overrides) -> AnalysisReport:
    values = {
        "repository": "billing-service",
        "analysis_mode": AnalysisMode.POST_COMMIT,
        "commit_id": "abcdef1234567890",
        "target_sha": "abcdef1234567890",
        "risk_score": 10,
        "risk_level": Severity.LOW,
        "summary": "Configuration changed in application yml",
        "summary_source": "rule_based",
    }
    values.update(overrides)
    return AnalysisReport(**values)


def test_find_by_commit_matches_sha_prefix_case_insensitively():
    store = AnalysisStore()
    report = _report()
    store.add(report)

    assert store.find_by_commit("ABCDEF12") is report
    assert store.find_by_commit("abc") is None
    assert store.find_by_commit("ffff") is None


def test_store_is_bounded_and_keeps_most_recent_entries():
    store = AnalysisStore(max_entries=10)
    for index in range(12):
        store.add(_report(summary=f"change {index}"))

    summaries = [report.summary for report in store.snapshot()]

    assert len(summaries) == 10
    assert summaries[0] == "change 2"
    assert summaries[-1] == "change 11"


def test_latest_for_returns_newest_report_of_repository():
    store = AnalysisStore()
    older = _report(generated_at=datetime(2024, 1, 1, tzinfo=timezone.utc))
    newer = _report(generated_at=datetime(2024, 1, 2, tzinfo=timezone.utc))
    store.add(newer)
    store.add(older)

    assert store.latest_for("billing-service") is newer
    assert store.latest_for("unknown") is None


def test_search_ranks_by_term_coverage_and_filters_by_repository():
    store = AnalysisStore()
    store.add(_report(summary="Configuration changed in application yml"))
    store.add(
        _report(
            repository="frontend/web-app",
            summary="Unrelated styling update",
            commit_id=None,
            target_sha=None,
        )
    )

    matches = store.search("application configuration", top_k=5)
    scoped = store.search("application configuration", repository="frontend/web-app")

    assert len(matches) == 1
    assert matches[0].repository == "billing-service"
    assert matches[0].similarity == 1.0
    assert {"application", "configuration"} <= set(matches[0].matched_terms)
    assert scoped == []


def test_search_uses_finding_titles_and_changed_files():
    store = AnalysisStore()
    report = _report(
        summary="Rule summary",
        changed_files=["src/main/resources/application.yml"],
        findings=[
            Finding(
                finding_id="configuration_change:src/main/resources/application.yml",
                category="configuration_change",
                severity=Severity.HIGH,
                title="Configuration changed: src/main/resources/application.yml",
            )
        ],
    )
    store.add(report)

    matches = store.search("application yml")

    assert [match.analysis_id for match in matches] == [report.analysis_id]


def test_similarity_helpers():
    assert tokenize("Hello, World-2!") == frozenset({"hello", "world"})
    assert query_coverage(frozenset(), ["anything"]) == 0.0
    assert query_coverage(frozenset({"a1", "b2"}), ["a1"]) == 0.5
