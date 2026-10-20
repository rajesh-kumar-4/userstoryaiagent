from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from app.domain.models import ChangeArea, ChangedFile, ChangeType

_STATUS_TO_CHANGE: Mapping[str, ChangeType] = {
    "A": ChangeType.ADDED,
    "C": ChangeType.ADDED,
    "D": ChangeType.DELETED,
    "R": ChangeType.RENAMED,
    "M": ChangeType.MODIFIED,
    "T": ChangeType.MODIFIED,
}


@dataclass
class LineStats:
    added: int = 0
    deleted: int = 0
    modified: int = 0


def _strip_side(raw: str) -> str | None:
    value = raw.rstrip("\t")
    if value == "/dev/null":
        return None
    if value.startswith(("a/", "b/")):
        return value[2:]
    return value


def parse_unified_hunks(patch: str) -> dict[str, LineStats]:
    stats: dict[str, LineStats] = {}
    current: str | None = None
    old_path: str | None = None
    in_hunk = False
    added = 0
    deleted = 0

    def close_hunk() -> None:
        nonlocal added, deleted
        if current is not None and (added or deleted):
            paired = min(added, deleted)
            entry = stats.setdefault(current, LineStats())
            entry.modified += paired
            entry.added += added - paired
            entry.deleted += deleted - paired
        added = 0
        deleted = 0

    for line in patch.splitlines():
        if line.startswith("diff --git "):
            close_hunk()
            in_hunk = False
            current = None
            old_path = None
            continue
        if not in_hunk:
            if line.startswith("--- "):
                old_path = _strip_side(line[4:])
            elif line.startswith("+++ "):
                new_path = _strip_side(line[4:])
                current = new_path if new_path is not None else old_path
                if current is not None:
                    stats.setdefault(current, LineStats())
            elif line.startswith("@@"):
                in_hunk = True
            continue
        if line.startswith("@@"):
            close_hunk()
        elif line.startswith("+"):
            added += 1
        elif line.startswith("-"):
            deleted += 1

    close_hunk()
    return stats


def parse_name_status(output: str, stats: Mapping[str, LineStats], area: ChangeArea) -> list[ChangedFile]:
    tokens = [token for token in output.split("\0") if token]
    files: list[ChangedFile] = []
    index = 0
    while index < len(tokens):
        status = tokens[index][:1]
        if status in ("R", "C"):
            if index + 2 >= len(tokens):
                break
            old_path, new_path = tokens[index + 1], tokens[index + 2]
            index += 3
        else:
            if index + 1 >= len(tokens):
                break
            old_path, new_path = None, tokens[index + 1]
            index += 2
        counts = stats.get(new_path, LineStats())
        files.append(
            ChangedFile(
                path=new_path,
                old_path=old_path,
                change_type=_STATUS_TO_CHANGE.get(status, ChangeType.MODIFIED),
                area=area,
                added_lines=counts.added,
                deleted_lines=counts.deleted,
                modified_lines=counts.modified,
            )
        )
    return files
