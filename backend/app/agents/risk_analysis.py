"""Agents 4-6: security findings, impact tracing across the working tree, and change risk."""

from __future__ import annotations

import os
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from app.agents.ast_parser import ANALYZABLE_SUFFIXES
from app.agents.base import Agent, Draft
from app.agents.code_reader import MAX_FILE_BYTES
from app.agents.context import SharedContext
from app.domain.analysis import SEVERITY_WEIGHTS, Finding, Severity, level_for_score
from app.domain.models import ChangeSet
from app.rag.collections import Collection
from app.services.rule_analyzer import is_test_path, score_findings

MAX_FINDINGS = 200
MAX_FINDINGS_OUT = 100
MAX_TRACED_SYMBOLS = 50
MAX_FILES_SCANNED = 2000
MAX_REFERENCES = 200
MIN_SYMBOL_LENGTH = 4


class SecurityAnalysisAgent(Agent):
    index = 4
    name = "security_analysis"
    description = "Collects SonarQube, Checkmarx, and Sonatype findings for the repository."
    collection = Collection.SECURITY_ANALYSIS

    def run(self, ctx: SharedContext) -> dict[str, Any]:
        record = ctx.require_repository()
        scan = self.deps.security.collect(record.id, record.name)
        findings = [
            {
                "source": item.source,
                "severity": item.severity.value,
                "title": item.title,
                "file": item.file,
                "line": item.line,
                "rule": item.rule,
            }
            for item in scan.findings[:MAX_FINDINGS]
        ]
        return {
            "sources": list(scan.sources),
            "finding_count": len(scan.findings),
            "findings": findings,
            "truncated": len(scan.findings) > MAX_FINDINGS,
            "warnings": list(scan.warnings),
        }


class ImpactAnalysisAgent(Agent):
    """Finds files outside the change set that reference changed declarations.

    Scope: the working tree. For historical POST_COMMIT runs this reflects the current checkout,
    not the historical tree.
    """

    index = 5
    name = "impact_analysis"
    description = "Finds files outside the change set that reference changed declarations."
    collection = Collection.IMPACT_ANALYSIS

    def run(self, ctx: SharedContext) -> dict[str, Any]:
        change_set = ctx.require_change_set()
        root = Path(ctx.require_repository().path)
        names = _traceable_names(ctx.output("ast_analysis").get("symbols", []))
        if not names:
            return {
                "scope": "working_tree",
                "symbols": [],
                "references": [],
                "impacted_files": [],
                "files_scanned": 0,
                "truncated": False,
            }
        pattern = re.compile(r"\b(?:" + "|".join(re.escape(name) for name in names) + r")\b")
        changed = {change.path for change in change_set.files}
        ignored = set(self.deps.settings.ignored_directories)

        references: list[dict[str, Any]] = []
        impacted: set[str] = set()
        scanned = 0
        truncated = False
        for path in _source_files(root, ignored):
            if scanned >= MAX_FILES_SCANNED or len(references) >= MAX_REFERENCES:
                truncated = True
                break
            relative = path.relative_to(root).as_posix()
            if relative in changed:
                continue
            text = _read_small(path)
            if text is None:
                continue
            scanned += 1
            for number, line in enumerate(text.splitlines(), start=1):
                for match in pattern.finditer(line):
                    if len(references) >= MAX_REFERENCES:
                        truncated = True
                        break
                    references.append({"symbol": match.group(0), "file": relative, "line": number})
                    impacted.add(relative)
        return {
            "scope": "working_tree",
            "symbols": names,
            "references": references,
            "impacted_files": sorted(impacted),
            "files_scanned": scanned,
            "truncated": truncated,
        }


class RiskAnalysisAgent(Agent):
    index = 6
    name = "risk_analysis"
    description = "Scores change risk from rule findings and security findings."
    collection = Collection.RISK_ANALYSIS

    def run(self, ctx: SharedContext) -> dict[str, Any]:
        change_set = ctx.require_change_set()
        findings = list(self.deps.analyzer.analyze(change_set))
        findings.extend(_security_findings(ctx.output("security_analysis").get("findings", [])))
        findings = _dedupe(findings)
        score = score_findings(findings)
        level = level_for_score(score)
        ordered = sorted(findings, key=lambda finding: SEVERITY_WEIGHTS[finding.severity], reverse=True)
        categories: dict[str, int] = {}
        for finding in findings:
            categories[finding.category] = categories.get(finding.category, 0) + 1
        high_count = sum(1 for finding in findings if finding.severity in (Severity.HIGH, Severity.CRITICAL))
        history = ctx.output("history_analysis")
        return {
            "risk_score": score,
            "risk_level": level.value,
            "finding_count": len(findings),
            "high_severity_count": high_count,
            "categories": categories,
            "findings": [finding.model_dump(mode="json") for finding in ordered[:MAX_FINDINGS_OUT]],
            "impacted_files": ctx.output("impact_analysis").get("impacted_files", [])[:50],
            "test_files_changed": sum(1 for change in change_set.files if is_test_path(change.path)),
            "similar_changes": history.get("matches", []),
        }

    def documents(self, ctx: SharedContext, output: dict[str, Any]) -> list[Draft]:
        titles = [item["title"] for item in output.get("findings", [])[:10]]
        summary = "; ".join(titles) if titles else "no findings"
        text = (
            f"{ctx.analysis_mode.value} risk on {ctx.require_repository().name}: "
            f"score {output['risk_score']} ({output['risk_level']}). {summary}"
        )
        return [
            Draft(
                collection=Collection.RISK_ANALYSIS,
                text=text,
                metadata={"risk_level": output["risk_level"], "risk_score": output["risk_score"]},
            )
        ]


def _traceable_names(symbols: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for item in symbols:
        name = str(item.get("name", ""))
        if len(name) < MIN_SYMBOL_LENGTH or name.startswith("__") or name in seen:
            continue
        seen.add(name)
        names.append(name)
        if len(names) >= MAX_TRACED_SYMBOLS:
            break
    return names


def _source_files(root: Path, ignored: set[str]) -> Iterator[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in ignored and not name.startswith(".")]
        for filename in filenames:
            path = Path(dirpath) / filename
            if path.suffix.lower() in ANALYZABLE_SUFFIXES:
                yield path


def _read_small(path: Path) -> str | None:
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _security_findings(items: list[dict[str, Any]]) -> list[Finding]:
    return [
        Finding(
            finding_id=f"security-{index}",
            category="security",
            severity=Severity(item["severity"]),
            title=item["title"],
            detail=item.get("rule") or "",
            file=item.get("file"),
            line=item.get("line"),
            source=item.get("source") or "security",
        )
        for index, item in enumerate(items)
    ]


def _dedupe(findings: list[Finding]) -> list[Finding]:
    seen: set[tuple[str, str, str | None, int | None]] = set()
    unique: list[Finding] = []
    for finding in findings:
        key = (finding.category, finding.title, finding.file, finding.line)
        if key in seen:
            continue
        seen.add(key)
        unique.append(finding)
    return unique
