import type { RepositoryInfo } from "./types";

export interface GraphNode {
  id: string;
  label: string;
  x: number;
  y: number;
  tags: string[];
}

export interface GraphEdge {
  source: string;
  target: string;
  sharedTags: string[];
}

/**
 * Builds a repository relationship graph. The backend has no dependency-graph API, so two
 * repositories are linked when they share a technology tag. The UI labels the graph accordingly.
 */
export function buildSharedTagGraph(
  repositories: Pick<RepositoryInfo, "id" | "name" | "technology_tags">[],
  radius = 200,
  center = 260,
): { nodes: GraphNode[]; edges: GraphEdge[] } {
  const count = repositories.length;
  const nodes: GraphNode[] = repositories.map((repo, index) => {
    const angle = count === 0 ? 0 : (2 * Math.PI * index) / count - Math.PI / 2;
    return {
      id: repo.id,
      label: repo.name,
      x: center + radius * Math.cos(angle),
      y: center + radius * Math.sin(angle),
      tags: [...repo.technology_tags].sort(),
    };
  });

  const edges: GraphEdge[] = [];
  for (let i = 0; i < nodes.length; i += 1) {
    for (let j = i + 1; j < nodes.length; j += 1) {
      const shared = nodes[i].tags.filter((tag) => nodes[j].tags.includes(tag));
      if (shared.length > 0) {
        edges.push({ source: nodes[i].id, target: nodes[j].id, sharedTags: shared });
      }
    }
  }
  return { nodes, edges };
}

/** Counts how many repositories use each technology tag, sorted by popularity. */
export function tagUsage(repositories: Pick<RepositoryInfo, "technology_tags">[]): { tag: string; count: number }[] {
  const counts = new Map<string, number>();
  for (const repo of repositories) {
    for (const tag of new Set(repo.technology_tags)) {
      counts.set(tag, (counts.get(tag) ?? 0) + 1);
    }
  }
  return [...counts.entries()]
    .map(([tag, count]) => ({ tag, count }))
    .sort((a, b) => b.count - a.count || a.tag.localeCompare(b.tag));
}
