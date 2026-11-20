import { describe, expect, it } from "vitest";
import {
  PLAY,
  ROAD_Z,
  TERRAIN,
  YARD,
  borderHeight,
  inside,
  layoutBorder,
  outside,
  pathDistance,
  roadBank,
} from "@/episodes/ep1/data/forestBorder";
import { WEST_YARD, inClearing, laneDistance } from "@/episodes/ep1/data/villageAreas";

const flat = () => 0;
const options = { nearDepth: 14, farDepth: 44, density: 0.85, clear: () => true };

describe("forest border ground", () => {
  it("measures signed distance from a rectangle", () => {
    expect(outside(TERRAIN, 0, 0)).toBeLessThan(0);
    expect(outside(TERRAIN, TERRAIN.maxX + 5, 0)).toBeCloseTo(5);
    expect(outside(TERRAIN, TERRAIN.maxX + 3, TERRAIN.maxZ + 4)).toBeCloseTo(5);
  });

  it("meets the authored terrain exactly at its edge", () => {
    const terrain = (x: number, z: number) => 0.1 * Math.sin(x) + 0.05 * Math.cos(z);
    for (const [x, z] of [
      [TERRAIN.maxX, 10],
      [TERRAIN.minX, -12],
      [5, TERRAIN.minZ],
      [-7, TERRAIN.maxZ],
      [TERRAIN.maxX, ROAD_Z + 0.4],
    ])
      expect(borderHeight(x, z, terrain)).toBeCloseTo(terrain(x, z), 6);
  });

  it("tucks under the terrain inside it, except on the raised bunds", () => {
    expect(borderHeight(0, 0, flat)).toBeLessThan(0);
    expect(borderHeight(57, 75, () => -0.32)).toBeGreaterThan(0);
  });

  it("carries the road bank on past the terrain", () => {
    expect(borderHeight(TERRAIN.maxX + 20, ROAD_Z, flat)).toBeCloseTo(roadBank(0));
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

  it("closes the walls with a tree line and stands palms in the fields past it", () => {
    const line = layout.plants.filter((p) => outside(PLAY, p.x, p.z) < 10);
    expect(line.length).toBeGreaterThan(150);
    const species = new Set(line.map((p) => p.species));
    expect(species.has("banana")).toBe(true);
    expect(species.has("sugarPalm")).toBe(true);
    // No bamboo anywhere: bananas and palms in its place (the user, Nov 19).
    expect(layout.plants.some((p) => p.species === "bamboo")).toBe(false);
    const fields = layout.plants.filter((p) => outside(PLAY, p.x, p.z) >= 10);
    expect(fields.filter((p) => p.species === "sugarPalm").length).toBeGreaterThan(14);
    // No leafless trees anywhere (the user, Nov 19).
    expect(layout.plants.some((p) => p.species === "dead")).toBe(false);
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

  it("grows nothing inside the walls: the village file carries the countryside there", () => {
    for (const p of layout.plants) expect(outside(TERRAIN, p.x, p.z)).toBeGreaterThan(0);
  });

  it("keeps the expansion's clearings and lanes open", () => {
    for (const p of layout.plants) {
      expect(inClearing(p.x, p.z)).toBe(false);
      expect(laneDistance(p.x, p.z)).toBeGreaterThan(1);
    }
    // The old family yard is inside the walls.
    expect(inside(PLAY, WEST_YARD.x - WEST_YARD.rx, WEST_YARD.z, 2)).toBe(true);
  });

  it("respects the area's own obstacles inside the terrain", () => {
    const blocked = layoutBorder({ ...options, clear: () => false });
    for (const p of blocked.plants) expect(outside(TERRAIN, p.x, p.z)).toBeGreaterThanOrEqual(0);
  });
});
