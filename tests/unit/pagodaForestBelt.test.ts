import { describe, expect, it } from "vitest";
import { BELT, WALKABLE, layoutBelt, toWalkable } from "@/episodes/ep2/pagodaForestBelt";

describe("Episode 2 forest belt", () => {
  const trees = layoutBelt(9);

  it("plants a full belt round the whole map", () => {
    expect(trees.length).toBeGreaterThan(150);
    expect(trees.length).toBeLessThan(420);
    // Every side of the map has trees: west, east, north and south of the walkable ground.
    const minX = Math.min(...WALKABLE.map((r) => r.minX)),
      maxX = Math.max(...WALKABLE.map((r) => r.maxX)),
      minZ = Math.min(...WALKABLE.map((r) => r.minZ)),
      maxZ = Math.max(...WALKABLE.map((r) => r.maxZ));
    expect(trees.some((t) => t.x < minX)).toBe(true);
    expect(trees.some((t) => t.x > maxX)).toBe(true);
    expect(trees.some((t) => t.z < minZ)).toBe(true);
    expect(trees.some((t) => t.z > maxZ)).toBe(true);
  });

  it("never stands on ground Sora can walk", () => {
    for (const t of trees)
      expect(toWalkable(t.x, t.z), `${t.x},${t.z}`).toBeGreaterThanOrEqual(BELT.near);
  });

  it("uses every template and is the same every load", () => {
    expect(new Set(trees.map((t) => t.template)).size).toBe(9);
    expect(layoutBelt(9)).toEqual(trees);
  });
});
