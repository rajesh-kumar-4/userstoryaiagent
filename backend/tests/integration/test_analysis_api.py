import pytest
from dependency_injector import providers
from fastapi.testclient import TestClient

from app.core.exceptions import LLMProviderError
from app.core.llm.base_provider import LLMProvider, LLMResponse
from app.core.security.rbac import Role
from app.main import create_app
from tests.support import write

PRE_COMMIT_BODY = {"repo_path": "billing-service"}
MONITOR_BODY = {"mode": "SCHEDULED", "interval_seconds": 60, "debounce_seconds": 0}


class FakeLLM(LLMProvider):
    name = "fake"

    def __init__(self) -> None:
        super().__init__(model="fake-model")

    def complete(self, messages, *, temperature: float = 0.2, max_tokens: int = 512) -> LLMResponse:
        return LLMResponse(provider="fake", model="fake-model", content="LLM narrative for the change.")


class BrokenLLM(FakeLLM):
    def complete(self, messages, *, temperature: float = 0.2, max_tokens: int = 512) -> LLMResponse:
        raise LLMProviderError("fake request failed: ConnectError")


def _client(settings) -> TestClient:
    return TestClient(create_app(settings))


@pytest.fixture
def pending_change(sample_workspace):
    """Uncommitted change set in billing-service: a dependency, a config file, and a source edit."""
    billing = sample_workspace / "billing-service"
    write(
        billing / "pom.xml",
        "<project><dependencies><dependency>spring-boot-starter-web</dependency></dependencies></project>",
    )
    write(billing / "src" / "main" / "resources" / "application.yml", "server:\n  port: 8080\n")
    write(billing / "src" / "main" / "App.java", "class App {\n  int y;\n}\n")
    return billing


def test_pre_commit_analysis_reports_configuration_and_dependency_risk(settings, pending_change):
    with _client(settings) as client:
        response = client.post("/pre-commit-analysis", json=PRE_COMMIT_BODY)

    assert response.status_code == 200
    report = response.json()
    categories = {finding["category"] for finding in report["findings"]}
    assert {"configuration_change", "dependency_change", "missing_tests"} <= categories
    assert report["repository"] == "billing-service"
    assert report["risk_score"] >= 50
    assert report["risk_level"] in {"HIGH", "CRITICAL"}
    assert report["summary_source"] == "rule_based"
    assert report["llm_provider"] is None


def test_llm_narrative_replaces_rule_summary_when_provider_is_available(settings, pending_change):
    app = create_app(settings)
    app.state.container.llm_provider.override(providers.Object(FakeLLM()))

    with TestClient(app) as client:
        report = client.post("/pre-commit-analysis", json=PRE_COMMIT_BODY).json()

    assert report["summary_source"] == "llm"
    assert report["summary"] == "LLM narrative for the change."
    assert report["llm_provider"] == "fake"


def test_llm_failure_falls_back_to_rule_summary_with_warning(settings, pending_change):
    app = create_app(settings)
    app.state.container.llm_provider.override(providers.Object(BrokenLLM()))

    with TestClient(app) as client:
        report = client.post("/pre-commit-analysis", json=PRE_COMMIT_BODY).json()

    assert report["summary_source"] == "rule_based"
    assert any("LLM summary unavailable" in warning for warning in report["warnings"])


def test_post_commit_analysis_is_retrievable_by_sha_prefix(settings, sample_workspace):
    with _client(settings) as client:
        report = client.post("/post-commit-analysis", json=PRE_COMMIT_BODY).json()
        sha = report["commit_id"]
        found = client.get(f"/analysis/{sha[:8]}")
        missing = client.get("/analysis/deadbeef")

    assert sha
    assert found.status_code == 200
    assert found.json()["analysis_id"] == report["analysis_id"]
    assert missing.status_code == 404
    assert missing.json()["error"] == "AnalysisNotFoundError"


def test_similar_change_search_matches_stored_analysis(settings, pending_change):
    with _client(settings) as client:
        client.post("/pre-commit-analysis", json=PRE_COMMIT_BODY)
        matches = client.post("/search-similar-changes", json={"query": "application configuration changed"})
        scoped = client.post(
            "/search-similar-changes",
            json={"query": "application configuration changed", "repository": "frontend/web-app"},
        )

    assert matches.status_code == 200
    body = matches.json()
    assert body and body[0]["repository"] == "billing-service"
    assert "configuration" in body[0]["matched_terms"]
    assert scoped.json() == []


def test_criticality_report_contains_all_factors(settings, sample_workspace):
    with _client(settings) as client:
        response = client.post("/criticality-analysis", json={"repo_path": "billing-service"})

    assert response.status_code == 200
    body = response.json()
    assert body["repository"] == "billing-service"
    assert set(body["factors"]) == {
        "technology_breadth",
        "contributor_breadth",
        "commit_activity",
        "latest_risk",
        "high_severity_findings",
    }
    assert 0 <= body["score"] <= 100
    assert body["rationale_source"] == "rule_based"


def test_dashboard_reflects_stored_analyses(settings, pending_change):
    with _client(settings) as client:
        client.post("/pre-commit-analysis", json=PRE_COMMIT_BODY)
        summary = client.get("/dashboard/summary").json()
        repositories = client.get("/dashboard/repositories").json()
        trends = client.get("/dashboard/trends", params={"days": 7}).json()

    assert summary["registered_repositories"] == 3
    assert summary["total_analyses"] == 1
    assert summary["analyzed_repositories"] == 1
    assert summary["analyses_by_mode"] == {"PRE_COMMIT": 1}
    assert repositories[0]["repository"] == "billing-service"
    assert len(trends) == 7
    assert sum(point["analyses"] for point in trends) == 1


def test_invalid_refs_and_missing_fields_are_rejected(settings, sample_workspace):
    with _client(settings) as client:
        option_injection = client.post(
            "/branch-analysis",
            json={"repo_path": "billing-service", "source_branch": "-evil", "target_branch": "main"},
        )
        missing_source = client.post("/release-analysis", json={"repo_path": "billing-service"})

    assert option_injection.status_code == 422
    assert missing_source.status_code == 422


def test_rbac_enforces_api_keys_and_permissions(settings, pending_change):
    secured = settings.model_copy(
        update={
            "auth_enabled": True,
            "api_keys": {"viewer-key": Role.VIEWER, "analyst-key": Role.ANALYST},
        }
    )
    viewer = {"X-API-Key": "viewer-key"}
    analyst = {"X-API-Key": "analyst-key"}

    with _client(secured) as client:
        anonymous = client.post("/pre-commit-analysis", json=PRE_COMMIT_BODY)
        unknown = client.post("/pre-commit-analysis", json=PRE_COMMIT_BODY, headers={"X-API-Key": "nope"})
        viewer_run = client.post("/pre-commit-analysis", json=PRE_COMMIT_BODY, headers=viewer)
        analyst_run = client.post("/pre-commit-analysis", json=PRE_COMMIT_BODY, headers=analyst)
        viewer_dashboard = client.get("/dashboard/summary", headers=viewer)
        analyst_monitor = client.put("/monitor", json=MONITOR_BODY, headers=analyst)

    assert anonymous.status_code == 401
    assert unknown.status_code == 401
    assert viewer_run.status_code == 403
    assert analyst_run.status_code == 200
    assert viewer_dashboard.status_code == 200
    assert analyst_monitor.status_code == 403


def test_repository_and_intelligence_routes_are_gated(settings, sample_workspace):
    secured = settings.model_copy(
        update={
            "auth_enabled": True,
            "api_keys": {"viewer-key": Role.VIEWER, "analyst-key": Role.ANALYST},
        }
    )
    viewer = {"X-API-Key": "viewer-key"}
    analyst = {"X-API-Key": "analyst-key"}

    with _client(secured) as client:
        anonymous_list = client.get("/repositories")
        viewer_list = client.get("/repositories", headers=viewer)
        viewer_refresh = client.post("/repositories/refresh", headers=viewer)
        analyst_refresh = client.post("/repositories/refresh", headers=analyst)
        viewer_summary = client.get("/workspace/summary", headers=viewer)
        viewer_scope = client.post("/change-scope", json={}, headers=viewer)

    assert anonymous_list.status_code == 401
    assert viewer_list.status_code == 200
    assert viewer_refresh.status_code == 403
    assert analyst_refresh.status_code == 200
    assert viewer_summary.status_code == 200
    assert viewer_scope.status_code == 403
