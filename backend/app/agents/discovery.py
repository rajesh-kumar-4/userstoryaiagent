"""Agent 0: resolves the requested repository and its current Git state."""

from __future__ import annotations

from typing import Any

from app.agents.base import Agent
from app.agents.context import SharedContext
from app.rag.collections import Collection


class RepositoryDiscoveryAgent(Agent):
    index = 0
    name = "repository_discovery"
    description = "Resolves the requested repository and its current Git state."
    collection = Collection.REPOSITORIES

    def run(self, ctx: SharedContext) -> dict[str, Any]:
        record = self.deps.registry.resolve(ctx.request.repo_path)
        ctx.repository = record
        return self.deps.explorer.describe(record.id).model_dump(mode="json")
