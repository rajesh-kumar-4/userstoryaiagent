"""Analysis orchestration: change scope, rules, security findings, LLM narrative, persistence, and events.

The rule-based analyzer is the orchestrator for /analyze-* endpoints. The ten-agent LangGraph workflow
(app.agents, exposed at /agent-runs) runs separately and shares the analyzer and security scanners.
"""

import logging
from dataclasses import dataclass, field

from app.core.events import EventBus
from app.core.exceptions import LLMProviderError
from app.core.llm.base_provider import LLMProvider
from app.core.llm.prompt_manager import PromptError, PromptManager
from app.core.telemetry import get_tracer
from app.domain.analysis import (
    SEVERITY_WEIGHTS,
    AnalysisReport,
    CriticalityReport,
    Finding,
    Severity,
    level_for_score,
)
from app.domain.models import ChangeEvent, ChangeScopeRequest, ChangeSet, EventType
from app.services.analysis_store import AnalysisStore
from app.services.change_scope import ChangeScopeResolver
from app.services.repository_registry import RepositoryRegistry
from app.services.rule_analyzer import RuleBasedAnalyzer, score_findings
from app.services.security_scan_service import SecurityScanService
from app.services.workspace_analysis import WorkspaceAnalysisService

logger = logging.getLogger(__name__)

MAX_CHANGED_FILES_RECORDED = 200
MAX_FINDINGS_IN_PROMPT = 25
HISTORY_LIMIT = 200


@dataclass
class _Narrative:
    text: str
    source: str
    provider: str | None = None
    warnings: list[str] = field(default_factory=list)


class AnalysisService:
    def __init__(
        self,
        *,
        registry: RepositoryRegistry,
        change_scope: ChangeScopeResolver,
        analyzer: RuleBasedAnalyzer,
        store: AnalysisStore,
        security: SecurityScanService,
        history: WorkspaceAnalysisService,
        bus: EventBus,
        prompts: PromptManager,
        llm: LLMProvider | None = None,
    ) -> None:
        self._registry = registry
        self._change_scope = change_scope
        self._analyzer = analyzer
        self._store = store
        self._security = security
        self._history = history
        self._bus = bus
        self._prompts = prompts
        self._llm = llm

    def run(self, request: ChangeScopeRequest) -> AnalysisReport:
        with get_tracer().start_as_current_span("analysis.run") as span:
            span.set_attribute("analysis.mode", request.analysis_mode.value)
            change_set = self._change_scope.resolve(request)
            record = self._registry.resolve(change_set.repository)
            span.set_attribute("analysis.repository", record.id)
            span.set_attribute("analysis.files", len(change_set.files))

            findings = self._analyzer.analyze(change_set)
            scan = self._security.collect(record.id, record.name)
            findings = _dedupe([*findings, *(_security_finding(item) for item in scan.findings)])

            score = score_findings(findings)
            level = level_for_score(score)
            narrative = self._narrate(change_set, findings, score, level)
            span.set_attribute("analysis.risk_score", score)

            report = AnalysisReport(
                repository=record.id,
                analysis_mode=change_set.analysis_mode,
                commit_id=change_set.target_sha or change_set.base_sha,
                base_sha=change_set.base_sha,
                target_sha=change_set.target_sha,
                changed_files=[change.path for change in change_set.files][:MAX_CHANGED_FILES_RECORDED],
                totals=dict(change_set.totals),
                findings=findings,
                risk_score=score,
                risk_level=level,
                summary=narrative.text,
                summary_source=narrative.source,
                llm_provider=narrative.provider,
                security_sources=list(scan.sources),
                warnings=[*scan.warnings, *narrative.warnings],
            )
            self._store.add(report)
            self._bus.publish(
                ChangeEvent(
                    type=EventType.ANALYSIS_REQUESTED,
                    repository=record.id,
                    payload={
                        "analysis_id": report.analysis_id,
                        "analysis_mode": report.analysis_mode.value,
                        "risk_level": level.value,
                        "risk_score": score,
                    },
                )
            )
            return report

    def criticality(self, repository: str) -> CriticalityReport:
        record = self._registry.resolve(repository)
        history = self._history.history(record.id, "HEAD", HISTORY_LIMIT)
        latest = self._store.latest_for(record.id)
        high_findings = (
            sum(1 for finding in latest.findings if finding.severity in (Severity.HIGH, Severity.CRITICAL))
            if latest
            else 0
        )
        factors = {
            "technology_breadth": min(5 * len(record.technology_tags), 20),
            "contributor_breadth": min(4 * history.author_count, 20),
            "commit_activity": min(history.commit_count // 5, 20),
            "latest_risk": min(latest.risk_score // 2, 30) if latest else 0,
            "high_severity_findings": min(5 * high_findings, 20),
        }
        score = min(100, sum(factors.values()))
        level = level_for_score(score)
        rationale, source = self._criticality_rationale(record.id, score, level, factors, history.commit_count)
        return CriticalityReport(
            repository=record.id,
            score=score,
            level=level,
            factors=factors,
            rationale=rationale,
            rationale_source=source,
        )

    def _narrate(self, change_set: ChangeSet, findings: list[Finding], score: int, level: Severity) -> _Narrative:
        fallback = _rule_summary(change_set, findings, score, level)
        if self._llm is None:
            return _Narrative(text=fallback, source="rule_based")
        try:
            messages = self._prompts.render(
                "analysis_summary",
                {
                    "repository": change_set.repository,
                    "analysis_mode": change_set.analysis_mode.value,
                    "totals": _format_totals(change_set.totals),
                    "risk_level": level.value,
                    "risk_score": score,
                    "findings": _format_findings(findings),
                },
            )
            with get_tracer().start_as_current_span("llm.analysis_summary"):
                response = self._llm.complete(messages, temperature=0.2, max_tokens=300)
            return _Narrative(text=response.content, source="llm", provider=response.provider)
        except (LLMProviderError, PromptError) as exc:
            logger.warning("LLM summary unavailable, using rule-based summary: %s", exc)
            return _Narrative(text=fallback, source="rule_based", warnings=[f"LLM summary unavailable: {exc}"])

    def _criticality_rationale(
        self,
        repository: str,
        score: int,
        level: Severity,
        factors: dict[str, int],
        commit_count: int,
    ) -> tuple[str, str]:
        top = sorted(((value, name) for name, value in factors.items() if value > 0), reverse=True)[:2]
        fallback = (
            f"Criticality {level.value} ({score}/100) across {commit_count} recent commit(s). "
            + (f"Largest contributors: {', '.join(name for _, name in top)}." if top else "No contributing factors.")
        )
        if self._llm is None:
            return fallback, "rule_based"
        try:
            messages = self._prompts.render(
                "criticality_rationale",
                {
                    "repository": repository,
                    "level": level.value,
                    "score": score,
                    "factors": ", ".join(f"{name}={value}" for name, value in factors.items()),
                    "context": f"recent commits={commit_count}",
                },
            )
            response = self._llm.complete(messages, temperature=0.2, max_tokens=200)
            return response.content, "llm"
        except (LLMProviderError, PromptError) as exc:
            logger.warning("LLM rationale unavailable: %s", exc)
            return fallback, "rule_based"


def _security_finding(item) -> Finding:
    location = f"{item.file}:{item.line}" if item.file and item.line else (item.file or "")
    return Finding(
        finding_id=f"security:{item.source}:{item.rule or item.title}:{location}",
        category="security",
        severity=item.severity,
        title=item.title,
        detail=f"Reported by {item.source}",
        file=item.file,
        line=item.line,
        source=item.source,
    )


def _dedupe(findings: list[Finding]) -> list[Finding]:
    unique: dict[str, Finding] = {}
    for finding in findings:
        unique.setdefault(finding.finding_id, finding)
    return list(unique.values())


def _format_totals(totals: dict[str, int]) -> str:
    return ", ".join(f"{key}={value}" for key, value in totals.items())


def _format_findings(findings: list[Finding]) -> str:
    if not findings:
        return "none"
    lines = []
    for finding in findings[:MAX_FINDINGS_IN_PROMPT]:
        location = f" ({finding.file})" if finding.file else ""
        lines.append(f"- [{finding.severity.value}] {finding.category}: {finding.title}{location}")
    return "\n".join(lines)


def _rule_summary(change_set: ChangeSet, findings: list[Finding], score: int, level: Severity) -> str:
    totals = change_set.totals
    base = (
        f"{change_set.repository} ({change_set.analysis_mode.value}): {totals['files_changed']} file(s) changed, "
        f"+{totals['added_lines']}/-{totals['deleted_lines']} lines. Risk {level.value} (score {score})."
    )
    if not findings:
        return f"{base} No rule-based findings."
    top = sorted(findings, key=lambda finding: SEVERITY_WEIGHTS[finding.severity], reverse=True)[:3]
    titles = "; ".join(finding.title for finding in top)
    return f"{base} {len(findings)} finding(s): {titles}."
