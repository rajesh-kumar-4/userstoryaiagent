"""MCP tools for RAG search, history indexing, and source ingestion."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any, TypeVar

from app.mcp.registry import ToolArgumentError, ToolRegistry
from app.rag.collections import Collection
from app.rag.ingest import records_from_commits

if TYPE_CHECKING:
    from app.container import AppContainer

MAX_HISTORY_LIMIT = 500
MAX_TOP_K = 50
_E = TypeVar("_E", bound=Enum)


def _schema(properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {"type": "object", "properties": properties, "required": required, "additionalProperties": False}


_COLLECTION_NAMES = [collection.value for collection in Collection]
_SEARCH_SCHEMA = _schema(
    {
        "query": {"type": "string", "minLength": 2, "maxLength": 2000},
        "repository": {"type": "string", "maxLength": 1024},
        "source_type": {"type": "string", "maxLength": 64},
        "collections": {"type": "array", "items": {"type": "string", "enum": _COLLECTION_NAMES}, "minItems": 1},
        "top_k": {"type": "integer", "minimum": 1, "maximum": MAX_TOP_K},
    },
    ["query"],
)
_INDEX_HISTORY_SCHEMA = _schema(
    {
        "repository": {"type": "string", "minLength": 1, "maxLength": 1024},
        "limit": {"type": "integer", "minimum": 1, "maximum": MAX_HISTORY_LIMIT},
    },
    ["repository"],
)
_INGEST_SCHEMA = _schema({"path": {"type": "string", "minLength": 1, "maxLength": 512}}, ["path"])


def register_rag_tools(tools: ToolRegistry, container: AppContainer) -> None:
    tools.register(
        "rag_search",
        "Searches indexed RAG collections for similar historical changes, risks, and stories.",
        _SEARCH_SCHEMA,
        lambda args: _search(container, args),
    )
    tools.register(
        "rag_index_history",
        "Indexes recent commit summaries of a repository into the git_analysis collection.",
        _INDEX_HISTORY_SCHEMA,
        lambda args: _index_history(container, args),
    )
    tools.register(
        "rag_ingest_sources",
        "Ingests a JSON or JSONL source file from the RAG sources directory.",
        _INGEST_SCHEMA,
        lambda args: _ingest(container, args),
    )


def _search(container: AppContainer, args: dict[str, Any]) -> dict[str, Any]:
    query = _required_text(args, "query", 2000)
    names = args.get("collections") or _COLLECTION_NAMES
    collections = [_enum(Collection, name, "collections") for name in names]
    top_k = min(max(int(args.get("top_k") or 5), 1), MAX_TOP_K)
    hits = container.retriever().search(
        query,
        collections=collections,
        top_k=top_k,
        repository=args.get("repository") or None,
        source_type=args.get("source_type") or None,
    )
    return {"hits": [hit.model_dump() for hit in hits]}


def _index_history(container: AppContainer, args: dict[str, Any]) -> dict[str, Any]:
    repository = _required_text(args, "repository", 1024)
    limit = min(max(int(args.get("limit") or 100), 1), MAX_HISTORY_LIMIT)
    explorer = container.explorer()
    info = explorer.describe(repository)
    commits = explorer.commits(info.id, "HEAD", limit)
    result = container.rag_ingestor().ingest_records(records_from_commits(info.id, commits))
    return result.model_dump()


def _ingest(container: AppContainer, args: dict[str, Any]) -> dict[str, Any]:
    path = _required_text(args, "path", 512)
    return container.rag_ingestor().ingest_file(path).model_dump()


def _required_text(args: dict[str, Any], key: str, max_length: int) -> str:
    value = args.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ToolArgumentError(f"Argument '{key}' is required")
    if len(value) > max_length:
        raise ToolArgumentError(f"Argument '{key}' exceeds {max_length} characters")
    return value.strip()


def _enum(enum_type: type[_E], value: Any, key: str) -> _E:
    try:
        return enum_type(value)
    except ValueError as exc:
        raise ToolArgumentError(f"Argument '{key}' contains an unsupported value: {value}") from exc
