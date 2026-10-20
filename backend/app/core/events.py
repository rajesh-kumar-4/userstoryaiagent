from __future__ import annotations

import logging
import threading
from collections import OrderedDict, deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from app.domain.models import ChangeEvent, EventType, utc_now

logger = logging.getLogger(__name__)

EventHandler = Callable[[ChangeEvent], None]


@dataclass(frozen=True)
class DeadLetter:
    event: ChangeEvent
    handler: str
    error: str
    failed_at: datetime


class EventBus:
    def __init__(self, history_size: int = 500, dedupe_window: int = 10_000) -> None:
        self._subscribers: dict[EventType | None, list[EventHandler]] = {}
        self._history: deque[ChangeEvent] = deque(maxlen=history_size)
        self._dead_letters: deque[DeadLetter] = deque(maxlen=history_size)
        self._seen: OrderedDict[str, None] = OrderedDict()
        self._dedupe_window = dedupe_window
        self._lock = threading.RLock()

    def subscribe(self, handler: EventHandler, event_type: EventType | None = None) -> None:
        with self._lock:
            self._subscribers.setdefault(event_type, []).append(handler)

    def publish(self, event: ChangeEvent) -> int:
        with self._lock:
            if event.event_id in self._seen:
                return 0
            self._seen[event.event_id] = None
            while len(self._seen) > self._dedupe_window:
                self._seen.popitem(last=False)
            self._history.append(event)
            handlers = [*self._subscribers.get(None, []), *self._subscribers.get(event.type, [])]

        delivered = 0
        for handler in handlers:
            try:
                handler(event)
                delivered += 1
            except Exception as exc:
                logger.exception("event handler failed for %s", event.type.value)
                with self._lock:
                    self._dead_letters.append(
                        DeadLetter(
                            event=event,
                            handler=getattr(handler, "__qualname__", repr(handler)),
                            error=str(exc),
                            failed_at=utc_now(),
                        )
                    )
        return delivered

    def recent(
        self,
        limit: int = 100,
        repository: str | None = None,
        event_type: EventType | None = None,
    ) -> list[ChangeEvent]:
        with self._lock:
            items = list(self._history)
        matches = [
            event
            for event in reversed(items)
            if (repository is None or event.repository == repository)
            and (event_type is None or event.type == event_type)
        ]
        return matches[:limit]

    def dead_letters(self) -> list[DeadLetter]:
        with self._lock:
            return list(self._dead_letters)
