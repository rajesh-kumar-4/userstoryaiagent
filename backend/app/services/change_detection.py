from __future__ import annotations

import fnmatch
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from pathlib import Path

from app.domain.models import ChangeEvent, EventType, FileStamp, RepositoryRecord
from app.infrastructure.git.git_repository import GitRepository

MANIFEST_NAMES = frozenset(
    {
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
        "package.json",
        "package-lock.json",
        "requirements.txt",
        "pyproject.toml",
        "go.mod",
        "go.sum",
    }
)
CONFIG_PATTERNS = ("application*.yml", "application*.yaml", "application*.properties")


@dataclass(frozen=True)
class RepositorySnapshot:
    repository: str
    current_branch: str | None
    head_sha: str | None
    branch_heads: dict[str, str] = field(default_factory=dict)
    pr_refs: dict[str, str] = field(default_factory=dict)
    files: dict[str, FileStamp] = field(default_factory=dict)


def classify_file(path: str) -> EventType:
    name = PurePosixPath(path).name
    if name in MANIFEST_NAMES or fnmatch.fnmatch(name, "requirements*.txt"):
        return EventType.DEPENDENCY_UPDATED
    if any(fnmatch.fnmatch(name, pattern) for pattern in CONFIG_PATTERNS):
        return EventType.CONFIG_UPDATED
    return EventType.FILE_MODIFIED


def _event(
    event_type: EventType,
    repository: str,
    branch: str | None,
    *,
    file: str | None = None,
    payload: dict | None = None,
) -> ChangeEvent:
    return ChangeEvent(type=event_type, repository=repository, branch=branch, file=file, payload=payload or {})


def diff_snapshots(
    previous: RepositorySnapshot | None,
    current: RepositorySnapshot,
    merge_commits: frozenset[str] = frozenset(),
) -> list[ChangeEvent]:
    if previous is None:
        return []

    repo_id = current.repository
    branch = current.current_branch
    events: list[ChangeEvent] = []

    if previous.current_branch != current.current_branch:
        events.append(
            _event(
                EventType.BRANCH_CHANGED,
                repo_id,
                branch,
                payload={"from": previous.current_branch, "to": current.current_branch},
            )
        )

    for name in sorted(previous.branch_heads.keys() - current.branch_heads.keys()):
        events.append(
            _event(
                EventType.BRANCH_CHANGED,
                repo_id,
                name,
                payload={"action": "DELETED", "from": previous.branch_heads[name]},
            )
        )

    for name, sha in sorted(current.branch_heads.items()):
        old = previous.branch_heads.get(name)
        if old == sha:
            continue
        if old is None:
            events.append(
                _event(EventType.BRANCH_CHANGED, repo_id, name, payload={"action": "CREATED", "to": sha})
            )
        elif sha in merge_commits:
            events.append(
                _event(EventType.MERGE_COMPLETED, repo_id, name, payload={"from": old, "to": sha})
            )
        else:
            events.append(
                _event(EventType.COMMIT_CREATED, repo_id, name, payload={"from": old, "to": sha})
            )

    for ref, sha in sorted(current.pr_refs.items()):
        if ref not in previous.pr_refs:
            events.append(_event(EventType.PR_CREATED, repo_id, branch, payload={"ref": ref, "head_sha": sha}))

    for path in sorted(current.files):
        if previous.files.get(path) == current.files[path]:
            continue
        events.append(_event(classify_file(path), repo_id, branch, file=path))

    for path in sorted(previous.files.keys() - current.files.keys()):
        events.append(_event(EventType.FILE_DELETED, repo_id, branch, file=path))

    return events


class ChangeDetectionEngine:
    def __init__(self, watch_patterns: Sequence[str]) -> None:
        self._patterns = tuple(watch_patterns)

    def snapshot(self, record: RepositoryRecord, repo: GitRepository) -> RepositorySnapshot:
        return RepositorySnapshot(
            repository=record.id,
            current_branch=repo.current_branch(),
            head_sha=repo.head_sha(),
            branch_heads=dict(repo.local_branches()),
            pr_refs=dict(repo.pull_request_refs()),
            files=repo.watched_files(self._patterns),
        )

    def detect(
        self,
        record: RepositoryRecord,
        previous: RepositorySnapshot | None,
    ) -> tuple[RepositorySnapshot, list[ChangeEvent]]:
        with GitRepository(Path(record.path)) as repo:
            current = self.snapshot(record, repo)
            merges: set[str] = set()
            if previous is not None:
                for name, sha in current.branch_heads.items():
                    old = previous.branch_heads.get(name)
                    if old is not None and old != sha and len(repo.parents_of(sha)) > 1:
                        merges.add(sha)
        return current, diff_snapshots(previous, current, frozenset(merges))
