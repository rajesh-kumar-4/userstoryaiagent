from typing import Any

from fastapi import APIRouter, Body, Depends

from app.api.dependencies import get_container
from app.api.security import require_permission
from app.container import AppContainer
from app.core.security.rbac import Permission
from app.mcp.server import handle_message

router = APIRouter(tags=["system"])


@router.get("/health")
def health(container: AppContainer = Depends(get_container)) -> dict[str, Any]:
    return {"status": "ok", "repositories": len(container.registry().all_records())}


@router.post("/mcp", dependencies=[Depends(require_permission(Permission.REPOSITORY_READ))])
def mcp_endpoint(
    message: Any = Body(...),
    container: AppContainer = Depends(get_container),
) -> dict[str, Any] | None:
    response = handle_message(container.tool_registry(), message)
    return response
