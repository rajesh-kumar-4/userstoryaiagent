import { scoreColor } from "@/components/charts/palette";
import { cn } from "@/lib/utils";

export interface HeatmapItem {
  id: string;
  label: string;
  score: number;
  detail?: string;
}

/** Grid of tiles colored by risk score. Tiles are real buttons when `onSelect` is set, for keyboard use. */
export function RiskHeatmap({
  items,
  onSelect,
  emptyMessage = "No scored items",
}: {
  items: HeatmapItem[];
  onSelect?: (item: HeatmapItem) => void;
  emptyMessage?: string;
}) {
  if (items.length === 0) {
    return <p className="text-sm text-muted-foreground">{emptyMessage}</p>;
  }

  return (
    <ul className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4" aria-label="Risk heatmap">
      {items.map((item) => {
        const tile = (
          <div className="flex h-full flex-col justify-between gap-2 p-3 text-left">
            <span className="truncate text-sm font-semibold text-white drop-shadow">{item.label}</span>
            <span className="flex items-baseline justify-between text-white">
              <span className="text-xl font-bold tabular-nums">{item.score}</span>
              {item.detail && <span className="text-[11px] opacity-90">{item.detail}</span>}
            </span>
          </div>
        );
        return (
          <li key={item.id}>
            {onSelect ? (
              <button
                type="button"
                onClick={() => onSelect(item)}
                className={cn("block h-full w-full rounded-lg transition hover:brightness-110 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring")}
                style={{ backgroundColor: scoreColor(item.score), minHeight: 88 }}
                aria-label={`${item.label}, risk score ${item.score}`}
              >
                {tile}
              </button>
            ) : (
              <div className="h-full rounded-lg" style={{ backgroundColor: scoreColor(item.score), minHeight: 88 }}>
                {tile}
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}
