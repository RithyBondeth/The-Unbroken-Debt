import { describe, expect, it } from "vitest";
import {
  PLAY,
  ROAD_Z,
  TERRAIN,
  YARD,
  borderHeight,
  inBelt,
  inside,
  layoutBorder,
  outside,
  pathDistance,
  roadBank,
} from "../../src/episodes/ep1/data/forestBorder";

const flat = () => 0;
const options = { nearDepth: 14, farDepth: 44, density: 0.85, clear: () => true };

describe("forest border ground", () => {
  it("measures signed distance from a rectangle", () => {
    expect(outside(TERRAIN, 0, 0)).toBeLessThan(0);
    expect(outside(TERRAIN, 45, 0)).toBeCloseTo(5);
    expect(outside(TERRAIN, 43, 96)).toBeCloseTo(5);
  });

  it("meets the authored terrain exactly at its edge", () => {
    const terrain = (x: number, z: number) => 0.1 * Math.sin(x) + 0.05 * Math.cos(z);
    for (const [x, z] of [
      [40, 10],
      [-40, -12],
      [5, -40],
      [-7, 92],
      [40, ROAD_Z + 0.4],
    ])
      expect(borderHeight(x, z, terrain)).toBeCloseTo(terrain(x, z), 6);
  });

  it("tucks under the terrain inside it, except on the raised bunds", () => {
    expect(borderHeight(0, 0, flat)).toBeLessThan(0);
    expect(borderHeight(37, 75, () => -0.32)).toBeGreaterThan(0);
  });

  it("carries the road bank on past the terrain", () => {
    expect(borderHeight(60, ROAD_Z, flat)).toBeCloseTo(roadBank(0));
  });
});

describe("forest border layout", () => {
  const layout = layoutBorder(options);

  it("is deterministic", () => {
    expect(layoutBorder(options).plants).toEqual(layout.plants);
  });

  it("keeps the yard, path and road clear", () => {
    for (const p of layout.plants) {
      expect(inside(YARD, p.x, p.z, -1.2)).toBe(false);
      expect(pathDistance(p.x, p.z)).toBeGreaterThan(2);
      if (Math.abs(p.x) > TERRAIN.maxX) expect(Math.abs(p.z - ROAD_Z)).toBeGreaterThan(2.5);
    }
  });

  it("fills the thicket at the walls and the belt round the compound", () => {
    const thicket = layout.plants.filter((p) => Math.abs(outside(PLAY, p.x, p.z)) < 3);
    const belt = layout.plants.filter((p) => inBelt(p.x, p.z));
    expect(thicket.length).toBeGreaterThan(150);
    expect(belt.length).toBeGreaterThan(100);
    expect(new Set(layout.plants.map((p) => p.species)).size).toBeGreaterThanOrEqual(8);
  });

  it("puts painted far trees only beyond the modelled ring", () => {
    expect(layout.cards.length).toBeGreaterThan(800);
    for (const c of layout.cards)
      expect(outside(TERRAIN, c.x, c.z)).toBeGreaterThan(options.nearDepth - 6);
  });

  it("thins out on the low preset", () => {
    const low = layoutBorder({ ...options, nearDepth: 8, farDepth: 24, density: 0.55 });
    expect(low.plants.length).toBeLessThan(layout.plants.length * 0.75);
    expect(low.cards.length).toBeLessThan(layout.cards.length * 0.6);
  });

  it("respects the area's own obstacles inside the terrain", () => {
    const blocked = layoutBorder({ ...options, clear: () => false });
    for (const p of blocked.plants) expect(outside(TERRAIN, p.x, p.z)).toBeGreaterThanOrEqual(0);
  });
});
