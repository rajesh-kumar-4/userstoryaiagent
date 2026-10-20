from app.core.security.rbac import ANONYMOUS_ADMIN, Authenticator, Permission, Principal, Role


def test_disabled_authenticator_grants_admin_without_key():
    authenticator = Authenticator(enabled=False, api_keys={})

    principal = authenticator.authenticate(None)

    assert principal == ANONYMOUS_ADMIN
    assert principal.allows(Permission.MONITOR_MANAGE)


def test_enabled_authenticator_rejects_missing_empty_and_unknown_keys():
    authenticator = Authenticator(enabled=True, api_keys={"viewer-key": Role.VIEWER})

    assert authenticator.authenticate(None) is None
    assert authenticator.authenticate("") is None
    assert authenticator.authenticate("wrong-key") is None


def test_valid_key_resolves_role_without_exposing_the_key():
    authenticator = Authenticator(enabled=True, api_keys={"analyst-key": Role.ANALYST})

    principal = authenticator.authenticate("analyst-key")

    assert principal is not None
    assert principal.role is Role.ANALYST
    assert "analyst-key" not in principal.name


def test_role_permissions_are_hierarchical():
    viewer = Principal(name="viewer", role=Role.VIEWER)
    analyst = Principal(name="analyst", role=Role.ANALYST)
    admin = Principal(name="admin", role=Role.ADMIN)

    assert viewer.allows(Permission.REPOSITORY_READ)
    assert not viewer.allows(Permission.ANALYSIS_RUN)
    assert analyst.allows(Permission.ANALYSIS_RUN)
    assert not analyst.allows(Permission.MONITOR_MANAGE)
    assert all(admin.allows(permission) for permission in Permission)


def test_key_count_and_enabled_flag_are_reported():
    authenticator = Authenticator(enabled=True, api_keys={"a-key": Role.VIEWER, "b-key": Role.ADMIN})

    assert authenticator.enabled is True
    assert authenticator.key_count == 2
