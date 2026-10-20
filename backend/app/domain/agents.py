"""Agent workflow models: status values, per-agent traces, audit events, and stored run records."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.domain.models import AnalysisMode, utc_now


class AgentStatus(str, Enum):
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"


class RunStatus(str, Enum):
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class AgentDescriptor(BaseModel):
    index: int
    name: str
    tool: str
    description: str
    collection: str | None = None


class AgentTrace(BaseModel):
    agent: str
    index: int
    status: AgentStatus
    duration_ms: int = Field(default=0, ge=0)
    message: str = ""


class AuditEvent(BaseModel):
    sequence: int
    run_id: str
    event: str
    agent: str | None = None
    detail: str = ""
    occurred_at: datetime = Field(default_factory=utc_now)


class AgentRun(BaseModel):
    run_id: str
    repository: str | None = None
    analysis_mode: AnalysisMode
    status: RunStatus
    agents: list[AgentTrace] = Field(default_factory=list)
    outputs: dict[str, dict[str, Any]] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    audit: list[AuditEvent] = Field(default_factory=list)
    started_at: datetime
    finished_at: datetime | None = None
