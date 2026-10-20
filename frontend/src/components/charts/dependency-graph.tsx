import { useMemo } from "react";
import { buildSharedTagGraph } from "@/lib/graph";
import type { RepositoryInfo } from "@/lib/types";

/**
 * SVG relationship graph. Repositories are linked when they share a technology tag.
 * This is not a true code dependency graph; the backend does not expose one.
 */
export function DependencyGraph({
  repositories,
  selectedId,
  onSelect,
  size = 520,
}: {
  repositories: Pick<RepositoryInfo, "id" | "name" | "technology_tags">[];
  selectedId?: string | null;
  onSelect?: (id: string) => void;
  size?: number;
}) {
  const center = size / 2;
  const radius = size / 2 - 90;
  const graph = useMemo(() => buildSharedTagGraph(repositories, radius, center), [repositories, radius, center]);
  const byId = new Map(graph.nodes.map((node) => [node.id, node]));

  if (repositories.length === 0) {
    return <p className="text-sm text-muted-foreground">No repositories registered.</p>;
  }

  return (
    <svg viewBox={`0 0 ${size} ${size}`} className="h-auto w-full max-w-2xl" role="img" aria-label="Repository relationship graph">
      <g>
        {graph.edges.map((edge) => {
          const from = byId.get(edge.source);
          const to = byId.get(edge.target);
          if (!from || !to) return null;
          const active = selectedId === edge.source || selectedId === edge.target;
          return (
            <line
              key={`${edge.source}-${edge.target}`}
              x1={from.x}
              y1={from.y}
              x2={to.x}
              y2={to.y}
              stroke={active ? "#38bdf8" : "#64748b"}
              strokeOpacity={active ? 0.9 : 0.4}
              strokeWidth={Math.min(1 + edge.sharedTags.length, 4)}
            >
              <title>Shared tags: {edge.sharedTags.join(", ")}</title>
            </line>
          );
        })}
      </g>
      <g>
        {graph.nodes.map((node) => {
          const selected = node.id === selectedId;
          return (
            <g
              key={node.id}
              transform={`translate(${node.x}, ${node.y})`}
              onClick={onSelect ? () => onSelect(node.id) : undefined}
              style={{ cursor: onSelect ? "pointer" : "default" }}
              role={onSelect ? "button" : undefined}
              tabIndex={onSelect ? 0 : undefined}
              onKeyDown={
                onSelect
                  ? (event) => {
                      if (event.key === "Enter" || event.key === " ") onSelect(node.id);
                    }
                  : undefined
              }
            >
              <circle r={selected ? 15 : 11} fill={selected ? "#38bdf8" : "#1e293b"} stroke="#38bdf8" strokeWidth={2} />
              <text y={28} textAnchor="middle" fontSize={12} fill="currentColor">
                {node.label.length > 18 ? `${node.label.slice(0, 17)}...` : node.label}
              </text>
              <title>{node.tags.length ? `Tags: ${node.tags.join(", ")}` : "No technology tags"}</title>
            </g>
          );
        })}
      </g>
    </svg>
  );
}
