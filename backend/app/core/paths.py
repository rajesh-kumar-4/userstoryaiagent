from pathlib import Path

from app.core.exceptions import PathOutsideWorkspaceError


def ensure_within(root: Path, candidate: Path) -> Path:
    resolved = candidate.resolve()
    base = root.resolve()
    if resolved != base and base not in resolved.parents:
        raise PathOutsideWorkspaceError(f"Path is outside the workspace: {candidate}")
    return resolved
