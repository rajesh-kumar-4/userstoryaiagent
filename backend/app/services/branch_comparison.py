from __future__ import annotations

from app.domain.models import AnalysisMode, ChangeArea, ChangeSet, CompareMode
from app.infrastructure.git.git_repository import GitRepository


class BranchComparisonService:
    def compare(
        self,
        repo: GitRepository,
        repository_id: str,
        source: str,
        target: str,
        mode: AnalysisMode,
        compare_mode: CompareMode = CompareMode.MERGE_BASE,
    ) -> ChangeSet:
        source_sha = repo.resolve_commit(source)
        target_sha = repo.resolve_commit(target)
        if compare_mode is CompareMode.DIRECT:
            base_sha = target_sha
        else:
            base_sha = repo.merge_base(target_sha, source_sha)
        return ChangeSet(
            repository=repository_id,
            analysis_mode=mode,
            base_ref=target,
            target_ref=source,
            base_sha=base_sha,
            target_sha=source_sha,
            files=repo.diff_range(base_sha, source_sha, ChangeArea.COMPARISON),
        )
