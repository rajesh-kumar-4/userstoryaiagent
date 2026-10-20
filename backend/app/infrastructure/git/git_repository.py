from __future__ import annotations

import os
import re
import stat
import subprocess
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path

from git import Commit, InvalidGitRepositoryError, NoSuchPathError, Repo

from app.core.exceptions import GitOperationError, InvalidRequestError, RefNotFoundError
from app.core.redaction import redact_text, redact_url
from app.domain.models import ChangeArea, ChangedFile, ChangeType, CommitInfo, FileStamp
from app.infrastructure.git.diff_parser import parse_name_status, parse_unified_hunks

EMPTY_TREE_SHA = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
DEFAULT_BRANCH_CANDIDATES = ("main", "master", "develop")
PULL_REQUEST_REF_PREFIXES = ("refs/pull", "refs/merge-requests", "refs/remotes/origin/pr")
_REF_PATTERN = re.compile(r"^[A-Za-z0-9._/@-]+$")
_MAX_UNTRACKED_BYTES = 5 * 1024 * 1024
_GIT_TIMEOUT_SECONDS = 60
_GIT_ENV = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_EDITOR": "true", "GIT_OPTIONAL_LOCKS": "0"}


def validate_ref(ref: str) -> str:
    if not ref or ref.startswith("-") or ".." in ref or not _REF_PATTERN.match(ref):
        raise InvalidRequestError(f"Invalid git reference: {ref!r}")
    return ref


def _split_nul(output: str) -> list[str]:
    return [token for token in output.split("\0") if token]


def _count_lines(path: Path) -> int:
    try:
        if not path.is_file() or path.stat().st_size > _MAX_UNTRACKED_BYTES:
            return 0
        data = path.read_bytes()
    except OSError:
        return 0
    if not data or b"\0" in data:
        return 0
    return data.count(b"\n") + (0 if data.endswith(b"\n") else 1)


def _commit_info(commit: Commit) -> CommitInfo:
    return CommitInfo(
        sha=commit.hexsha,
        short_sha=commit.hexsha[:7],
        author_name=commit.author.name or "",
        author_email=commit.author.email or "",
        authored_at=datetime.fromtimestamp(commit.authored_date, tz=timezone.utc),
        summary=commit.summary,
        parents=[parent.hexsha for parent in commit.parents],
    )


class GitRepository:
    def __init__(self, path: Path) -> None:
        self.path = path
        try:
            self._repo = Repo(str(path), search_parent_directories=False)
        except (InvalidGitRepositoryError, NoSuchPathError) as exc:
            raise GitOperationError(f"Not a git repository: {path.name}") from exc

    def close(self) -> None:
        self._repo.close()

    def __enter__(self) -> GitRepository:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def _run(self, command: str, *args: str) -> str:
        name = command.replace("_", "-")
        try:
            completed = subprocess.run(
                ["git", "-C", str(self.path), name, *args],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                stdin=subprocess.DEVNULL,
                timeout=_GIT_TIMEOUT_SECONDS,
                env=_GIT_ENV,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise GitOperationError(f"git {name} could not complete: {type(exc).__name__}") from exc
        if completed.returncode != 0:
            detail = redact_text(completed.stderr.strip())[:300] or "no details"
            raise GitOperationError(f"git {name} failed: {detail}")
        return completed.stdout.rstrip("\n")

    def current_branch(self) -> str | None:
        try:
            return self._repo.active_branch.name
        except TypeError:
            return None

    def head_sha(self) -> str | None:
        return self._repo.head.commit.hexsha if self._repo.head.is_valid() else None

    def is_dirty(self) -> bool:
        return bool(self._run("status", "--porcelain", "--untracked-files=all"))

    def remote_origin_url(self) -> str | None:
        for remote in self._repo.remotes:
            if remote.name == "origin":
                return redact_url(remote.url)
        return None

    def default_branch(self) -> str | None:
        try:
            symbolic = self._run("symbolic_ref", "refs/remotes/origin/HEAD")
            return symbolic.removeprefix("refs/remotes/origin/")
        except GitOperationError:
            pass
        local = {name for name, _ in self.local_branches()}
        for candidate in DEFAULT_BRANCH_CANDIDATES:
            if candidate in local:
                return candidate
        return self.current_branch()

    def local_branches(self) -> list[tuple[str, str]]:
        return [(ref.removeprefix("refs/heads/"), sha) for ref, sha in self._for_each_ref("refs/heads")]

    def remote_branches(self) -> list[tuple[str, str]]:
        return [
            (ref.removeprefix("refs/remotes/origin/"), sha)
            for ref, sha in self._for_each_ref("refs/remotes/origin")
            if ref != "refs/remotes/origin/HEAD"
        ]

    def pull_request_refs(self) -> list[tuple[str, str]]:
        return self._for_each_ref(*PULL_REQUEST_REF_PREFIXES)

    def _for_each_ref(self, *patterns: str) -> list[tuple[str, str]]:
        output = self._run("for_each_ref", "--format=%(refname)\t%(objectname)", *patterns)
        rows: list[tuple[str, str]] = []
        for line in output.splitlines():
            ref, _, sha = line.partition("\t")
            if ref and sha:
                rows.append((ref, sha))
        return rows

    def resolve_commit(self, ref: str) -> str:
        validate_ref(ref)
        for candidate in (ref, f"origin/{ref}"):
            try:
                return self._run("rev_parse", "--verify", "--quiet", f"{candidate}^{{commit}}")
            except GitOperationError:
                continue
        raise RefNotFoundError(f"Reference not found in {self.path.name}: {ref}")

    def commit_info(self, ref: str) -> CommitInfo:
        return _commit_info(self._repo.commit(self.resolve_commit(ref)))

    def list_commits(self, ref: str, limit: int) -> list[CommitInfo]:
        sha = self.resolve_commit(ref)
        return [_commit_info(commit) for commit in self._repo.iter_commits(sha, max_count=limit)]

    def history(self, ref: str, limit: int) -> list[tuple[CommitInfo, int, int]]:
        sha = self.resolve_commit(ref)
        entries: list[tuple[CommitInfo, int, int]] = []
        for commit in self._repo.iter_commits(sha, max_count=limit):
            totals = commit.stats.total
            entries.append(
                (_commit_info(commit), int(totals.get("insertions", 0)), int(totals.get("deletions", 0)))
            )
        return entries

    def parents_of(self, sha: str) -> list[str]:
        return [parent.hexsha for parent in self._repo.commit(sha).parents]

    def merge_base(self, left: str, right: str) -> str:
        try:
            return self._run("merge_base", left, right)
        except GitOperationError as exc:
            raise GitOperationError(f"No common ancestor between {left[:7]} and {right[:7]}") from exc

    def diff_range(self, base_sha: str, target_sha: str, area: ChangeArea) -> list[ChangedFile]:
        return self._collect_changes([base_sha, target_sha], area)

    def working_tree_changes(self) -> list[ChangedFile]:
        base = self.head_sha() or EMPTY_TREE_SHA
        return [
            *self._collect_changes([base, "--cached"], ChangeArea.STAGED),
            *self._collect_changes([], ChangeArea.UNSTAGED),
            *self._untracked_files(),
        ]

    def _collect_changes(self, rev_args: list[str], area: ChangeArea) -> list[ChangedFile]:
        name_status = self._run("diff", *rev_args, "--name-status", "-z", "-M", "--no-color")
        patch = self._run("diff", *rev_args, "-U0", "-M", "--no-color", "--no-ext-diff")
        return parse_name_status(name_status, parse_unified_hunks(patch), area)

    def _untracked_files(self) -> list[ChangedFile]:
        output = self._run("ls_files", "--others", "--exclude-standard", "-z")
        return [
            ChangedFile(
                path=relative,
                change_type=ChangeType.UNTRACKED,
                area=ChangeArea.UNTRACKED,
                added_lines=_count_lines(self.path / relative),
            )
            for relative in _split_nul(output)
        ]

    def watched_files(self, patterns: Sequence[str]) -> dict[str, FileStamp]:
        if not patterns:
            return {}
        pathspecs = [f":(glob){pattern}" for pattern in patterns]
        output = self._run(
            "ls_files", "--cached", "--others", "--exclude-standard", "-z", "--", *pathspecs
        )
        stamps: dict[str, FileStamp] = {}
        for relative in _split_nul(output):
            try:
                info = os.stat(self.path / relative)
            except OSError:
                continue
            if stat.S_ISREG(info.st_mode):
                stamps[relative] = FileStamp(size=info.st_size, mtime_ns=info.st_mtime_ns)
        return stamps
