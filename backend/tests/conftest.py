from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from app.config import Settings
from app.container import AppContainer, build_container
from app.domain.models import MonitorMode
from tests.support import commit_all, git, init_repo, remove_tree, write


@pytest.fixture
def workspace(tmp_path: Path) -> Iterator[Path]:
    root = tmp_path / "workspace"
    root.mkdir()
    yield root
    remove_tree(root)


@pytest.fixture
def platform_root(workspace: Path) -> Path:
    return init_repo(workspace / "userstoryaiagent")


@pytest.fixture
def settings(workspace: Path, platform_root: Path) -> Settings:
    return Settings(
        _env_file=None,
        workspace_root=workspace,
        platform_root=platform_root,
        max_discovery_depth=2,
        monitor_mode=MonitorMode.MANUAL,
        monitor_interval_seconds=30,
        monitor_debounce_seconds=0,
    )


@pytest.fixture
def sample_workspace(workspace: Path, platform_root: Path) -> Path:
    billing = init_repo(workspace / "billing-service")
    write(
        billing / "pom.xml",
        "<project><dependencies><dependency>spring-boot-starter</dependency></dependencies></project>",
    )
    write(billing / "src" / "main" / "App.java", "class App {}\n")
    commit_all(billing, "initial commit")

    git(billing, "checkout", "-b", "feature/PAY-1")
    write(billing / "src" / "main" / "App.java", "class App {\n  int x;\n}\n")
    commit_all(billing, "feature work")
    git(billing, "checkout", "main")

    frontend = init_repo(workspace / "frontend" / "web-app")
    write(frontend / "package.json", '{"dependencies": {"react": "18.0.0"}}')
    write(frontend / "src" / "index.js", "console.log('hi');\n")
    commit_all(frontend, "frontend initial")

    payments = init_repo(workspace / "services" / "payments")
    write(payments / "go.mod", "module payments\n")
    commit_all(payments, "payments initial")

    write(workspace / "not-a-repo" / "readme.txt", "plain folder\n")
    return workspace


@pytest.fixture
def container(settings: Settings, sample_workspace: Path) -> AppContainer:
    app_container = build_container(settings)
    app_container.registry().refresh()
    return app_container
