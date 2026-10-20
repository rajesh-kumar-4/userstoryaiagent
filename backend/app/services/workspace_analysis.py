from __future__ import annotations

from collections import Counter
from pathlib import Path

from app.core.exceptions import GitOperationError, InvalidRequestError
from app.domain.models import HistoricalSummary, RepositoryStatusSummary, WorkspaceSummary, utc_now
from app.infrastructure.git.git_repository import GitRepository
from app.services.repository_registry import RepositoryRegistry

MAX_HISTORY_LIMIT = 500


class WorkspaceAnalysisService:
    def __init__(self, registry: RepositoryRegistry) -> None:
        self._registry = registry

    def summary(self) -> WorkspaceSummary:
        items: list[RepositoryStatusSummary] = []
        for record in self._registry.all_records():
            try:
                with GitRepository(Path(record.path)) as repo:
                    changes = repo.working_tree_changes()
                    items.append(
                        RepositoryStatusSummary(
                            repository=record.id,
                            current_branch=repo.current_branch(),
                            latest_commit=repo.head_sha(),
                            changed_files=len(changes),
                            is_dirty=bool(changes),
                        )
                    )
            except GitOperationError as exc:
                items.append(
                    RepositoryStatusSummary(
                        repository=record.id,
                        current_branch=None,
                        latest_commit=None,
                        changed_files=0,
                        is_dirty=False,
                        error=str(exc),
                    )
                )
        return WorkspaceSummary(
            generated_at=utc_now(),
            repository_count=len(items),
            dirty_repository_count=sum(1 for item in items if item.is_dirty),
            repositories=items,
        )

    def history(self, repository: str, ref: str = "HEAD", limit: int = 100) -> HistoricalSummary:
        if not 1 <= limit <= MAX_HISTORY_LIMIT:
            raise InvalidRequestError(f"limit must be between 1 and {MAX_HISTORY_LIMIT}")
        record = self._registry.resolve(repository)
        with GitRepository(Path(record.path)) as repo:
            entries = repo.history(ref, limit)

        authors = Counter(info.author_name for info, _, _ in entries)
        dates = [info.authored_at for info, _, _ in entries]
        return HistoricalSummary(
            repository=record.id,
            ref=ref,
            commit_count=len(entries),
            author_count=len(authors),
            insertions=sum(insertions for _, insertions, _ in entries),
            deletions=sum(deletions for _, _, deletions in entries),
            first_commit_at=min(dates) if dates else None,
            last_commit_at=max(dates) if dates else None,
            top_authors=dict(authors.most_common(10)),
            commits=[info for info, _, _ in entries],
        )
