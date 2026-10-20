"""Role-based access control and API-key authentication.

API keys are configured in plaintext (environment or secret store) but are only kept as
SHA-256 digests in memory. Comparisons use hmac.compare_digest and check every configured key.
"""

import hashlib
import hmac
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum


class Role(str, Enum):
    VIEWER = "VIEWER"
    ANALYST = "ANALYST"
    ADMIN = "ADMIN"


class Permission(str, Enum):
    REPOSITORY_READ = "repository:read"
    DASHBOARD_READ = "dashboard:read"
    SEARCH_READ = "search:read"
    ANALYSIS_RUN = "analysis:run"
    MONITOR_MANAGE = "monitor:manage"


_VIEWER_PERMISSIONS = frozenset({Permission.REPOSITORY_READ, Permission.DASHBOARD_READ, Permission.SEARCH_READ})

ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.VIEWER: _VIEWER_PERMISSIONS,
    Role.ANALYST: _VIEWER_PERMISSIONS | {Permission.ANALYSIS_RUN},
    Role.ADMIN: frozenset(Permission),
}


@dataclass(frozen=True)
class Principal:
    name: str
    role: Role

    def allows(self, permission: Permission) -> bool:
        return permission in ROLE_PERMISSIONS[self.role]


# Used when authentication is disabled (local development). Treat as full access.
ANONYMOUS_ADMIN = Principal(name="anonymous", role=Role.ADMIN)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class Authenticator:
    def __init__(self, *, enabled: bool, api_keys: Mapping[str, Role]) -> None:
        self._enabled = enabled
        self._entries: list[tuple[str, Role]] = [(_digest(key), Role(role)) for key, role in api_keys.items()]

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def key_count(self) -> int:
        return len(self._entries)

    def authenticate(self, presented_key: str | None) -> Principal | None:
        if not self._enabled:
            return ANONYMOUS_ADMIN
        if not presented_key:
            return None
        digest = _digest(presented_key)
        matched: Role | None = None
        for stored_digest, role in self._entries:
            if hmac.compare_digest(stored_digest, digest) and matched is None:
                matched = role
        if matched is None:
            return None
        return Principal(name=f"api-key:{digest[:8]}", role=matched)
