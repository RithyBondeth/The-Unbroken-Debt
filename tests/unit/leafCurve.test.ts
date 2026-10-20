import { describe, expect, it } from "vitest";
import { leafProfile } from "../../src/ui/diegetic/leafCurve";

describe("leafProfile", () => {
  const width = 0.148;
  const last = (t: number) => leafProfile(t, width, 24).at(-1) as [number, number];

  it("lies flat on the right at the start and on the left at the end", () => {
    const [x0, y0] = last(0);
    expect(x0).toBeCloseTo(width, 6);
    expect(y0).toBeCloseTo(0, 6);
    const [x1, y1] = last(1);
    expect(x1).toBeCloseTo(-width, 6);
    expect(y1).toBeCloseTo(0, 6);
  });

  it("keeps the page's length while it curls", () => {
    for (const t of [0.25, 0.5, 0.75]) {
      const points = leafProfile(t, width, 24);
      let length = 0;
      for (let i = 1; i < points.length; i++) {
        length += Math.hypot(points[i][0] - points[i - 1][0], points[i][1] - points[i - 1][1]);
      }
      expect(length).toBeCloseTo(width, 6);
    }
  });

  it("lifts the page off the paper mid-turn, with the outer edge lagging", () => {
    const points = leafProfile(0.5, width, 24);
    const middle = points[12];
    expect(middle[1]).toBeGreaterThan(0.05);
    // The edge has not yet passed the spine as far as a rigid page would.
    expect(points.at(-1)?.[0]).toBeGreaterThan(-width * 0.2);
    for (const [, y] of points) expect(y).toBeGreaterThanOrEqual(-1e-9);
  });
});
