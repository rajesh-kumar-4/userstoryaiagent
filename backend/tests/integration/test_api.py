from fastapi.testclient import TestClient

from app.main import create_app


def _client(settings):
    return TestClient(create_app(settings))


def test_health_and_repository_listing(settings, sample_workspace):
    with _client(settings) as client:
        health = client.get("/health")
        listing = client.get("/repositories")

    assert health.status_code == 200
    assert health.json()["repositories"] == 3
    assert {item["id"] for item in listing.json()} == {"billing-service", "frontend/web-app", "services/payments"}


def test_nested_repository_routes_resolve(settings, sample_workspace):
    with _client(settings) as client:
        describe = client.get("/repositories/frontend/web-app")
        branches = client.get("/repositories/frontend/web-app/branches")
        status = client.get("/repositories/billing-service/status")

    assert describe.status_code == 200
    assert describe.json()["name"] == "web-app"
    assert branches.status_code == 200
    assert status.status_code == 200
    assert "totals" in status.json()


def test_domain_errors_map_to_http_status(settings, sample_workspace):
    with _client(settings) as client:
        missing = client.get("/repositories/unknown-repo")
        outside = client.post("/repositories/register", json={"path": "../outside"})
        bad_limit = client.get("/repositories/billing-service/commits", params={"limit": 0})

    assert missing.status_code == 404
    assert missing.json()["error"] == "RepositoryNotFoundError"
    assert outside.status_code == 403
    assert bad_limit.status_code == 422


def test_pr_analysis_validation_is_enforced(settings, sample_workspace):
    with _client(settings) as client:
        response = client.post(
            "/change-scope",
            json={"repo_path": "billing-service", "analysis_mode": "PR_ANALYSIS"},
        )

    assert response.status_code == 422


def test_change_scope_and_summary_endpoints(settings, sample_workspace):
    with _client(settings) as client:
        scope = client.post(
            "/change-scope",
            json={
                "repo_path": "billing-service",
                "analysis_mode": "BRANCH_ANALYSIS",
                "source_branch": "feature/PAY-1",
                "target_branch": "main",
            },
        )
        summary = client.get("/workspace/summary")

    assert scope.status_code == 200
    assert scope.json()["totals"]["files_changed"] == 1
    assert summary.json()["repository_count"] == 3


def test_monitor_configuration_and_events(settings, sample_workspace):
    with _client(settings) as client:
        current = client.get("/monitor")
        updated = client.put(
            "/monitor",
            json={"mode": "SCHEDULED", "interval_seconds": 60, "debounce_seconds": 0},
        )
        scan = client.post("/monitor/scan")
        events = client.get("/events", params={"event_type": "REPOSITORY_DISCOVERED"})

    assert current.json()["config"]["mode"] == "MANUAL"
    assert updated.json()["config"]["mode"] == "SCHEDULED"
    assert scan.status_code == 200
    assert len(events.json()) >= 3


def test_mcp_endpoint_lists_and_calls_tools(settings, sample_workspace):
    with _client(settings) as client:
        listed = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        called = client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "list_repositories", "arguments": {}},
            },
        )
        notification = client.post("/mcp", json={"jsonrpc": "2.0", "method": "ping"})

    tool_names = {tool["name"] for tool in listed.json()["result"]["tools"]}
    assert "list_repositories" in tool_names
    assert called.json()["result"]["isError"] is False
    assert notification.json() is None
