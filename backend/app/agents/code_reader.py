"""Reads file content for a change set: the working tree for PRE_COMMIT, otherwise git revisions."""

from __future__ import annotations

from pathlib import Path

import git
from git.exc import GitError

from app.core.exceptions import DomainError
from app.core.paths import ensure_within
from app.domain.models import AnalysisMode, ChangeSet

MAX_FILE_BYTES = 512 * 1024


def current_content(root: Path, change_set: ChangeSet, path: str) -> str | None:
    """Target-side content. Uses the working tree for PRE_COMMIT or when no target revision exists."""
    if change_set.analysis_mode is AnalysisMode.PRE_COMMIT or not change_set.target_sha:
        return read_worktree(root, path)
    return read_revision(root, change_set.target_sha, path)


def base_content(root: Path, change_set: ChangeSet, path: str) -> str | None:
    if not change_set.base_sha:
        return None
    return read_revision(root, change_set.base_sha, path)


def read_worktree(root: Path, path: str) -> str | None:
    try:
        candidate = ensure_within(root, root / path)
    except DomainError:
        return None
    try:
        if not candidate.is_file() or candidate.stat().st_size > MAX_FILE_BYTES:
            return None
        return candidate.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def read_revision(root: Path, sha: str, path: str) -> str | None:
    repo = None
    try:
        repo = git.Repo(root)
        blob = repo.commit(sha).tree / path
        if blob.type != "blob" or blob.size > MAX_FILE_BYTES:
            return None
        return blob.data_stream.read().decode("utf-8", errors="replace")
    except (KeyError, ValueError, OSError, GitError):
        return None
    finally:
        if repo is not None:
            repo.close()
