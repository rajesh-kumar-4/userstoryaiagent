import re
from urllib.parse import urlsplit, urlunsplit

REDACTED = "***REDACTED***"

_KEY_VALUE_PATTERN = re.compile(r"(?i)\b(password|passwd|token|secret|api[_-]?key)\b(\s*[=:]\s*)\S+")
_TOKEN_PATTERNS = (
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}\b"),
)


def redact_url(url: str) -> str:
    parts = urlsplit(url)
    if "@" not in parts.netloc:
        return url
    host = parts.netloc.rsplit("@", 1)[1]
    return urlunsplit((parts.scheme, host, parts.path, parts.query, parts.fragment))


def redact_text(text: str) -> str:
    redacted = _KEY_VALUE_PATTERN.sub(lambda match: f"{match.group(1)}{match.group(2)}{REDACTED}", text)
    for pattern in _TOKEN_PATTERNS:
        redacted = pattern.sub(REDACTED, redacted)
    return redacted
