from __future__ import annotations

from app.domain.branching import classify_branch
from app.domain.models import BranchInfo
from app.infrastructure.git.git_repository import GitRepository


class BranchDiscoveryService:
    def list_branches(self, repo: GitRepository) -> list[BranchInfo]:
        current = repo.current_branch()
        default = repo.default_branch()
        local = repo.local_branches()
        local_names = {name for name, _ in local}

        branches = [
            BranchInfo(
                name=name,
                kind=classify_branch(name),
                is_remote=False,
                head_commit=sha,
                is_current=name == current,
                is_default=name == default,
            )
            for name, sha in local
        ]
        branches.extend(
            BranchInfo(
                name=name,
                kind=classify_branch(name),
                is_remote=True,
                head_commit=sha,
                is_current=False,
                is_default=name == default,
            )
            for name, sha in repo.remote_branches()
            if name not in local_names
        )
        return sorted(branches, key=lambda branch: (branch.is_remote, branch.name))
