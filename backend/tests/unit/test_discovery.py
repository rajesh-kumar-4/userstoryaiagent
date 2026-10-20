from pathlib import Path

from app.services.repository_discovery import read_codeowners
from app.services.technology_detection import detect_technologies
from app.services.workspace_scanner import WorkspaceScanner
from tests.support import init_repo, write


def test_technology_detection_reads_manifests(tmp_path: Path):
    write(tmp_path / "package.json", '{"dependencies": {"react": "18.0.0"}}')

    tags = detect_technologies(tmp_path)

    assert "nodejs" in tags
    assert "react" in tags
    assert "java" not in tags


def test_codeowners_wildcard_owner_is_read(tmp_path: Path):
    write(tmp_path / ".github" / "CODEOWNERS", "# comment\n* @org/platform @alice\n")

    assert read_codeowners(tmp_path) == ["@org/platform", "@alice"]


def test_scanner_respects_depth_ignores_and_platform_root(tmp_path: Path):
    root = tmp_path / "ws"
    init_repo(root / "app-a")
    init_repo(root / "group" / "app-b")
    init_repo(root / "deep" / "level" / "app-c")
    init_repo(root / "node_modules" / "ignored")
    init_repo(root / "platform")

    found = WorkspaceScanner(root, max_depth=2, ignored_directories=["node_modules"], platform_root=root / "platform").scan()
    names = sorted(path.relative_to(root.resolve()).as_posix() for path in found)

    assert names == ["app-a", "group/app-b"]


def test_scanner_returns_empty_for_missing_root(tmp_path: Path):
    assert WorkspaceScanner(tmp_path / "missing", 2, []).scan() == []
