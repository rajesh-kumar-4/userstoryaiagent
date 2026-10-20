import { describe, expect, it } from "vitest";
import { buildSharedTagGraph, tagUsage } from "./graph";

const repos = [
  { id: "a", name: "alpha", technology_tags: ["python", "fastapi"] },
  { id: "b", name: "beta", technology_tags: ["fastapi", "react"] },
  { id: "c", name: "gamma", technology_tags: ["go"] },
];

describe("buildSharedTagGraph", () => {
  it("places one node per repository on the circle", () => {
    const { nodes } = buildSharedTagGraph(repos, 200, 260);
    expect(nodes).toHaveLength(3);
    // The first node starts at the top of the circle.
    expect(nodes[0].x).toBeCloseTo(260, 6);
    expect(nodes[0].y).toBeCloseTo(60, 6);
    for (const node of nodes) {
      expect(Math.hypot(node.x - 260, node.y - 260)).toBeCloseTo(200, 6);
    }
  });

  it("links repositories that share a technology tag", () => {
    const { edges } = buildSharedTagGraph(repos);
    expect(edges).toEqual([{ source: "a", target: "b", sharedTags: ["fastapi"] }]);
  });

  it("returns an empty graph for no repositories", () => {
    expect(buildSharedTagGraph([])).toEqual({ nodes: [], edges: [] });
  });

  it("sorts node tags without mutating the input", () => {
    const input = [{ id: "x", name: "x", technology_tags: ["zeta", "alpha"] }];
    const { nodes } = buildSharedTagGraph(input);
    expect(nodes[0].tags).toEqual(["alpha", "zeta"]);
    expect(input[0].technology_tags).toEqual(["zeta", "alpha"]);
  });
});

describe("tagUsage", () => {
  it("counts each tag once per repository, most used first", () => {
    const usage = tagUsage([
      { technology_tags: ["fastapi", "fastapi", "python"] },
      { technology_tags: ["fastapi"] },
      { technology_tags: ["go", "python"] },
    ]);
    expect(usage).toEqual([
      { tag: "fastapi", count: 2 },
      { tag: "python", count: 2 },
      { tag: "go", count: 1 },
    ]);
  });
});
