import type { AnalysisReport, ChangeSet, Finding, Severity } from "./types";

// Mirrors REF_PATTERN in backend/app/api/schemas.py.
const REF_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._/@-]*$/;

export function validateRef(label: string, value: string, required: boolean): string | null {
  const trimmed = value.trim();
  if (!trimmed) return required ? `${label} is required` : null;
  if (trimmed.length > 255) return `${label} must be 255 characters or fewer`;
  if (!REF_PATTERN.test(trimmed)) return `${label} may only contain letters, digits, and . _ / @ -`;
  return null;
}

export function validateBranchPair(source: string, target: string): string | null {
  if (source.trim() && source.trim() === target.trim()) {
    return "Source and target branches must differ";
  }
  return null;
}

/** Maps a numeric score to the same severity bands used by the backend. */
export function classifyRiskScore(score: number): Severity {
  if (score >= 80) return "CRITICAL";
  if (score >= 50) return "HIGH";
  if (score >= 20) return "MEDIUM";
  return "LOW";
}

export type PreCommitDecision = "PASS" | "WARN" | "BLOCK";

export interface PreCommitGate {
  decision: PreCommitDecision;
  reasons: string[];
}

/** Pre-commit gate: CRITICAL or HIGH blocks the commit, MEDIUM warns. */
export function evaluatePreCommitGate(report: Pick<AnalysisReport, "findings" | "risk_level">): PreCommitGate {
  const reasons: string[] = [];
  const blocking = report.findings.filter((f) => f.severity === "CRITICAL" || f.severity === "HIGH");
  const warnings = report.findings.filter((f) => f.severity === "MEDIUM");
  if (blocking.length > 0) {
    reasons.push(`${blocking.length} CRITICAL/HIGH finding(s) must be resolved before committing`);
    return { decision: "BLOCK", reasons };
  }
  if (warnings.length > 0 || report.risk_level === "MEDIUM") {
    reasons.push(`${warnings.length} MEDIUM finding(s) should be reviewed`);
    return { decision: "WARN", reasons };
  }
  return { decision: "PASS", reasons: ["No blocking or medium findings"] };
}

export type ReleaseDecision = "GO" | "CONDITIONAL_GO" | "NO_GO";

export interface ReleaseGate {
  decision: ReleaseDecision;
  reasons: string[];
  checklist: { label: string; passed: boolean }[];
}

/**
 * Release readiness (CAB view). NO_GO on any CRITICAL finding or CRITICAL risk level.
 * CONDITIONAL_GO on HIGH risk, HIGH findings, analysis warnings, or a risk score at or above maxScore.
 */
export function evaluateReleaseGate(
  report: Pick<AnalysisReport, "findings" | "risk_level" | "risk_score" | "warnings" | "summary_source">,
  maxScore = 70,
): ReleaseGate {
  const criticalFindings = report.findings.filter((f) => f.severity === "CRITICAL").length;
  const highFindings = report.findings.filter((f) => f.severity === "HIGH").length;
  const reasons: string[] = [];

  let decision: ReleaseDecision = "GO";
  if (criticalFindings > 0 || report.risk_level === "CRITICAL") {
    decision = "NO_GO";
    reasons.push(`${criticalFindings} CRITICAL finding(s) block the release`);
  } else {
    if (highFindings > 0) reasons.push(`${highFindings} HIGH finding(s) need a documented waiver`);
    if (report.risk_level === "HIGH") reasons.push("Overall risk level is HIGH");
    if (report.risk_score >= maxScore) reasons.push(`Risk score ${report.risk_score} is at or above ${maxScore}`);
    if (report.warnings.length > 0) reasons.push(`${report.warnings.length} analysis warning(s) to review`);
    if (reasons.length > 0) decision = "CONDITIONAL_GO";
  }

  if (reasons.length === 0) reasons.push("All release checks passed");

  const checklist = [
    { label: "No CRITICAL findings", passed: criticalFindings === 0 },
    { label: "No HIGH findings", passed: highFindings === 0 },
    { label: `Risk score below ${maxScore}`, passed: report.risk_score < maxScore },
    { label: "No analysis warnings", passed: report.warnings.length === 0 },
    { label: "Summary produced by analysis engine", passed: report.summary_source.length > 0 },
  ];

  return { decision, reasons, checklist };
}

export function groupFindingsByCategory(findings: Finding[]): Record<string, Finding[]> {
  const groups: Record<string, Finding[]> = {};
  for (const finding of findings) {
    (groups[finding.category] ??= []).push(finding);
  }
  return groups;
}

export function countBySeverity(findings: Finding[]): Record<Severity, number> {
  const counts: Record<Severity, number> = { LOW: 0, MEDIUM: 0, HIGH: 0, CRITICAL: 0 };
  for (const finding of findings) counts[finding.severity] += 1;
  return counts;
}

/** File-level breakdown from a change set, sorted by churn (added + deleted + modified lines). */
export function fileChurn(changeSet: Pick<ChangeSet, "files">): { path: string; churn: number; type: string }[] {
  return changeSet.files
    .map((file) => ({
      path: file.path,
      churn: file.added_lines + file.deleted_lines + file.modified_lines,
      type: file.change_type,
    }))
    .sort((a, b) => b.churn - a.churn || a.path.localeCompare(b.path));
}
