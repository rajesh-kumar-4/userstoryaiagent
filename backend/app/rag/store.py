"""ChromaDB persistence and similarity search.

The client is created lazily on first use, so building the container never touches disk.
Every collection is created with cosine space and the hashing embedder. Records are upserted
with deterministic ids, so re-running an analysis replaces its documents instead of duplicating them.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.core.exceptions import RagError
from app.rag.collections import Collection
from app.rag.embeddings import EMBEDDING_MODEL, HashingEmbedder

MAX_TOP_K = 50
Metadata = dict[str, str | int | float | bool]


class VectorDocument(BaseModel):
    id: str = Field(min_length=1, max_length=512)
    text: str = Field(min_length=1)
    metadata: Metadata


class RagHit(BaseModel):
    collection: str
    id: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    similarity: float


class VectorStore:
    def __init__(self, client_factory: Callable[[], Any], embedder: HashingEmbedder | None = None) -> None:
        self._client_factory = client_factory
        self._client: Any = None
        self._embedder = embedder or HashingEmbedder()
        self._handles: dict[str, Any] = {}
        self._lock = threading.RLock()

    def upsert(self, collection: Collection, documents: Sequence[VectorDocument]) -> int:
        unique: dict[str, VectorDocument] = {}
        for document in documents:
            unique[document.id] = document
        if not unique:
            return 0
        values = list(unique.values())
        texts = [document.text for document in values]
        self._handle(collection).upsert(
            ids=[document.id for document in values],
            documents=texts,
            metadatas=[dict(document.metadata) for document in values],
            embeddings=self._embedder.embed(texts),
        )
        return len(values)

    def count(self, collection: Collection) -> int:
        return int(self._handle(collection).count())

    def query(
        self,
        collection: Collection,
        text: str,
        *,
        top_k: int,
        repository: str | None = None,
        source_type: str | None = None,
    ) -> list[RagHit]:
        if not text.strip():
            return []
        handle = self._handle(collection)
        total = int(handle.count())
        if total == 0:
            return []
        clauses: list[dict[str, Any]] = []
        if repository:
            clauses.append({"repository": repository})
        if source_type:
            clauses.append({"source_type": source_type})
        where: dict[str, Any] | None = None
        if len(clauses) == 1:
            where = clauses[0]
        elif clauses:
            where = {"$and": clauses}
        result = handle.query(
            query_embeddings=self._embedder.embed([text]),
            n_results=min(max(1, min(top_k, MAX_TOP_K)), total),
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        hits: list[RagHit] = []
        for doc_id, document, metadata, distance in zip(
            result["ids"][0], result["documents"][0], result["metadatas"][0], result["distances"][0]
        ):
            hits.append(
                RagHit(
                    collection=collection.value,
                    id=doc_id,
                    text=document or "",
                    metadata=dict(metadata or {}),
                    similarity=round(1.0 - float(distance), 4),
                )
            )
        return hits

    def close(self) -> None:
        with self._lock:
            if self._client is not None:
                self._client.clear_system_cache()
            self._client = None
            self._handles.clear()

    def _client_or_create(self) -> Any:
        if self._client is None:
            self._client = self._client_factory()
        return self._client

    def _handle(self, collection: Collection) -> Any:
        with self._lock:
            handle = self._handles.get(collection.value)
            if handle is not None:
                return handle
            handle = self._client_or_create().get_or_create_collection(
                name=collection.value,
                embedding_function=self._embedder,
                metadata={"hnsw:space": "cosine", "embedding_model": EMBEDDING_MODEL},
            )
            stored_model = (handle.metadata or {}).get("embedding_model")
            if stored_model != EMBEDDING_MODEL:
                raise RagError(
                    f"collection {collection.value} was built with embedding model {stored_model!r}; re-index it"
                )
            self._handles[collection.value] = handle
            return handle


def build_vector_store(chroma_path: Path | None, chroma_host: str | None, chroma_port: int) -> VectorStore:
    """HTTP Chroma server when a host is configured, persistent local Chroma when a path is set,
    otherwise an in-process ephemeral client (for development and tests)."""
    import chromadb

    if chroma_host:
        return VectorStore(lambda: chromadb.HttpClient(host=chroma_host, port=chroma_port))
    if chroma_path is None:
        return VectorStore(chromadb.EphemeralClient)

    def open_local() -> Any:
        chroma_path.mkdir(parents=True, exist_ok=True)
        return chromadb.PersistentClient(path=str(chroma_path))

    return VectorStore(open_local)
