from __future__ import annotations

import asyncio
import contextlib
import logging
import threading
import time
from collections.abc import Callable
from datetime import datetime

from pydantic import BaseModel, Field

from app.core.events import EventBus
from app.core.exceptions import GitOperationError
from app.domain.models import ChangeEvent, EventType, MonitorMode, utc_now
from app.services.change_detection import ChangeDetectionEngine, RepositorySnapshot
from app.services.repository_registry import RepositoryRegistry

logger = logging.getLogger(__name__)

IDLE_POLL_SECONDS = 1.0


class MonitorConfig(BaseModel):
    mode: MonitorMode = MonitorMode.MANUAL
    interval_seconds: float = Field(default=30.0, ge=1.0, le=86_400.0)
    debounce_seconds: float = Field(default=5.0, ge=0.0, le=3_600.0)


class MonitorStatus(BaseModel):
    config: MonitorConfig
    running: bool
    tracked_repositories: int
    pending_events: int
    last_cycle_at: datetime | None
    repository_errors: dict[str, str] = Field(default_factory=dict)


class WorkspaceMonitor:
    def __init__(
        self,
        registry: RepositoryRegistry,
        detection: ChangeDetectionEngine,
        bus: EventBus,
        config: MonitorConfig,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._registry = registry
        self._detection = detection
        self._bus = bus
        self._config = config
        self._clock = clock
        self._snapshots: dict[str, RepositorySnapshot] = {}
        self._pending: dict[str, list[ChangeEvent]] = {}
        self._pending_since: dict[str, float] = {}
        self._errors: dict[str, str] = {}
        self._last_cycle_at: datetime | None = None
        self._last_scheduled_at: float | None = None
        self._lock = threading.RLock()
        self._task: asyncio.Task[None] | None = None

    @property
    def config(self) -> MonitorConfig:
        with self._lock:
            return self._config

    def update_config(self, config: MonitorConfig) -> None:
        with self._lock:
            self._config = config

    def run_cycle(self) -> list[ChangeEvent]:
        with self._lock:
            self._registry.refresh()
            live: set[str] = set()
            for record in self._registry.all_records():
                live.add(record.id)
                try:
                    snapshot, events = self._detection.detect(record, self._snapshots.get(record.id))
                except GitOperationError as exc:
                    self._errors[record.id] = str(exc)
                    continue
                self._errors.pop(record.id, None)
                self._snapshots[record.id] = snapshot
                if events:
                    self._pending.setdefault(record.id, []).extend(events)
                    self._pending_since[record.id] = self._clock()

            for repo_id in set(self._snapshots) - live:
                del self._snapshots[repo_id]
            for repo_id in set(self._errors) - live:
                del self._errors[repo_id]

            self._last_cycle_at = utc_now()
            if self._config.mode is MonitorMode.SCHEDULED:
                self._request_scheduled_analysis(live)
            return self._flush_due()

    def status(self) -> MonitorStatus:
        with self._lock:
            return MonitorStatus(
                config=self._config,
                running=self._task is not None and not self._task.done(),
                tracked_repositories=len(self._snapshots),
                pending_events=sum(len(events) for events in self._pending.values()),
                last_cycle_at=self._last_cycle_at,
                repository_errors=dict(self._errors),
            )

    async def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run_forever())

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def _run_forever(self) -> None:
        while True:
            config = self.config
            if config.mode is MonitorMode.MANUAL:
                await asyncio.sleep(IDLE_POLL_SECONDS)
                continue
            try:
                await asyncio.to_thread(self.run_cycle)
            except Exception:
                logger.exception("workspace monitor cycle failed")
            await asyncio.sleep(config.interval_seconds)

    def _request_scheduled_analysis(self, repo_ids: set[str]) -> None:
        now = self._clock()
        if self._last_scheduled_at is not None and now - self._last_scheduled_at < self._config.interval_seconds:
            return
        self._last_scheduled_at = now
        for repo_id in sorted(repo_ids):
            self._bus.publish(
                ChangeEvent(type=EventType.ANALYSIS_REQUESTED, repository=repo_id, payload={"reason": "SCHEDULED"})
            )

    def _flush_due(self) -> list[ChangeEvent]:
        now = self._clock()
        flushed: list[ChangeEvent] = []
        for repo_id in list(self._pending):
            if now - self._pending_since[repo_id] < self._config.debounce_seconds:
                continue
            events = self._pending.pop(repo_id)
            del self._pending_since[repo_id]
            for event in events:
                self._bus.publish(event)
            flushed.extend(events)
        return flushed
