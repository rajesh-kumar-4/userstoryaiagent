import { scoreColor } from "@/components/charts/palette";
import { RiskBadge } from "@/components/common/risk-badge";
import type { Severity } from "@/lib/types";

/** Semicircle gauge for a 0-100 risk score. */
export function ScoreGauge({ score, level, label = "Risk score" }: { score: number; level?: Severity; label?: string }) {
  const clamped = Math.max(0, Math.min(100, score));
  const radius = 70;
  const circumference = Math.PI * radius;
  const offset = circumference * (1 - clamped / 100);
  const color = scoreColor(clamped);

  return (
    <div className="flex flex-col items-center gap-2" role="img" aria-label={`${label} ${clamped} of 100`}>
      <svg viewBox="0 0 180 104" className="w-48">
        <path d="M 20 90 A 70 70 0 0 1 160 90" fill="none" stroke="#334155" strokeWidth={14} strokeLinecap="round" />
        <path
          d="M 20 90 A 70 70 0 0 1 160 90"
          fill="none"
          stroke={color}
          strokeWidth={14}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />
        <text x="90" y="82" textAnchor="middle" fontSize="28" fontWeight="700" fill="currentColor">
          {clamped}
        </text>
      </svg>
      <p className="text-xs text-muted-foreground">{label}</p>
      {level && <RiskBadge level={level} />}
    </div>
  );
}
