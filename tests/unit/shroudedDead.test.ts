import { describe, expect, it } from "vitest";
import { LANDING, hopPose } from "../../src/episodes/ep2/ShroudedDead";

describe("the shrouded dead's hop", () => {
  it("crouches, leaves the ground stretched, and lands squashed", () => {
    expect(hopPose(0.1).lift).toBe(0);
    expect(hopPose(0.1).squash).toBeGreaterThan(0.3);
    const apex = hopPose((0.15 + LANDING) / 2);
    expect(apex.lift).toBeGreaterThan(0.2);
    expect(hopPose(0.2).stretch).toBeGreaterThan(0.6);
    expect(hopPose(LANDING).lift).toBe(0);
    expect(hopPose(LANDING).squash).toBe(1);
  });
  it("is back to rest by the end of each hop, so hops chain smoothly", () => {
    const end = hopPose(0.999);
    expect(end.lift).toBe(0);
    expect(end.squash).toBeLessThan(0.01);
    expect(hopPose(0).squash).toBe(0);
  });
});
