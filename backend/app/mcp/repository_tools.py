from __future__ import annotations

from typing import Any

from app.container import AppContainer
from app.domain.models import ChangeScopeRequest, EventType
from app.mcp.registry import ToolRegistry

_REPOSITORY_PROPERTY = {
    "type": "string",
    "description": "Repository id, repository name, or a path inside the workspace",
}
_REF_PROPERTY = {"type": "string", "description": "Branch, tag, or commit (default HEAD)"}
_LIMIT_PROPERTY = {"type": "integer", "minimum": 1, "maximum": 500}


def _schema(properties: dict[str, Any] | None = None, required: list[str] | None = None) -> dict[str, Any]:
    return {"type": "object", "properties": properties or {}, "required": required or []}


def register_repository_tools(tools: ToolRegistry, container: AppContainer) -> None:
    tools.register(
        "discover_repositories",
        "Rescan the workspace and register new or removed repositories without restart.",
        _schema(),
        lambda args: container.registry().refresh(),
    )
    tools.register(
        "list_repositories",
        "List all registered repositories with current branch and latest commit.",
        _schema(),
        lambda args: container.explorer().list_repositories(),
    )
    tools.register(
        "describe_repository",
        "Return metadata for one repository.",
        _schema({"repository": _REPOSITORY_PROPERTY}, ["repository"]),
        lambda args: container.explorer().describe(args["repository"]),
    )
    tools.register(
        "list_branches",
        "List local and remote branches with their classification.",
        _schema({"repository": _REPOSITORY_PROPERTY}, ["repository"]),
        lambda args: container.explorer().branches(args["repository"]),
    )
    tools.register(
        "list_commits",
        "List recent commits for a reference.",
        _schema({"repository": _REPOSITORY_PROPERTY, "ref": _REF_PROPERTY, "limit": _LIMIT_PROPERTY}, ["repository"]),
        lambda args: container.explorer().commits(
            args["repository"], args.get("ref") or "HEAD", int(args.get("limit") or 50)
        ),
    )
    tools.register(
        "get_repository_status",
        "Return staged, unstaged, and untracked changes (PRE_COMMIT scope).",
        _schema({"repository": _REPOSITORY_PROPERTY}, ["repository"]),
        lambda args: container.explorer().status(args["repository"]),
    )
    tools.register(
        "list_pull_requests",
        "Detect pull request refs available in the repository.",
        _schema({"repository": _REPOSITORY_PROPERTY}, ["repository"]),
        lambda args: container.explorer().pull_requests(args["repository"]),
    )
    tools.register(
        "resolve_change_scope",
        "Resolve the change set for PRE_COMMIT, POST_COMMIT, PR_ANALYSIS, BRANCH_ANALYSIS, or RELEASE_ANALYSIS.",
        _schema(
            {
                "repo_path": _REPOSITORY_PROPERTY,
                "analysis_mode": {"type": "string"},
                "commit_id": {"type": "string"},
                "source_branch": {"type": "string"},
                "target_branch": {"type": "string"},
                "compare_mode": {"type": "string", "enum": ["MERGE_BASE", "DIRECT"]},
            },
            ["repo_path"],
        ),
        lambda args: container.change_scope().resolve(ChangeScopeRequest.model_validate(args)),
    )
    tools.register(
        "workspace_summary",
        "Summarize branch, commit, and working tree state for every repository.",
        _schema(),
        lambda args: container.workspace_analysis().summary(),
    )
    tools.register(
        "repository_history",
        "Summarize commit history, authors, and churn for a repository.",
        _schema({"repository": _REPOSITORY_PROPERTY, "ref": _REF_PROPERTY, "limit": _LIMIT_PROPERTY}, ["repository"]),
        lambda args: container.workspace_analysis().history(
            args["repository"], args.get("ref") or "HEAD", int(args.get("limit") or 100)
        ),
    )
    tools.register(
        "register_repository",
        "Register a repository by path inside the workspace.",
        _schema({"path": {"type": "string"}}, ["path"]),
        lambda args: container.registry().resolve(args["path"]),
    )
    tools.register(
        "run_monitor_scan",
        "Run one workspace monitoring cycle and return the change events it produced.",
        _schema(),
        lambda args: container.monitor().run_cycle(),
    )
    tools.register(
        "recent_events",
        "Return recent change events, optionally filtered by repository or event type.",
        _schema(
            {
                "limit": _LIMIT_PROPERTY,
                "repository": _REPOSITORY_PROPERTY,
                "event_type": {"type": "string", "enum": [event.value for event in EventType]},
            }
        ),
        lambda args: container.event_bus().recent(
            limit=int(args.get("limit") or 100),
            repository=args.get("repository"),
            event_type=EventType(args["event_type"]) if args.get("event_type") else None,
        ),
    )
