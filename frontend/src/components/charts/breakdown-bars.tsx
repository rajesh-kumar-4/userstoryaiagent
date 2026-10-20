import { scoreColor } from "@/components/charts/palette";

/** Horizontal bars for a label-to-value map. Pure CSS, so it needs no chart library. */
export function BreakdownBars({
  data,
  max,
  emptyMessage = "No data",
  format = (value: number) => String(value),
}: {
  data: Record<string, number>;
  max?: number;
  emptyMessage?: string;
  format?: (value: number) => string;
}) {
  const entries = Object.entries(data).sort((a, b) => b[1] - a[1]);
  if (entries.length === 0) return <p className="text-sm text-muted-foreground">{emptyMessage}</p>;
  const ceiling = max ?? Math.max(...entries.map(([, value]) => value), 1);

  return (
    <ul className="space-y-2.5">
      {entries.map(([label, value]) => {
        const pct = Math.max(2, Math.min(100, (value / ceiling) * 100));
        return (
          <li key={label}>
            <div className="mb-1 flex justify-between gap-3 text-xs">
              <span className="truncate text-muted-foreground">{label}</span>
              <span className="font-semibold tabular-nums">{format(value)}</span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-muted" role="presentation">
              <div className="h-full rounded-full bg-primary" style={{ width: `${pct}%` }} />
            </div>
          </li>
        );
      })}
    </ul>
  );
}

/** Same as BreakdownBars but colored by a 0-100 risk score scale. */
export function ScoreBars({ data, emptyMessage }: { data: Record<string, number>; emptyMessage?: string }) {
  const entries = Object.entries(data).sort((a, b) => b[1] - a[1]);
  if (entries.length === 0) return <p className="text-sm text-muted-foreground">{emptyMessage ?? "No data"}</p>;
  return (
    <ul className="space-y-2.5">
      {entries.map(([label, score]) => (
        <li key={label}>
          <div className="mb-1 flex justify-between text-xs">
            <span className="truncate text-muted-foreground">{label}</span>
            <span className="font-semibold tabular-nums">{score}</span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
            <div className="h-full rounded-full" style={{ width: `${Math.max(2, Math.min(100, score))}%`, backgroundColor: scoreColor(score) }} />
          </div>
        </li>
      ))}
    </ul>
  );
}
