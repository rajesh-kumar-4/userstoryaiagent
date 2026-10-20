from __future__ import annotations

import logging
from pathlib import Path

from app.core.exceptions import GitOperationError, InvalidRequestError
from app.domain.models import (
    AnalysisMode,
    BranchInfo,
    ChangeScopeRequest,
    ChangeSet,
    CommitInfo,
    PullRequestRef,
    RepositoryInfo,
    RepositoryRecord,
)
from app.infrastructure.git.git_repository import GitRepository
from app.services.branch_discovery import BranchDiscoveryService
from app.services.commit_discovery import CommitDiscoveryService
from app.services.change_scope import ChangeScopeResolver
from app.services.git_metadata import GitMetadataService
from app.services.pull_request_service import PullRequestService
from app.services.repository_registry import RepositoryRegistry

logger = logging.getLogger(__name__)

MAX_COMMIT_LIMIT = 500


class RepositoryExplorer:
    def __init__(
        self,
        registry: RepositoryRegistry,
        branches: BranchDiscoveryService,
        commits: CommitDiscoveryService,
        metadata: GitMetadataService,
        scope: ChangeScopeResolver,
        pulls: PullRequestService,
    ) -> None:
        self._registry = registry
        self._branches = branches
        self._commits = commits
        self._metadata = metadata
        self._scope = scope
        self._pulls = pulls

    def list_repositories(self) -> list[RepositoryInfo]:
        infos: list[RepositoryInfo] = []
        for record in self._registry.all_records():
            try:
                infos.append(self._info(record))
            except GitOperationError:
                logger.warning("skipping unreadable repository %s", record.id)
        return infos

    def describe(self, identifier: str) -> RepositoryInfo:
        return self._info(self._registry.resolve(identifier))

    def branches(self, identifier: str) -> list[BranchInfo]:
        record = self._registry.resolve(identifier)
        with GitRepository(Path(record.path)) as repo:
            return self._branches.list_branches(repo)

    def commits(self, identifier: str, ref: str = "HEAD", limit: int = 50) -> list[CommitInfo]:
        if not 1 <= limit <= MAX_COMMIT_LIMIT:
            raise InvalidRequestError(f"limit must be between 1 and {MAX_COMMIT_LIMIT}")
        record = self._registry.resolve(identifier)
        with GitRepository(Path(record.path)) as repo:
            return self._commits.list_commits(repo, ref, limit)

    def status(self, identifier: str) -> ChangeSet:
        return self._scope.resolve(ChangeScopeRequest(repo_path=identifier, analysis_mode=AnalysisMode.PRE_COMMIT))

    def pull_requests(self, identifier: str) -> list[PullRequestRef]:
        record = self._registry.resolve(identifier)
        with GitRepository(Path(record.path)) as repo:
            return self._pulls.list_pull_requests(repo)

    def _info(self, record: RepositoryRecord) -> RepositoryInfo:
        with GitRepository(Path(record.path)) as repo:
            meta = self._metadata.describe(repo)
        return RepositoryInfo(
            id=record.id,
            name=record.name,
            path=record.path,
            current_branch=meta.current_branch,
            default_branch=meta.default_branch,
            latest_commit=meta.latest_commit,
            remote_origin=meta.remote_origin,
            is_dirty=meta.is_dirty,
            technology_tags=record.technology_tags,
            owners=record.owners,
            discovered_at=record.discovered_at,
        )
