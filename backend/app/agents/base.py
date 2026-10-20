"""Agent contract and the dependencies agents receive."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.agents.context import SharedContext
from app.config import Settings
from app.core.llm.base_provider import LLMProvider
from app.core.llm.prompt_manager import PromptManager
from app.rag.collections import Collection
from app.rag.retrieval import Retriever
from app.services.change_scope import ChangeScopeResolver
from app.services.repository_explorer import RepositoryExplorer
from app.services.repository_registry import RepositoryRegistry
from app.services.rule_analyzer import RuleBasedAnalyzer
from app.services.security_scan_service import SecurityScanService
from app.services.workspace_analysis import WorkspaceAnalysisService

MAX_DOCUMENT_CHARS = 4000


@dataclass(frozen=True)
class AgentDeps:
    settings: Settings
    registry: RepositoryRegistry
    explorer: RepositoryExplorer
    change_scope: ChangeScopeResolver
    analyzer: RuleBasedAnalyzer
    security: SecurityScanService
    history: WorkspaceAnalysisService
    retriever: Retriever
    prompts: PromptManager
    llm: LLMProvider | None = None


@dataclass(frozen=True)
class Draft:
    """Text an agent wants indexed in its RAG collection after the run completes."""

    collection: Collection
    text: str
    metadata: dict[str, str | int | float | bool] = field(default_factory=dict)


def compact_json(output: dict[str, Any]) -> str:
    return json.dumps(output, sort_keys=True, default=str)[:MAX_DOCUMENT_CHARS]


class Agent(ABC):
    index: int = -1
    name: str = ""
    description: str = ""
    collection: Collection | None = None

    def __init__(self, deps: AgentDeps) -> None:
        self.deps = deps

    @property
    def tool_name(self) -> str:
        return f"agent_{self.name}"

    @abstractmethod
    def run(self, ctx: SharedContext) -> dict[str, Any]:
        """Return a JSON-serializable output. Raise AgentSkipped when inputs are missing."""

    def documents(self, ctx: SharedContext, output: dict[str, Any]) -> list[Draft]:
        if self.collection is None:
            return []
        return [Draft(collection=self.collection, text=compact_json(output))]
