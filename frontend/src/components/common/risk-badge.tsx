import { Badge } from "@/components/ui/badge";
import type { Severity } from "@/lib/types";

export function RiskBadge({ level }: { level: Severity | string | undefined | null }) {
  if (!level) return <Badge variant="muted">Unknown</Badge>;
  const known = level === "LOW" || level === "MEDIUM" || level === "HIGH" || level === "CRITICAL";
  return <Badge variant={known ? level : "muted"}>{level}</Badge>;
}

export function ScoreBadge({ score }: { score: number }) {
  const level: Severity = score >= 80 ? "CRITICAL" : score >= 50 ? "HIGH" : score >= 20 ? "MEDIUM" : "LOW";
  return (
    <span className="inline-flex items-center gap-2">
      <span className="font-semibold tabular-nums">{score}</span>
      <RiskBadge level={level} />
    </span>
  );
}
