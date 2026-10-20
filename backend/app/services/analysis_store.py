"""Bounded in-memory store for analysis reports. Persistence (PostgreSQL) is added in a later part."""

import threading
from collections import deque

from app.domain.analysis import AnalysisReport, SimilarChange
from app.services.similarity import query_coverage, tokenize

MIN_COMMIT_PREFIX = 4


class AnalysisStore:
    def __init__(self, max_entries: int = 1000) -> None:
        self._reports: deque[AnalysisReport] = deque(maxlen=max_entries)
        self._lock = threading.RLock()

    def add(self, report: AnalysisReport) -> None:
        with self._lock:
            self._reports.append(report)

    def snapshot(self) -> list[AnalysisReport]:
        with self._lock:
            return list(self._reports)

    def get(self, analysis_id: str) -> AnalysisReport | None:
        for report in self.snapshot():
            if report.analysis_id == analysis_id:
                return report
        return None

    def find_by_commit(self, commit_prefix: str) -> AnalysisReport | None:
        """Return the most recent report whose target or base SHA starts with the prefix."""
        prefix = commit_prefix.lower()
        if len(prefix) < MIN_COMMIT_PREFIX:
            return None
        for report in reversed(self.snapshot()):
            for sha in (report.target_sha, report.base_sha):
                if sha and sha.lower().startswith(prefix):
                    return report
        return None

    def latest_for(self, repository: str) -> AnalysisReport | None:
        matches = [report for report in self.snapshot() if report.repository == repository]
        return max(matches, key=lambda report: report.generated_at) if matches else None

    def search(self, query: str, *, repository: str | None = None, top_k: int = 5) -> list[SimilarChange]:
        query_terms = tokenize(query)
        scored: list[tuple[float, AnalysisReport, list[str]]] = []
        for report in self.snapshot():
            if repository is not None and report.repository != repository:
                continue
            document = tokenize(
                " ".join(
                    [
                        report.repository,
                        report.analysis_mode.value,
                        report.summary,
                        *report.changed_files,
                        *(finding.title for finding in report.findings),
                    ]
                )
            )
            shared = sorted(query_terms & document)
            if not shared:
                continue
            scored.append((query_coverage(query_terms, document), report, shared))

        scored.sort(key=lambda item: (item[0], item[1].generated_at), reverse=True)
        return [
            SimilarChange(
                analysis_id=report.analysis_id,
                repository=report.repository,
                analysis_mode=report.analysis_mode,
                commit_id=report.commit_id,
                risk_level=report.risk_level,
                similarity=round(score, 3),
                matched_terms=terms[:20],
                summary=report.summary,
            )
            for score, report, terms in scored[:top_k]
        ]
