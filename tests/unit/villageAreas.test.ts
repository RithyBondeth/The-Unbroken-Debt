import { describe, expect, it } from "vitest";
import { LANES, laneCurve, laneDistance } from "@/episodes/ep1/data/villageAreas";

describe("village expansion lanes", () => {
  it("draws the same wandering curve as the Blender plan (village_layout.lane_curve)", () => {
    const curve = laneCurve(LANES[0]);
    expect(curve.length).toBe(25);
    expect(curve[0][0]).toBeCloseTo(13, 6);
    expect(curve[24][1]).toBeCloseTo(-14, 6);
    // Values printed by tools/areas/village_layout.py, mirrored to Babylon space.
    expect(curve[12][0]).toBeCloseTo(20.512364963192546, 6);
    expect(curve[12][1]).toBeCloseTo(-11.587725142011452, 6);
  });

  it("wanders off the straight line between its control points", () => {
    const curve = laneCurve(LANES[0]);
    const off = Math.max(...curve.map(([x, z]) => Math.abs(z - (-11 + ((x - 13) / 16) * -3))));
    expect(off).toBeGreaterThan(0.3);
    expect(laneDistance(...curve[8])).toBeLessThan(1e-6);
  });
});
