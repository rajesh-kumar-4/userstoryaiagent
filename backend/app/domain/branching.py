from app.domain.models import BranchKind

_PREFIXES: tuple[tuple[str, BranchKind], ...] = (
    ("release/", BranchKind.RELEASE),
    ("feature/", BranchKind.FEATURE),
    ("bugfix/", BranchKind.BUGFIX),
    ("hotfix/", BranchKind.HOTFIX),
)


def classify_branch(name: str) -> BranchKind:
    if name in ("main", "master"):
        return BranchKind.MAIN
    if name == "develop":
        return BranchKind.DEVELOP
    for prefix, kind in _PREFIXES:
        if name.startswith(prefix):
            return kind
    return BranchKind.OTHER
