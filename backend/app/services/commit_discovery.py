from __future__ import annotations

from app.domain.models import AnalysisMode, ChangeArea, ChangeSet, CommitInfo
from app.infrastructure.git.git_repository import EMPTY_TREE_SHA, GitRepository


class CommitDiscoveryService:
    def list_commits(self, repo: GitRepository, ref: str, limit: int) -> list[CommitInfo]:
        return repo.list_commits(ref, limit)

    def get_commit(self, repo: GitRepository, ref: str) -> CommitInfo:
        return repo.commit_info(ref)

    def commit_change_set(self, repo: GitRepository, repository_id: str, ref: str) -> ChangeSet:
        commit = repo.commit_info(ref)
        base_sha = commit.parents[0] if commit.parents else EMPTY_TREE_SHA
        return ChangeSet(
            repository=repository_id,
            analysis_mode=AnalysisMode.POST_COMMIT,
            base_ref=base_sha,
            target_ref=commit.sha,
            base_sha=base_sha,
            target_sha=commit.sha,
            files=repo.diff_range(base_sha, commit.sha, ChangeArea.COMMITTED),
        )
