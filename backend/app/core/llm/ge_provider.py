"""Capgemini Generative Engine provider.

The implementation lives in `openai_provider.py` because GE exposes an OpenAI-compatible
chat endpoint. This module re-exports it under its own name for discoverability.
"""

from app.core.llm.openai_provider import GenerativeEngineProvider

__all__ = ["GenerativeEngineProvider"]
