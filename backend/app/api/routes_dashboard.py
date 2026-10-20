"""Dashboard endpoints: portfolio summary, per-repository risk, and daily trends."""

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_container
from app.api.security import require_permission
from app.container import AppContainer
from app.core.security.rbac import Permission
from app.domain.analysis import DashboardSummary, RepositoryRisk, TrendPoint

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get(
    "/summary",
    response_model=DashboardSummary,
    dependencies=[Depends(require_permission(Permission.DASHBOARD_READ))],
)
def dashboard_summary(container: AppContainer = Depends(get_container)) -> DashboardSummary:
    return container.dashboard().summary()


@router.get(
    "/repositories",
    response_model=list[RepositoryRisk],
    dependencies=[Depends(require_permission(Permission.DASHBOARD_READ))],
)
def dashboard_repositories(container: AppContainer = Depends(get_container)) -> list[RepositoryRisk]:
    return container.dashboard().repository_risk()


@router.get(
    "/trends",
    response_model=list[TrendPoint],
    dependencies=[Depends(require_permission(Permission.DASHBOARD_READ))],
)
def dashboard_trends(
    days: int = Query(default=30, ge=1, le=365),
    container: AppContainer = Depends(get_container),
) -> list[TrendPoint]:
    return container.dashboard().trends(days)
