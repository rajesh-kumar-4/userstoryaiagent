"""Append-only audit trail for agent runs. Details are redacted and length-limited before storage."""

from __future__ import annotations

import logging
import threading
from collections import deque

from app.core.redaction import redact_text
from app.domain.agents import AuditEvent

logger = logging.getLogger("usai.audit")

MAX_DETAIL_CHARS = 500


class AuditLogger:
    def __init__(self, max_events: int = 5000) -> None:
        self._events: deque[AuditEvent] = deque(maxlen=max_events)
        self._sequence = 0
        self._lock = threading.Lock()

    def record(self, run_id: str, event: str, *, agent: str | None = None, detail: str = "") -> AuditEvent:
        clean = redact_text(detail)[:MAX_DETAIL_CHARS]
        with self._lock:
            self._sequence += 1
            item = AuditEvent(sequence=self._sequence, run_id=run_id, event=event, agent=agent, detail=clean)
            self._events.append(item)
        logger.info("run=%s agent=%s event=%s", run_id, agent or "-", event)
        return item

    def for_run(self, run_id: str) -> list[AuditEvent]:
        with self._lock:
            return [item for item in self._events if item.run_id == run_id]
