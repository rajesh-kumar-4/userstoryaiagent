import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { CHART_GRID_DARK, CHART_PRIMARY, CHART_TEXT_DARK } from "@/components/charts/palette";
import type { TrendPoint } from "@/lib/types";

/** Average risk score per day. The area's height is the score (0-100). */
export function RiskTrendChart({ data, height = 260 }: { data: TrendPoint[]; height?: number }) {
  return (
    <div style={{ width: "100%", height }} role="img" aria-label="Average risk score trend">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -12 }}>
          <defs>
            <linearGradient id="riskTrendFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={CHART_PRIMARY} stopOpacity={0.45} />
              <stop offset="100%" stopColor={CHART_PRIMARY} stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke={CHART_GRID_DARK} strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="date" tick={{ fill: CHART_TEXT_DARK, fontSize: 11 }} tickLine={false} />
          <YAxis domain={[0, 100]} tick={{ fill: CHART_TEXT_DARK, fontSize: 11 }} tickLine={false} />
          <Tooltip contentStyle={{ background: "#0f172a", border: `1px solid ${CHART_GRID_DARK}`, borderRadius: 8 }} />
          <Area
            type="monotone"
            dataKey="average_risk_score"
            name="Avg risk"
            stroke={CHART_PRIMARY}
            fill="url(#riskTrendFill)"
            strokeWidth={2}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
