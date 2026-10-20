from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_container
from app.api.security import require_permission
from app.container import AppContainer
from app.core.security.rbac import Permission
from app.domain.models import ChangeEvent, EventType
from app.services.workspace_monitor import MonitorConfig, MonitorStatus

router = APIRouter(tags=["monitoring"])


@router.get("/monitor", response_model=MonitorStatus, dependencies=[Depends(require_permission(Permission.REPOSITORY_READ))])
def monitor_status(container: AppContainer = Depends(get_container)) -> MonitorStatus:
    return container.monitor().status()


@router.put("/monitor", response_model=MonitorStatus, dependencies=[Depends(require_permission(Permission.MONITOR_MANAGE))])
def update_monitor(
    body: MonitorConfig,
    container: AppContainer = Depends(get_container),
) -> MonitorStatus:
    monitor = container.monitor()
    monitor.update_config(body)
    return monitor.status()


@router.post("/monitor/scan", response_model=list[ChangeEvent], dependencies=[Depends(require_permission(Permission.MONITOR_MANAGE))])
def run_monitor_scan(container: AppContainer = Depends(get_container)) -> list[ChangeEvent]:
    return container.monitor().run_cycle()


@router.get("/events", response_model=list[ChangeEvent], dependencies=[Depends(require_permission(Permission.REPOSITORY_READ))])
def list_events(
    limit: int = Query(default=100, ge=1, le=500),
    repository: str | None = Query(default=None, max_length=1024),
    event_type: EventType | None = Query(default=None),
    container: AppContainer = Depends(get_container),
) -> list[ChangeEvent]:
    return container.event_bus().recent(limit=limit, repository=repository, event_type=event_type)
