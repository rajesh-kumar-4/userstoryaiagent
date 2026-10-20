"""Agent 7: summarizes recent history and retrieves similar past changes from RAG."""

from __future__ import annotations

import logging
from typing import Any

from app.agents.base import Agent
from app.agents.context import SharedContext
from app.domain.models import ChangeSet
from app.rag.collections import SIMILARITY_COLLECTIONS
from app.rag.store import RagHit

logger = logging.getLogger(__name__)

HISTORY_LIMIT = 200
MAX_MATCHES = 5
MIN_SIMILARITY = 0.2
MAX_TEXT_CHARS = 240
MAX_QUERY_FILES = 50
MAX_QUERY_SYMBOLS = 50
MAX_QUERY_CHARS = 2000


class HistoryAnalysisAgent(Agent):
    index = 7
    name = "history_analysis"
    description = "Summarizes recent history and retrieves similar past changes from RAG."
    collection = None

    def run(self, ctx: SharedContext) -> dict[str, Any]:
        record = ctx.require_repository()
        change_set = ctx.require_change_set()
        history = self.deps.history.history(record.id, "HEAD", HISTORY_LIMIT)
        query = _query_text(change_set, ctx.output("ast_analysis"), ctx.output("dependency_analysis"))
        matches, warnings = self._similar(query)
        return {
            "commits": history.commit_count,
            "authors": history.author_count,
            "matches": matches,
            "warnings": warnings,
        }

    def _similar(self, query: str) -> tuple[list[dict[str, Any]], list[str]]:
        if not query:
            return [], []
        try:
            hits = self.deps.retriever.search(
                query,
                collections=SIMILARITY_COLLECTIONS,
                top_k=MAX_MATCHES,
                min_similarity=MIN_SIMILARITY,
            )
        except Exception as exc:  # a RAG outage must not fail the analysis
            logger.warning("similarity search unavailable: %s", exc)
            return [], [f"similarity search unavailable ({type(exc).__name__})"]
        return [_match(hit) for hit in hits], []


def _match(hit: RagHit) -> dict[str, Any]:
    return {
        "collection": hit.collection,
        "id": hit.id,
        "similarity": hit.similarity,
        "source_type": str(hit.metadata.get("source_type", "")),
        "text": hit.text[:MAX_TEXT_CHARS],
    }


def _query_text(change_set: ChangeSet, ast_output: dict[str, Any], dependency_output: dict[str, Any]) -> str:
    parts = [change.path for change in change_set.files[:MAX_QUERY_FILES]]
    parts += [str(item.get("name", "")) for item in ast_output.get("symbols", [])[:MAX_QUERY_SYMBOLS]]
    for manifest in dependency_output.get("manifests", []):
        parts += [str(item.get("name", "")) for item in manifest.get("added", [])]
        parts += [str(item.get("name", "")) for item in manifest.get("changed", [])]
    return " ".join(part for part in parts if part)[:MAX_QUERY_CHARS]
