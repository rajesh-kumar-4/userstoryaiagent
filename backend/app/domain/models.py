from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, computed_field

SCHEMA_VERSION = 1


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AnalysisMode(str, Enum):
    PRE_COMMIT = "PRE_COMMIT"
    POST_COMMIT = "POST_COMMIT"
    PR_ANALYSIS = "PR_ANALYSIS"
    BRANCH_ANALYSIS = "BRANCH_ANALYSIS"
    RELEASE_ANALYSIS = "RELEASE_ANALYSIS"
    WORKSPACE_ANALYSIS = "WORKSPACE_ANALYSIS"
    HISTORICAL_ANALYSIS = "HISTORICAL_ANALYSIS"


class CompareMode(str, Enum):
    MERGE_BASE = "MERGE_BASE"
    DIRECT = "DIRECT"


class BranchKind(str, Enum):
    MAIN = "MAIN"
    DEVELOP = "DEVELOP"
    RELEASE = "RELEASE"
    FEATURE = "FEATURE"
    BUGFIX = "BUGFIX"
    HOTFIX = "HOTFIX"
    OTHER = "OTHER"


class ChangeType(str, Enum):
    ADDED = "ADDED"
    MODIFIED = "MODIFIED"
    DELETED = "DELETED"
    RENAMED = "RENAMED"
    UNTRACKED = "UNTRACKED"


class ChangeArea(str, Enum):
    STAGED = "STAGED"
    UNSTAGED = "UNSTAGED"
    UNTRACKED = "UNTRACKED"
    COMMITTED = "COMMITTED"
    COMPARISON = "COMPARISON"


class EventType(str, Enum):
    REPOSITORY_DISCOVERED = "REPOSITORY_DISCOVERED"
    REPOSITORY_REMOVED = "REPOSITORY_REMOVED"
    FILE_MODIFIED = "FILE_MODIFIED"
    FILE_DELETED = "FILE_DELETED"
    DEPENDENCY_UPDATED = "DEPENDENCY_UPDATED"
    CONFIG_UPDATED = "CONFIG_UPDATED"
    COMMIT_CREATED = "COMMIT_CREATED"
    BRANCH_CHANGED = "BRANCH_CHANGED"
    MERGE_COMPLETED = "MERGE_COMPLETED"
    PR_CREATED = "PR_CREATED"
    ANALYSIS_REQUESTED = "ANALYSIS_REQUESTED"
    AGENT_RUN_COMPLETED = "AGENT_RUN_COMPLETED"


class MonitorMode(str, Enum):
    MANUAL = "MANUAL"
    SCHEDULED = "SCHEDULED"
    CONTINUOUS = "CONTINUOUS"


@dataclass(frozen=True)
class FileStamp:
    size: int
    mtime_ns: int


class RepositoryRecord(BaseModel):
    id: str
    name: str
    path: str
    technology_tags: list[str] = Field(default_factory=list)
    owners: list[str] = Field(default_factory=list)
    discovered_at: datetime = Field(default_factory=utc_now)


class RepositoryInfo(BaseModel):
    id: str
    name: str
    path: str
    current_branch: str | None
    default_branch: str | None
    latest_commit: str | None
    remote_origin: str | None
    is_dirty: bool
    technology_tags: list[str] = Field(default_factory=list)
    owners: list[str] = Field(default_factory=list)
    discovered_at: datetime


class BranchInfo(BaseModel):
    name: str
    kind: BranchKind
    is_remote: bool
    head_commit: str
    is_current: bool
    is_default: bool


class CommitInfo(BaseModel):
    sha: str
    short_sha: str
    author_name: str
    author_email: str
    authored_at: datetime
    summary: str
    parents: list[str] = Field(default_factory=list)


class ChangedFile(BaseModel):
    path: str
    old_path: str | None = None
    change_type: ChangeType
    area: ChangeArea
    added_lines: int = Field(default=0, ge=0)
    deleted_lines: int = Field(default=0, ge=0)
    modified_lines: int = Field(default=0, ge=0)


class ChangeScopeRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=False)

    repo_path: str = Field(min_length=1, max_length=1024)
    analysis_mode: AnalysisMode = AnalysisMode.PRE_COMMIT
    commit_id: str | None = Field(default=None, max_length=255)
    source_branch: str | None = Field(default=None, max_length=255)
    target_branch: str | None = Field(default=None, max_length=255)
    compare_mode: CompareMode = CompareMode.MERGE_BASE


class ChangeSet(BaseModel):
    repository: str
    analysis_mode: AnalysisMode
    base_ref: str | None = None
    target_ref: str | None = None
    base_sha: str | None = None
    target_sha: str | None = None
    files: list[ChangedFile] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utc_now)

    @computed_field
    @property
    def totals(self) -> dict[str, int]:
        return {
            "files_changed": len(self.files),
            "added_lines": sum(f.added_lines for f in self.files),
            "deleted_lines": sum(f.deleted_lines for f in self.files),
            "modified_lines": sum(f.modified_lines for f in self.files),
        }


class PullRequestRef(BaseModel):
    provider: str
    number: int | None
    ref: str
    head_sha: str


class RefreshResult(BaseModel):
    added: list[str] = Field(default_factory=list)
    removed: list[str] = Field(default_factory=list)
    total: int
    refreshed_at: datetime = Field(default_factory=utc_now)


class ChangeEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    type: EventType
    repository: str
    branch: str | None = None
    file: str | None = None
    occurred_at: datetime = Field(default_factory=utc_now)
    payload: dict[str, Any] = Field(default_factory=dict)
    schema_version: int = SCHEMA_VERSION


class HistoricalSummary(BaseModel):
    repository: str
    ref: str
    commit_count: int
    author_count: int
    insertions: int
    deletions: int
    first_commit_at: datetime | None
    last_commit_at: datetime | None
    top_authors: dict[str, int] = Field(default_factory=dict)
    commits: list[CommitInfo] = Field(default_factory=list)


class RepositoryStatusSummary(BaseModel):
    repository: str
    current_branch: str | None
    latest_commit: str | None
    changed_files: int
    is_dirty: bool
    error: str | None = None


class WorkspaceSummary(BaseModel):
    generated_at: datetime
    repository_count: int
    dirty_repository_count: int
    repositories: list[RepositoryStatusSummary] = Field(default_factory=list)
