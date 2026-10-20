"""Dashboard aggregates computed from the analysis store and the repository registry."""

from datetime import date, datetime, timedelta, timezone
from statistics import mean

from app.domain.analysis import AnalysisReport, DashboardSummary, RepositoryRisk, Severity, TrendPoint
from app.services.analysis_store import AnalysisStore
from app.services.repository_registry import RepositoryRegistry


class DashboardService:
    def __init__(self, *, registry: RepositoryRegistry, store: AnalysisStore) -> None:
        self._registry = registry
        self._store = store

    def summary(self) -> DashboardSummary:
        reports = self._store.snapshot()
        by_mode: dict[str, int] = {}
        risk: dict[str, int] = {level.value: 0 for level in Severity}
        for report in reports:
            by_mode[report.analysis_mode.value] = by_mode.get(report.analysis_mode.value, 0) + 1
            risk[report.risk_level.value] += 1
        return DashboardSummary(
            registered_repositories=len(self._registry.all_records()),
            analyzed_repositories=len({report.repository for report in reports}),
            total_analyses=len(reports),
            analyses_by_mode=by_mode,
            risk_distribution=risk,
            average_risk_score=round(mean(r.risk_score for r in reports), 2) if reports else 0.0,
            last_analysis_at=max((r.generated_at for r in reports), default=None),
        )

    def repository_risk(self) -> list[RepositoryRisk]:
        grouped: dict[str, list[AnalysisReport]] = {}
        for report in self._store.snapshot():
            grouped.setdefault(report.repository, []).append(report)
        rows: list[RepositoryRisk] = []
        for repository, items in sorted(grouped.items()):
            latest = max(items, key=lambda report: report.generated_at)
            rows.append(
                RepositoryRisk(
                    repository=repository,
                    analysis_count=len(items),
                    latest_risk_score=latest.risk_score,
                    latest_risk_level=latest.risk_level,
                    latest_analysis_at=latest.generated_at,
                )
            )
        return rows

    def trends(self, days: int) -> list[TrendPoint]:
        today = datetime.now(timezone.utc).date()
        buckets: dict[date, list[int]] = {
            today - timedelta(days=offset): [] for offset in range(days - 1, -1, -1)
        }
        for report in self._store.snapshot():
            day = report.generated_at.astimezone(timezone.utc).date()
            if day in buckets:
                buckets[day].append(report.risk_score)
        return [
            TrendPoint(
                date=day.isoformat(),
                analyses=len(scores),
                average_risk_score=round(mean(scores), 2) if scores else 0.0,
            )
            for day, scores in buckets.items()
        ]
