from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_container
from app.api.schemas import RegisterRepositoryRequest
from app.api.security import require_permission
from app.container import AppContainer
from app.core.security.rbac import Permission
from app.domain.models import (
    BranchInfo,
    ChangeSet,
    CommitInfo,
    HistoricalSummary,
    PullRequestRef,
    RefreshResult,
    RepositoryInfo,
    RepositoryRecord,
)

router = APIRouter(prefix="/repositories", tags=["repositories"])


@router.get(
    "",
    response_model=list[RepositoryInfo],
    dependencies=[Depends(require_permission(Permission.REPOSITORY_READ))],
)
def list_repositories(container: AppContainer = Depends(get_container)) -> list[RepositoryInfo]:
    return container.explorer().list_repositories()


@router.post(
    "/refresh",
    response_model=RefreshResult,
    dependencies=[Depends(require_permission(Permission.ANALYSIS_RUN))],
)
def refresh_repositories(container: AppContainer = Depends(get_container)) -> RefreshResult:
    return container.registry().refresh()


@router.post(
    "/register",
    response_model=RepositoryRecord,
    dependencies=[Depends(require_permission(Permission.ANALYSIS_RUN))],
)
def register_repository(
    body: RegisterRepositoryRequest,
    container: AppContainer = Depends(get_container),
) -> RepositoryRecord:
    return container.registry().resolve(body.path)


# Suffix routes are declared before the greedy path route below.
@router.get(
    "/{repository:path}/branches",
    response_model=list[BranchInfo],
    dependencies=[Depends(require_permission(Permission.REPOSITORY_READ))],
)
def list_branches(repository: str, container: AppContainer = Depends(get_container)) -> list[BranchInfo]:
    return container.explorer().branches(repository)


@router.get(
    "/{repository:path}/commits",
    response_model=list[CommitInfo],
    dependencies=[Depends(require_permission(Permission.REPOSITORY_READ))],
)
def list_commits(
    repository: str,
    ref: str = Query(default="HEAD", max_length=255),
    limit: int = Query(default=50, ge=1, le=500),
    container: AppContainer = Depends(get_container),
) -> list[CommitInfo]:
    return container.explorer().commits(repository, ref, limit)


@router.get(
    "/{repository:path}/status",
    response_model=ChangeSet,
    dependencies=[Depends(require_permission(Permission.REPOSITORY_READ))],
)
def repository_status(repository: str, container: AppContainer = Depends(get_container)) -> ChangeSet:
    return container.explorer().status(repository)


@router.get(
    "/{repository:path}/pull-requests",
    response_model=list[PullRequestRef],
    dependencies=[Depends(require_permission(Permission.REPOSITORY_READ))],
)
def list_pull_requests(repository: str, container: AppContainer = Depends(get_container)) -> list[PullRequestRef]:
    return container.explorer().pull_requests(repository)


@router.get(
    "/{repository:path}/history",
    response_model=HistoricalSummary,
    dependencies=[Depends(require_permission(Permission.REPOSITORY_READ))],
)
def repository_history(
    repository: str,
    ref: str = Query(default="HEAD", max_length=255),
    limit: int = Query(default=100, ge=1, le=500),
    container: AppContainer = Depends(get_container),
) -> HistoricalSummary:
    return container.workspace_analysis().history(repository, ref, limit)


@router.get(
    "/{repository:path}",
    response_model=RepositoryInfo,
    dependencies=[Depends(require_permission(Permission.REPOSITORY_READ))],
)
def describe_repository(repository: str, container: AppContainer = Depends(get_container)) -> RepositoryInfo:
    return container.explorer().describe(repository)
