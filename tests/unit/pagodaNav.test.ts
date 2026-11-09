import { describe, expect, it } from "vitest";
import { PagodaNav } from "@/episodes/ep2/PagodaNav";
import { SHORTCUTS, onGardenSide, visitedZone } from "@/episodes/ep2/data/shortcuts";

const bounds = { minX: -20, maxX: 20, minZ: -20, maxZ: 20 };
// A wall across the middle with one gap at its east end, and a stupa in the open.
const wall = { minX: -20, maxX: 12, minZ: -0.3, maxZ: 0.3 };
const stupa = { minX: -6.7, maxX: -5.3, minZ: 7.3, maxZ: 8.7 };

describe("Episode 2 navigation", () => {
  const nav = new PagodaNav([wall, stupa], bounds);

  it("goes round a wall through its gap, never through it", () => {
    const path = nav.path({ x: -10, z: -8 }, { x: -10, z: 8 });
    expect(path.length).toBeGreaterThan(1);
    let prev = { x: -10, z: -8 };
    for (const p of path) {
      expect(nav.straight(prev, p)).toBe(true);
      prev = p;
    }
    expect(path.some((p) => p.x > 12)).toBe(true);
    expect(path[path.length - 1]).toEqual({ x: -10, z: 8 });
  });

  it("walks straight where the way is open", () => {
    const path = nav.path({ x: 15, z: -10 }, { x: 15, z: 10 });
    expect(path).toEqual([{ x: 15, z: 10 }]);
  });

  it("keeps a corpse's shoulders off a stupa", () => {
    expect(nav.walkable({ x: -6, z: 8 })).toBe(false);
    expect(nav.walkable({ x: -6, z: 9.1 })).toBe(false);
    expect(nav.walkable({ x: -6, z: 9.6 })).toBe(true);
  });

  it("gives up cleanly when there is no way", () => {
    const shut = new PagodaNav([{ minX: -20, maxX: 20, minZ: -0.3, maxZ: 0.3 }], bounds);
    expect(shut.path({ x: 0, z: -5 }, { x: 0, z: 5 })).toEqual([]);
  });
});

describe("Episode 2 shortcuts", () => {
  it("open only from the garden's side, within reach", () => {
    const terrace = SHORTCUTS.find((s) => s.id === "terrace")!;
    expect(onGardenSide(terrace, { x: 30.5, z: 25 })).toBe(true);
    expect(onGardenSide(terrace, { x: 27.8, z: 25 })).toBe(false);
    expect(onGardenSide(terrace, { x: 34, z: 25 })).toBe(false);
    const grove = SHORTCUTS.find((s) => s.id === "grove")!;
    expect(onGardenSide(grove, { x: -23, z: -43 })).toBe(true);
    expect(onGardenSide(grove, { x: -23, z: -40.5 })).toBe(false);
  });
  it("knows which part of the lost garden Sora is in", () => {
    expect(visitedZone({ x: 0, z: 0 })).toBe(null);
    expect(visitedZone({ x: -55, z: 5 })).toBe("court");
    expect(visitedZone({ x: 0, z: -70 })).toBe("grove");
  });
});
