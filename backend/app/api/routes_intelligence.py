from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_container
from app.api.security import require_permission
from app.container import AppContainer
from app.core.security.rbac import Permission
from app.domain.models import ChangeScopeRequest, ChangeSet, WorkspaceSummary

router = APIRouter(tags=["intelligence"])


@router.post(
    "/change-scope",
    response_model=ChangeSet,
    dependencies=[Depends(require_permission(Permission.ANALYSIS_RUN))],
)
def resolve_change_scope(
    body: ChangeScopeRequest,
    container: AppContainer = Depends(get_container),
) -> ChangeSet:
    return container.change_scope().resolve(body)


@router.get(
    "/workspace/summary",
    response_model=WorkspaceSummary,
    dependencies=[Depends(require_permission(Permission.REPOSITORY_READ))],
)
def workspace_summary(container: AppContainer = Depends(get_container)) -> WorkspaceSummary:
    return container.workspace_analysis().summary()
