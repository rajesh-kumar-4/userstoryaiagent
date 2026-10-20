from __future__ import annotations

from pathlib import Path

from app.core.exceptions import GitOperationError, InvalidRequestError
from app.domain.models import AnalysisMode, ChangeScopeRequest, ChangeSet, CompareMode
from app.infrastructure.git.git_repository import GitRepository
from app.services.branch_comparison import BranchComparisonService
from app.services.commit_discovery import CommitDiscoveryService
from app.services.pull_request_service import PullRequestService
from app.services.repository_registry import RepositoryRegistry

RELEASE_PREFIX = "release/"


def _require(value: str | None, name: str) -> str:
    if not value:
        raise InvalidRequestError(f"{name} is required for this analysis mode")
    return value


class ChangeScopeResolver:
    def __init__(
        self,
        registry: RepositoryRegistry,
        commits: CommitDiscoveryService,
        comparison: BranchComparisonService,
        pulls: PullRequestService,
    ) -> None:
        self._registry = registry
        self._commits = commits
        self._comparison = comparison
        self._pulls = pulls

    def resolve(self, request: ChangeScopeRequest) -> ChangeSet:
        mode = request.analysis_mode
        if mode in (AnalysisMode.WORKSPACE_ANALYSIS, AnalysisMode.HISTORICAL_ANALYSIS):
            raise InvalidRequestError(f"{mode.value} is served by the workspace and history endpoints")

        record = self._registry.resolve(request.repo_path)
        with GitRepository(Path(record.path)) as repo:
            if mode is AnalysisMode.PRE_COMMIT:
                return ChangeSet(
                    repository=record.id,
                    analysis_mode=mode,
                    base_ref="HEAD",
                    base_sha=repo.head_sha(),
                    files=repo.working_tree_changes(),
                )
            if mode is AnalysisMode.POST_COMMIT:
                return self._commits.commit_change_set(repo, record.id, request.commit_id or "HEAD")
            if mode is AnalysisMode.PR_ANALYSIS:
                source = _require(request.source_branch, "source_branch")
                target = _require(request.target_branch, "target_branch")
                return self._pulls.analyze(repo, record.id, source, target)

            source = request.source_branch or repo.current_branch()
            if not source:
                raise InvalidRequestError("source_branch is required when HEAD is detached")
            target = request.target_branch or repo.default_branch()
            if not target:
                raise GitOperationError("target_branch could not be determined")
            if mode is AnalysisMode.RELEASE_ANALYSIS and not source.startswith(RELEASE_PREFIX):
                raise InvalidRequestError("RELEASE_ANALYSIS requires a release/* source branch")
            return self._comparison.compare(repo, record.id, source, target, mode, request.compare_mode)
