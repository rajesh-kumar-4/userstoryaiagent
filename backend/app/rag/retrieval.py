"""Retrieval strategy: query each collection, merge by similarity, and keep the best hits."""

from __future__ import annotations

from collections.abc import Sequence

from app.rag.collections import Collection
from app.rag.store import RagHit, VectorStore


class Retriever:
    def __init__(self, store: VectorStore) -> None:
        self._store = store

    def search(
        self,
        text: str,
        *,
        collections: Sequence[Collection],
        top_k: int = 5,
        repository: str | None = None,
        source_type: str | None = None,
        min_similarity: float = 0.0,
    ) -> list[RagHit]:
        hits: list[RagHit] = []
        for collection in collections:
            hits.extend(
                self._store.query(
                    collection,
                    text,
                    top_k=top_k,
                    repository=repository,
                    source_type=source_type,
                )
            )
        kept = [hit for hit in hits if hit.similarity >= min_similarity]
        kept.sort(key=lambda hit: (-hit.similarity, hit.collection, hit.id))
        return kept[:top_k]
