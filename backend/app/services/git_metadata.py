from __future__ import annotations

from dataclasses import dataclass

from app.infrastructure.git.git_repository import GitRepository


@dataclass(frozen=True)
class GitMetadata:
    current_branch: str | None
    default_branch: str | None
    latest_commit: str | None
    remote_origin: str | None
    is_dirty: bool


class GitMetadataService:
    def describe(self, repo: GitRepository) -> GitMetadata:
        return GitMetadata(
            current_branch=repo.current_branch(),
            default_branch=repo.default_branch(),
            latest_commit=repo.head_sha(),
            remote_origin=repo.remote_origin_url(),
            is_dirty=repo.is_dirty(),
        )
