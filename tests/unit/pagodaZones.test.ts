import { describe, expect, it } from "vitest";
import { layoutFarForest, floorPieces } from "../../src/episodes/ep2/PagodaFarForest";
import { ZONE_REACH, zoneDistance } from "../../src/episodes/ep2/PagodaZones";
import {
  BOUNDS,
  ENTRY,
  KUTI,
  LIBRARY,
  LOST_GARDEN,
  MEMORY,
  TANK_BASIN,
} from "../../src/episodes/ep2/data/pagoda";

const inside = (x: number, z: number) =>
  LOST_GARDEN.some((g) => x > g.minX && x < g.maxX && z > g.minZ && z < g.maxZ);

describe("the lost garden", () => {
  it("adds its five zones without overlapping each other", () => {
    expect(LOST_GARDEN.map((g) => g.id)).toEqual(["court", "tank", "grove", "gallery", "terrace"]);
    for (const a of LOST_GARDEN)
      for (const b of LOST_GARDEN) {
        if (a === b) continue;
        const overlap = a.minX < b.maxX && b.minX < a.maxX && a.minZ < b.maxZ && b.minZ < a.maxZ;
        expect(overlap, `${a.id} and ${b.id}`).toBe(false);
      }
  });

  it("leaves the story points where they were and the memory space out of reach", () => {
    for (const p of [ENTRY, KUTI, LIBRARY, MEMORY]) expect(inside(p.x, p.z)).toBe(false);
    expect(Math.max(...LOST_GARDEN.map((g) => g.maxX))).toBeLessThan(69);
    expect(BOUNDS.maxX).toBeLessThan(69);
  });

  it("keeps every zone inside the fall guard's bounds", () => {
    for (const g of LOST_GARDEN) {
      expect(g.minX).toBeGreaterThan(BOUNDS.minX);
      expect(g.maxX).toBeLessThan(BOUNDS.maxX);
      expect(g.minZ).toBeGreaterThan(BOUNDS.minZ);
      expect(g.maxZ).toBeLessThan(BOUNDS.maxZ);
    }
  });

  it("measures distance to a zone, 0 inside it", () => {
    const court = LOST_GARDEN[0];
    expect(zoneDistance(court, (court.minX + court.maxX) / 2, (court.minZ + court.maxZ) / 2)).toBe(
      0,
    );
    expect(zoneDistance(court, court.maxX + 3, court.minZ - 4)).toBeCloseTo(5);
  });

  it("draws the zones next to the compound's spawn but not the far side of the map", () => {
    const court = LOST_GARDEN[0];
    expect(zoneDistance(court, -28, 22)).toBeLessThan(ZONE_REACH);
    const terrace = LOST_GARDEN[4];
    expect(zoneDistance(terrace, 0, 5)).toBeGreaterThan(ZONE_REACH);
  });

  it("keeps the far forest's cards out of the zones", () => {
    const trees = layoutFarForest();
    expect(trees.length).toBe(760);
    for (const t of trees) expect(inside(t.x, t.z), `${t.x},${t.z}`).toBe(false);
  });

  it("cuts the forest floor around a sunken basin and nowhere else", () => {
    const pieces = floorPieces(130, [TANK_BASIN]);
    const area = pieces.reduce((sum, [x0, x1, z0, z1]) => sum + (x1 - x0) * (z1 - z0), 0);
    const hole = (TANK_BASIN.maxX - TANK_BASIN.minX) * (TANK_BASIN.maxZ - TANK_BASIN.minZ);
    expect(area).toBeCloseTo(260 * 260 - hole);
    const midX = (TANK_BASIN.minX + TANK_BASIN.maxX) / 2,
      midZ = (TANK_BASIN.minZ + TANK_BASIN.maxZ) / 2;
    expect(pieces.some(([a, b, c, d]) => midX > a && midX < b && midZ > c && midZ < d)).toBe(false);
  });
});
