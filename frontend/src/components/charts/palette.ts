import type { Severity } from "@/lib/types";

// Hex values are used because Recharts needs concrete colors rather than CSS variables.
export const SEVERITY_COLORS: Record<Severity, string> = {
  LOW: "#22c55e",
  MEDIUM: "#eab308",
  HIGH: "#f97316",
  CRITICAL: "#ef4444",
};

export const CHART_PRIMARY = "#38bdf8";
export const CHART_GRID_DARK = "#334155";
export const CHART_GRID_LIGHT = "#e2e8f0";
export const CHART_TEXT_DARK = "#94a3b8";
export const CHART_TEXT_LIGHT = "#475569";

/** Heatmap tile background for a 0-100 score. */
export function scoreColor(score: number): string {
  if (score >= 80) return SEVERITY_COLORS.CRITICAL;
  if (score >= 50) return SEVERITY_COLORS.HIGH;
  if (score >= 20) return SEVERITY_COLORS.MEDIUM;
  return SEVERITY_COLORS.LOW;
}
