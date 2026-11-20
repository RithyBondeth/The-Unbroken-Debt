import { describe, expect, it } from "vitest";
import { MIST_BOUNDS, MIST_HEIGHT, bakeMistField, mistAt } from "@/episodes/ep1/data/forestMist";
import { PATH, PLAY, ROAD_Z } from "@/episodes/ep1/data/forestBorder";

describe("forest mist map", () => {
  it("keeps the path readable, lays mist on the fields and walls the edge", () => {
    for (const [x, z] of PATH) {
      const m = mistAt(x, z);
      expect(m.density).toBeLessThan(0.3);
      expect(m.height * MIST_HEIGHT).toBeLessThan(1.5);
    }
    // Out over the fields beside the walk: mist on the water, and somewhere a taller bank.
    const fields = [-30, -20, -14, 14, 20, 30].flatMap((x) =>
      [20, 40, 50].map((z) => mistAt(x, z)),
    );
    expect(Math.max(...fields.map((m) => m.density))).toBeGreaterThan(0.45);
    expect(Math.max(...fields.map((m) => m.height * MIST_HEIGHT))).toBeGreaterThan(2.2);
    expect(Math.min(...fields.map((m) => m.height * MIST_HEIGHT))).toBeGreaterThan(0.8);
    // Past the walls: thick and tall, so the forest has no edge to see.
    const edge = mistAt(PLAY.maxX + 10, 20);
    expect(edge.density).toBeGreaterThan(0.6);
    expect(edge.height * MIST_HEIGHT).toBeGreaterThan(4);
  });

  it("lies low over the paddies, a taller bank here and there", () => {
    const heights: number[] = [];
    for (let x = -50; x <= 50; x += 5)
      for (let z = ROAD_Z + 6; z <= ROAD_Z + 20; z += 4) {
        const m = mistAt(x, z);
        expect(m.density).toBeGreaterThan(0.3);
        heights.push(m.height * MIST_HEIGHT);
      }
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
