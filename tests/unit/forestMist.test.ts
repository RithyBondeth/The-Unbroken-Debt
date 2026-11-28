import { describe, expect, it } from "vitest";
import { MIST_BOUNDS, MIST_HEIGHT, bakeMistField, mistAt } from "@/episodes/ep1/data/forestMist";
import { PATH, PLAY } from "@/episodes/ep1/data/forestBorder";
import { BUILDINGS, FIELDS } from "@/episodes/ep1/data/farmLayout";
import { farmPathDistance, rectDistance } from "@/episodes/ep1/data/farmGround";

describe("forest mist map", () => {
  it("keeps the path readable, lays mist on the fields and walls the edge", () => {
    for (const [x, z] of PATH) {
      const m = mistAt(x, z);
      expect(m.density).toBeLessThan(0.3);
      expect(m.height * MIST_HEIGHT).toBeLessThan(1.5);
    }
    // Out over the farm's dry fields (away from their paths): low mist, and somewhere a
    // taller bank.
    const fields = FIELDS.flatMap((f) =>
      [0.2, 0.5, 0.8].flatMap((u) =>
        [0.2, 0.5, 0.8].map((v) => [
          f.minX + u * (f.maxX - f.minX),
          f.minZ + v * (f.maxZ - f.minZ),
        ]),
      ),
    )
      .filter(([x, z]) => farmPathDistance(x, z) > 3)
      .map(([x, z]) => mistAt(x, z));
    expect(fields.length).toBeGreaterThan(10);
    expect(Math.max(...fields.map((m) => m.density))).toBeGreaterThan(0.45);
    // (The taller banks drift over the whole farm: the next test finds them.)
    expect(Math.max(...fields.map((m) => m.height * MIST_HEIGHT))).toBeGreaterThan(1.2);
    expect(Math.min(...fields.map((m) => m.height * MIST_HEIGHT))).toBeGreaterThan(0.8);
    // Past the walls: thick and tall, so the forest has no edge to see.
    const edge = mistAt(PLAY.maxX + 10, 20);
    expect(edge.density).toBeGreaterThan(0.6);
    expect(edge.height * MIST_HEIGHT).toBeGreaterThan(4);
  });

  it("lies low over the farm's open ground, a taller bank here and there", () => {
    // Away from the paths and the buildings (data/farmLayout.ts), inside the fence.
    const heights: number[] = [];
    for (let x = -40; x <= 40; x += 6)
      for (let z = -54; z <= 36; z += 6) {
        if (farmPathDistance(x, z) < 4 || rectDistance(x, z, BUILDINGS) < 4) continue;
        const m = mistAt(x, z);
        expect(m.density).toBeGreaterThan(0.3);
        heights.push(m.height * MIST_HEIGHT);
      }
    expect(heights.length).toBeGreaterThan(80);
    heights.sort((a, b) => a - b);
    expect(heights[Math.floor(heights.length / 2)]).toBeLessThan(2.2); // most of it waist to chest high
    expect(heights[heights.length - 1]).toBeGreaterThan(heights[0] + 0.8); // not one flat sheet
  });

  it("bakes a map covering the village and the forest round it", () => {
    const { data, width, height } = bakeMistField();
    expect(width).toBe(Math.round(MIST_BOUNDS.width * 0.5));
    expect(height).toBe(Math.round(MIST_BOUNDS.depth * 0.5));
    expect(data.length).toBe(width * height * 4);
    expect(data.some((v, i) => i % 4 === 0 && v > 200)).toBe(true);
  });
});
