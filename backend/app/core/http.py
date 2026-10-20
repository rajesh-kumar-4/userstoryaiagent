"""Shared outbound HTTP helpers."""

from urllib.parse import urlsplit


def validate_base_url(url: str) -> str:
    """Return the URL without a trailing slash, or raise if it is not an absolute http(s) URL."""
    parts = urlsplit(url or "")
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise ValueError("Base URL must be an absolute http(s) URL")
    return url.rstrip("/")
