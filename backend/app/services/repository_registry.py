from __future__ import annotations

import logging
import threading
from pathlib import Path

from app.core.events import EventBus
from app.core.exceptions import InvalidRequestError, RepositoryNotFoundError
from app.core.paths import ensure_within
from app.domain.models import ChangeEvent, EventType, RefreshResult, RepositoryRecord
from app.services.repository_discovery import RepositoryDiscoveryEngine

logger = logging.getLogger(__name__)


class RepositoryRegistry:
    def __init__(self, discovery: RepositoryDiscoveryEngine, bus: EventBus) -> None:
        self._discovery = discovery
        self._bus = bus
        self._records: dict[str, RepositoryRecord] = {}
        self._lock = threading.RLock()

    def refresh(self) -> RefreshResult:
        discovered = {record.id: record for record in self._discovery.discover()}
        added: list[RepositoryRecord] = []
        removed: list[str] = []
        with self._lock:
            for repo_id, record in discovered.items():
                existing = self._records.get(repo_id)
                if existing is None:
                    added.append(record)
                    self._records[repo_id] = record
                else:
                    self._records[repo_id] = record.model_copy(update={"discovered_at": existing.discovered_at})
            for repo_id in [repo_id for repo_id in self._records if repo_id not in discovered]:
                del self._records[repo_id]
                removed.append(repo_id)
            total = len(self._records)

        for record in added:
            self._announce(EventType.REPOSITORY_DISCOVERED, record)
        for repo_id in removed:
            self._bus.publish(ChangeEvent(type=EventType.REPOSITORY_REMOVED, repository=repo_id))
        return RefreshResult(added=[record.id for record in added], removed=removed, total=total)

    def register(self, path: Path) -> RepositoryRecord:
        record = self._discovery.build_record(path)
        with self._lock:
            existing = self._records.get(record.id)
            is_new = existing is None
            if existing is not None:
                record = record.model_copy(update={"discovered_at": existing.discovered_at})
            self._records[record.id] = record
        if is_new:
            self._announce(EventType.REPOSITORY_DISCOVERED, record)
        return record

    def get(self, identifier: str) -> RepositoryRecord | None:
        with self._lock:
            if identifier in self._records:
                return self._records[identifier]
            matches = [record for record in self._records.values() if record.name == identifier]
        if len(matches) > 1:
            raise InvalidRequestError(f"Repository name '{identifier}' is ambiguous; use the repository id")
        return matches[0] if matches else None

    def resolve(self, identifier: str) -> RepositoryRecord:
        record = self.get(identifier)
        if record is not None:
            return record
        candidate = Path(identifier)
        if not candidate.is_absolute():
            candidate = self._discovery.root / candidate
        resolved = ensure_within(self._discovery.root, candidate)
        if not (resolved / ".git").exists():
            raise RepositoryNotFoundError(f"No repository found for '{identifier}'")
        return self.register(resolved)

    def all_records(self) -> list[RepositoryRecord]:
        with self._lock:
            return sorted(self._records.values(), key=lambda record: record.id)

    def _announce(self, event_type: EventType, record: RepositoryRecord) -> None:
        self._bus.publish(
            ChangeEvent(
                type=event_type,
                repository=record.id,
                payload={"name": record.name, "path": record.path, "technology_tags": record.technology_tags},
            )
        )
