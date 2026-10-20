import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { SEVERITY_COLORS } from "@/components/charts/palette";
import type { Severity } from "@/lib/types";

const ORDER: Severity[] = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];

/** Donut chart of analyses per severity level. */
export function RiskDistributionChart({
  distribution,
  height = 260,
}: {
  distribution: Partial<Record<Severity, number>> | Record<string, number>;
  height?: number;
}) {
  const data = ORDER.map((level) => ({ name: level, value: Number(distribution[level] ?? 0) })).filter(
    (item) => item.value > 0,
  );

  if (data.length === 0) {
    return (
      <div style={{ height }} className="flex items-center justify-center text-sm text-muted-foreground">
        No analyses recorded yet
      </div>
    );
  }

  return (
    <div style={{ width: "100%", height }} role="img" aria-label="Risk distribution by severity">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie data={data} dataKey="value" nameKey="name" innerRadius="55%" outerRadius="85%" paddingAngle={2} isAnimationActive={false}>
            {data.map((entry) => (
              <Cell key={entry.name} fill={SEVERITY_COLORS[entry.name as Severity]} />
            ))}
          </Pie>
          <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 8 }} />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
