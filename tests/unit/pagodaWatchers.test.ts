import { describe, expect, it } from "vitest";
import { CLEARING_X, GODDESS_PATH } from "../../src/episodes/ep2/PagodaWatchers";

const HALL_DOOR = { x: 22, z: 6.6 };
const dist = (a: { x: number; z: number }, b: { x: number; z: number }) =>
  Math.hypot(a.x - b.x, a.z - b.z);

describe("Episode 2 watching images", () => {
  it("brings the goddess from the clearing to the hall steps, nearer every move", () => {
    expect(GODDESS_PATH[0].x).toBeGreaterThan(CLEARING_X);
    expect(GODDESS_PATH.at(-1)!.x).toBeLessThan(CLEARING_X);
    for (let k = 1; k < GODDESS_PATH.length; k++)
      expect(dist(GODDESS_PATH[k], HALL_DOOR)).toBeLessThan(dist(GODDESS_PATH[k - 1], HALL_DOOR));
  });
  it("never stands her in the doorway or on the path into the clearing", () => {
    for (const p of GODDESS_PATH) {
      expect(dist(p, HALL_DOOR)).toBeGreaterThan(2.5);
      // The lane in from the breach runs between Z 6.5 and 10.9.
      if (p.x > CLEARING_X && p.x < 35) expect(p.z < 6 || p.z > 11.4).toBe(true);
    }
  });
});
