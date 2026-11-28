import { describe, expect, it } from "vitest";
import { DRAUGHT_RANGE, Draught, draughtAt, draughtPush } from "@/episodes/ep1/data/draught";

const still = { x: 0, y: 0, z: 0, vx: 0, vz: 0 };
const walking = { x: 0, y: 0, z: 0, vx: 2.2, vz: 0 };

describe("Sora's draught on candles and incense", () => {
  it("is strongest brushing past at a walk and fades with distance", () => {
    const near = draughtAt(walking, 0.3, 1.0, 0);
    const far = draughtAt(walking, 1.2, 1.0, 0);
    expect(near).toBeGreaterThan(0.6);
    expect(far).toBeLessThan(near);
    expect(draughtAt(walking, DRAUGHT_RANGE + 0.1, 1.0, 0)).toBe(0);
  });

  it("barely stirs them when she stands still", () => {
    expect(draughtAt(still, 0.3, 1.0, 0)).toBeLessThan(0.15);
  });

  it("does not reach a flame on another floor", () => {
    expect(draughtAt(walking, 0.3, 3.0, 0)).toBe(0);
  });

  it("pushes the air away from her and along her way", () => {
    const p = draughtPush(walking, 0, 1);
    expect(p.x).toBeGreaterThan(0.4);
    expect(p.z).toBeGreaterThan(0);
    expect(Math.hypot(p.x, p.z)).toBeCloseTo(1, 5);
  });

  it("follows her feet and ignores teleports", () => {
    const d = new Draught();
    d.update(1 / 60, { x: 0, y: 0, z: 0 });
    for (let k = 1; k <= 60; k++) d.update(1 / 60, { x: k * 0.03, y: 0, z: 0 });
    expect(d.vx).toBeGreaterThan(1.5);
    d.update(1 / 60, { x: 40, y: 0, z: 0 });
    expect(Math.hypot(d.vx, d.vz)).toBeLessThan(12);
  });
});
