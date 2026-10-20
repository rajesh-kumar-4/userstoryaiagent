"""Ingestion of historical and external records into RAG collections.

Sources are JSON arrays or JSON Lines files under the RAG sources directory. Each record has a
source_type, id, repository, text, and an optional flat metadata object. Scalar metadata only.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from app.config import Settings
from app.core.exceptions import InvalidRequestError
from app.core.paths import ensure_within
from app.domain.models import CommitInfo
from app.rag.collections import SOURCE_COLLECTIONS, Collection, SourceType
from app.rag.store import VectorDocument, VectorStore

MAX_RECORDS = 10_000
MAX_TEXT_CHARS = 8_000
MAX_FILE_BYTES = 5 * 1024 * 1024
_SUFFIXES = frozenset({".json", ".jsonl"})


class RagRecord(BaseModel):
    source_type: SourceType
    id: str = Field(min_length=1, max_length=256)
    repository: str = Field(min_length=1, max_length=1024)
    text: str = Field(min_length=1, max_length=MAX_TEXT_CHARS)
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)


class IngestResult(BaseModel):
    records: int
    indexed: dict[str, int]


def to_document(record: RagRecord) -> tuple[Collection, VectorDocument]:
    metadata = {
        **record.metadata,
        "source_type": record.source_type.value,
        "repository": record.repository,
        "record_id": record.id,
    }
    document = VectorDocument(
        id=f"{record.source_type.value}:{record.id}",
        text=record.text,
        metadata=metadata,
    )
    return SOURCE_COLLECTIONS[record.source_type], document


def records_from_commits(repository: str, commits: Sequence[CommitInfo]) -> list[RagRecord]:
    return [
        RagRecord(
            source_type=SourceType.HISTORICAL_COMMIT,
            id=commit.sha,
            repository=repository,
            text=f"{commit.summary} (author {commit.author_name})",
            metadata={"commit": commit.short_sha, "authored_at": commit.authored_at.isoformat()},
        )
        for commit in commits
        if commit.summary.strip()
    ]


def parse_records(content: str, suffix: str) -> list[RagRecord]:
    try:
        if suffix == ".jsonl":
            raw: object = [json.loads(line) for line in content.splitlines() if line.strip()]
        else:
            raw = json.loads(content)
    except json.JSONDecodeError as exc:
        raise InvalidRequestError(f"invalid JSON in source file: {exc.msg}") from exc
    if not isinstance(raw, list):
        raise InvalidRequestError("source file must contain an array of records")
    if len(raw) > MAX_RECORDS:
        raise InvalidRequestError(f"source file exceeds {MAX_RECORDS} records")
    try:
        return [RagRecord.model_validate(item) for item in raw]
    except ValidationError as exc:
        first = exc.errors()[0]
        location = ".".join(str(part) for part in first.get("loc", ()))
        raise InvalidRequestError(f"invalid source record at {location or 'record'}: {first.get('msg')}") from exc


class RagIngestor:
    def __init__(self, store: VectorStore, sources_root: Path) -> None:
        self._store = store
        self._root = sources_root

    def ingest_file(self, relative_path: str) -> IngestResult:
        candidate = ensure_within(self._root, self._root / relative_path)
        if candidate.suffix.lower() not in _SUFFIXES:
            raise InvalidRequestError("source file must be .json or .jsonl")
        if not candidate.is_file():
            raise InvalidRequestError("source file not found")
        if candidate.stat().st_size > MAX_FILE_BYTES:
            raise InvalidRequestError("source file exceeds 5 MB")
        records = parse_records(candidate.read_text(encoding="utf-8"), candidate.suffix.lower())
        return self.ingest_records(records)

    def ingest_records(self, records: Sequence[RagRecord]) -> IngestResult:
        grouped: dict[Collection, list[VectorDocument]] = {}
        for record in records:
            collection, document = to_document(record)
            grouped.setdefault(collection, []).append(document)
        indexed = {collection.value: self._store.upsert(collection, documents) for collection, documents in grouped.items()}
        return IngestResult(records=len(records), indexed=indexed)


def build_ingestor(settings: Settings, store: VectorStore) -> RagIngestor:
    root = settings.rag_sources_dir or settings.workspace_root / "rag-sources"
    return RagIngestor(store, root)
