"""FastAPI dependencies that enforce API-key authentication and RBAC permissions."""

from fastapi import HTTPException, Header, Request

from app.core.security.rbac import Permission, Principal

API_KEY_HEADER = "X-API-Key"


def require_permission(permission: Permission):
    """Return a dependency that authenticates the API key and checks the permission."""

    def dependency(
        request: Request,
        x_api_key: str | None = Header(default=None, alias=API_KEY_HEADER),
    ) -> Principal:
        authenticator = request.app.state.container.authenticator()
        principal = authenticator.authenticate(x_api_key)
        if principal is None:
            raise HTTPException(
                status_code=401,
                detail="A valid API key is required",
                headers={"WWW-Authenticate": "ApiKey"},
            )
        if not principal.allows(permission):
            raise HTTPException(status_code=403, detail=f"Missing permission: {permission.value}")
        request.state.principal = principal
        return principal

    return dependency
