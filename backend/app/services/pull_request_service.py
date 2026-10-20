from __future__ import annotations

import re
from typing import Protocol

from app.domain.models import AnalysisMode, ChangeSet, PullRequestRef
from app.infrastructure.git.git_repository import GitRepository
from app.services.branch_comparison import BranchComparisonService


class PullRequestProvider(Protocol):
    def list_pull_requests(self, repo: GitRepository) -> list[PullRequestRef]: ...


def _provider_for(ref: str) -> str:
    if ref.startswith("refs/pull/"):
        return "GITHUB_REF"
    if ref.startswith("refs/merge-requests/"):
        return "GITLAB_REF"
    return "LOCAL_REF"


class LocalRefPullRequestProvider:
    _NUMBER = re.compile(r"/(\d+)(?:/|$)")

    def list_pull_requests(self, repo: GitRepository) -> list[PullRequestRef]:
        refs: list[PullRequestRef] = []
        for ref, sha in repo.pull_request_refs():
            match = self._NUMBER.search(ref)
            refs.append(
                PullRequestRef(
                    provider=_provider_for(ref),
                    number=int(match.group(1)) if match else None,
                    ref=ref,
                    head_sha=sha,
                )
            )
        return sorted(refs, key=lambda item: (item.provider, item.number or 0))


class PullRequestService:
    def __init__(self, provider: PullRequestProvider, comparison: BranchComparisonService) -> None:
        self._provider = provider
        self._comparison = comparison

    def list_pull_requests(self, repo: GitRepository) -> list[PullRequestRef]:
        return self._provider.list_pull_requests(repo)

    def analyze(self, repo: GitRepository, repository_id: str, source: str, target: str) -> ChangeSet:
        return self._comparison.compare(repo, repository_id, source, target, AnalysisMode.PR_ANALYSIS)
