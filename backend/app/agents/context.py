"""Shared run state passed between agents, and the bounded store of finished runs."""

from __future__ import annotations

import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from app.core.exceptions import AgentRunNotFoundError
from app.domain.agents import AgentRun, AgentTrace
from app.domain.models import AnalysisMode, ChangeScopeRequest, ChangeSet, RepositoryRecord, utc_now


class AgentSkipped(Exception):
    """An agent's inputs are unavailable. The workflow records SKIPPED and continues."""


@dataclass
class SharedContext:
    run_id: str
    request: ChangeScopeRequest
    started_at: datetime = field(default_factory=utc_now)
    repository: RepositoryRecord | None = None
    change_set: ChangeSet | None = None
    outputs: dict[str, dict[str, Any]] = field(default_factory=dict)
    traces: dict[str, AgentTrace] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @property
    def analysis_mode(self) -> AnalysisMode:
        return self.request.analysis_mode

    def require_repository(self) -> RepositoryRecord:
        if self.repository is None:
            raise AgentSkipped("repository not resolved")
        return self.repository

    def require_change_set(self) -> ChangeSet:
        if self.change_set is None:
            raise AgentSkipped("change set not resolved")
        return self.change_set

    def output(self, agent: str) -> dict[str, Any]:
        return self.outputs.get(agent, {})


class ContextManager:
    """Holds active run contexts and keeps the most recent finished runs (bounded)."""

    def __init__(self, history_size: int = 200) -> None:
        self._history_size = history_size
        self._active: dict[str, SharedContext] = {}
        self._finished: OrderedDict[str, AgentRun] = OrderedDict()
        self._lock = threading.RLock()

    def create(self, request: ChangeScopeRequest) -> SharedContext:
        ctx = SharedContext(run_id=str(uuid4()), request=request)
        with self._lock:
            self._active[ctx.run_id] = ctx
        return ctx

    def get(self, run_id: str) -> SharedContext:
        with self._lock:
            ctx = self._active.get(run_id)
        if ctx is None:
            raise AgentRunNotFoundError(f"agent run {run_id} is not active")
        return ctx

    def record(
        self,
        run_id: str,
        trace: AgentTrace,
        output: dict[str, Any] | None,
        warnings: list[str],
    ) -> None:
        ctx = self.get(run_id)
        with self._lock:
            ctx.traces[trace.agent] = trace
            if output is not None:
                ctx.outputs[trace.agent] = output
            ctx.warnings.extend(warnings)

    def add_warning(self, run_id: str, message: str) -> None:
        ctx = self.get(run_id)
        with self._lock:
            ctx.warnings.append(message)

    def finish(self, run: AgentRun) -> None:
        with self._lock:
            self._active.pop(run.run_id, None)
            self._finished[run.run_id] = run
            while len(self._finished) > self._history_size:
                self._finished.popitem(last=False)

    def get_run(self, run_id: str) -> AgentRun:
        with self._lock:
            run = self._finished.get(run_id)
        if run is None:
            raise AgentRunNotFoundError(f"agent run {run_id} not found")
        return run
