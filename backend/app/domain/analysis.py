"""Domain models for analysis reports, criticality, similarity search, and dashboards."""

from datetime import datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field

from app.domain.models import AnalysisMode, utc_now


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


SEVERITY_WEIGHTS: dict[Severity, int] = {
    Severity.LOW: 5,
    Severity.MEDIUM: 15,
    Severity.HIGH: 30,
    Severity.CRITICAL: 50,
}


def level_for_score(score: int) -> Severity:
    if score >= 80:
        return Severity.CRITICAL
    if score >= 50:
        return Severity.HIGH
    if score >= 20:
        return Severity.MEDIUM
    return Severity.LOW


class Finding(BaseModel):
    finding_id: str
    category: str
    severity: Severity
    title: str
    detail: str = ""
    file: str | None = None
    line: int | None = None
    source: str = "rule"


class AnalysisReport(BaseModel):
    analysis_id: str = Field(default_factory=lambda: str(uuid4()))
    repository: str
    analysis_mode: AnalysisMode
    commit_id: str | None = None
    base_sha: str | None = None
    target_sha: str | None = None
    changed_files: list[str] = Field(default_factory=list)
    totals: dict[str, int] = Field(default_factory=dict)
    findings: list[Finding] = Field(default_factory=list)
    risk_score: int = Field(ge=0, le=100)
    risk_level: Severity
    summary: str
    summary_source: str = Field(description="'rule_based' or 'llm'")
    llm_provider: str | None = None
    security_sources: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utc_now)


class CriticalityReport(BaseModel):
    repository: str
    score: int = Field(ge=0, le=100)
    level: Severity
    factors: dict[str, int]
    rationale: str
    rationale_source: str
    generated_at: datetime = Field(default_factory=utc_now)


class SimilarChange(BaseModel):
    analysis_id: str
    repository: str
    analysis_mode: AnalysisMode
    commit_id: str | None = None
    risk_level: Severity
    similarity: float = Field(ge=0.0, le=1.0)
    matched_terms: list[str] = Field(default_factory=list)
    summary: str


class DashboardSummary(BaseModel):
    registered_repositories: int
    analyzed_repositories: int
    total_analyses: int
    analyses_by_mode: dict[str, int]
    risk_distribution: dict[str, int]
    average_risk_score: float
    last_analysis_at: datetime | None = None
    generated_at: datetime = Field(default_factory=utc_now)


class RepositoryRisk(BaseModel):
    repository: str
    analysis_count: int
    latest_risk_score: int
    latest_risk_level: Severity
    latest_analysis_at: datetime


class TrendPoint(BaseModel):
    date: str
    analyses: int
    average_risk_score: float
