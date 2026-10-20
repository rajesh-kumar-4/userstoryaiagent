"""Deterministic hashing embeddings for the RAG layer.

Feature hashing over identifier-aware unigrams and bigrams. No model download is needed, the same text
produces the same vector in every process, and vectors are L2-normalized for cosine similarity.
The model id is stored in each collection's metadata; a mismatch means the collection must be re-indexed.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Sequence
from typing import Any

EMBEDDING_MODEL = "usai-hashing-v1"
DIMENSIONS = 384

_WORD = re.compile(r"[A-Za-z0-9]+")
_CAMEL_PART = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|[0-9]+")
_BIGRAM_WEIGHT = 0.5


def tokenize(text: str) -> list[str]:
    """Split on non-alphanumerics and camelCase/snake boundaries, lowercased."""
    tokens: list[str] = []
    for word in _WORD.findall(text):
        tokens.extend(part.lower() for part in _CAMEL_PART.findall(word))
    return tokens


def _bucket(feature: str) -> tuple[int, float]:
    digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
    index = int.from_bytes(digest[:4], "big") % DIMENSIONS
    sign = 1.0 if digest[4] & 1 else -1.0
    return index, sign


def embed_text(text: str) -> list[float]:
    tokens = tokenize(text)
    vector = [0.0] * DIMENSIONS
    if not tokens:
        vector[0] = 1.0
        return vector
    features = [(token, 1.0) for token in tokens]
    features += [(f"{left} {right}", _BIGRAM_WEIGHT) for left, right in zip(tokens, tokens[1:])]
    for feature, weight in features:
        index, sign = _bucket(feature)
        vector[index] += sign * weight
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        vector[0] = 1.0
        return vector
    return [value / norm for value in vector]


class HashingEmbedder:
    """Implements the ChromaDB embedding-function protocol without network or model files."""

    def __call__(self, input: Sequence[str]) -> list[list[float]]:
        return self.embed(input)

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [embed_text(text) for text in texts]

    @staticmethod
    def name() -> str:
        return EMBEDDING_MODEL

    def get_config(self) -> dict[str, Any]:
        return {"dimensions": DIMENSIONS}

    @staticmethod
    def build_from_config(config: dict[str, Any]) -> HashingEmbedder:
        return HashingEmbedder()

    @staticmethod
    def validate_config(config: dict[str, Any]) -> None:
        if config.get("dimensions", DIMENSIONS) != DIMENSIONS:
            raise ValueError(f"{EMBEDDING_MODEL} uses {DIMENSIONS} dimensions")

    def validate_config_update(self, old_config: dict[str, Any], new_config: dict[str, Any]) -> None:
        self.validate_config(new_config)

    def default_space(self) -> str:
        return "cosine"

    def supported_spaces(self) -> list[str]:
        return ["cosine", "l2", "ip"]
