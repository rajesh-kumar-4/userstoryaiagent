"""Lexical similarity used for change search.

Deterministic lexical scorer used by the change-search endpoint. Embedding-based search over agent
outputs and historical records lives in app.rag (ChromaDB); this module is not wired to it.
"""

import re
from collections.abc import Iterable

_TOKEN_PATTERN = re.compile(r"[a-z0-9]{2,}")


def tokenize(text: str) -> frozenset[str]:
    return frozenset(_TOKEN_PATTERN.findall(text.lower()))


def query_coverage(query_terms: frozenset[str], document_terms: Iterable[str]) -> float:
    """Fraction of query terms present in the document. Returns 0.0 for an empty query."""
    if not query_terms:
        return 0.0
    return len(query_terms & frozenset(document_terms)) / len(query_terms)
