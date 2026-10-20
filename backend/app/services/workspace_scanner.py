from __future__ import annotations

import os
from collections import deque
from collections.abc import Iterable
from pathlib import Path


def is_repository(path: Path) -> bool:
    return (path / ".git").exists()


class WorkspaceScanner:
    def __init__(
        self,
        root: Path,
        max_depth: int,
        ignored_directories: Iterable[str],
        platform_root: Path | None = None,
    ) -> None:
        self.root = root.resolve()
        self._max_depth = max_depth
        self._ignored = frozenset(ignored_directories)
        self._excluded = frozenset({platform_root.resolve()}) if platform_root else frozenset()

    def scan(self) -> list[Path]:
        if not self.root.is_dir():
            return []
        repositories: list[Path] = []
        pending: deque[tuple[Path, int]] = deque([(self.root, 0)])
        while pending:
            directory, depth = pending.popleft()
            if is_repository(directory):
                if directory not in self._excluded:
                    repositories.append(directory)
                continue
            if depth < self._max_depth:
                pending.extend((child, depth + 1) for child in self._child_directories(directory))
        return sorted(repositories)

    def _child_directories(self, directory: Path) -> list[Path]:
        try:
            entries = list(os.scandir(directory))
        except OSError:
            return []
        children: list[Path] = []
        for entry in entries:
            if entry.name.startswith(".") or entry.name in self._ignored:
                continue
            if entry.is_symlink() or not entry.is_dir(follow_symlinks=False):
                continue
            child = directory / entry.name
            if child in self._excluded:
                continue
            children.append(child)
        return children
