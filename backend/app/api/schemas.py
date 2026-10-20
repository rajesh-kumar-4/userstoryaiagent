from pydantic import BaseModel, Field

from app.domain.models import AnalysisMode, CompareMode
from app.rag.collections import Collection

# Git refs and SHAs: no leading dash (option injection) and no whitespace or shell metacharacters.
REF_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._/@-]*$"
REF_FIELD = Field(default=None, min_length=1, max_length=255, pattern=REF_PATTERN)
REQUIRED_REF_FIELD = Field(min_length=1, max_length=255, pattern=REF_PATTERN)
REPO_PATH_FIELD = Field(min_length=1, max_length=1024, description="Repository id, name, or path inside the workspace")


class RegisterRepositoryRequest(BaseModel):
    path: str = Field(min_length=1, max_length=1024, description="Repository path inside the workspace")


class RepositoryAnalysisRequest(BaseModel):
    repo_path: str = REPO_PATH_FIELD


class AnalyzeRepositoryRequest(RepositoryAnalysisRequest):
    analysis_mode: AnalysisMode = AnalysisMode.PRE_COMMIT
    commit_id: str | None = Field(default=None, min_length=1, max_length=64, pattern=REF_PATTERN)
    source_branch: str | None = REF_FIELD
    target_branch: str | None = REF_FIELD
    compare_mode: CompareMode = CompareMode.MERGE_BASE


class PostCommitAnalysisRequest(RepositoryAnalysisRequest):
    commit_id: str | None = Field(default=None, min_length=1, max_length=64, pattern=REF_PATTERN)


class BranchAnalysisRequest(RepositoryAnalysisRequest):
    source_branch: str | None = REF_FIELD
    target_branch: str | None = REF_FIELD
    compare_mode: CompareMode = CompareMode.MERGE_BASE


class PullRequestAnalysisRequest(RepositoryAnalysisRequest):
    source_branch: str = REQUIRED_REF_FIELD
    target_branch: str = REQUIRED_REF_FIELD


class ReleaseAnalysisRequest(RepositoryAnalysisRequest):
    source_branch: str = Field(min_length=1, max_length=255, pattern=REF_PATTERN, description="release/* branch")
    target_branch: str | None = REF_FIELD
    compare_mode: CompareMode = CompareMode.MERGE_BASE


class SimilarChangeSearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=2000, description="Free text describing the change")
    repository: str | None = Field(default=None, max_length=1024)
    top_k: int = Field(default=5, ge=1, le=50)


class RagSearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=2000, description="Free text describing the change or risk")
    repository: str | None = Field(default=None, max_length=1024)
    source_type: str | None = Field(default=None, max_length=64, description="Metadata filter, for example historical_commit")
    collections: list[Collection] | None = Field(default=None, min_length=1, description="Defaults to all collections")
    top_k: int = Field(default=5, ge=1, le=50)
    min_similarity: float = Field(default=0.0, ge=0.0, le=1.0)
