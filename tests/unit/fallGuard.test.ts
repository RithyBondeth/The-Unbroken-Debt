import { describe, expect, it } from "vitest";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { FallGuard } from "../../src/player/FallGuard";

describe("FallGuard", () => {
  it("returns to the spawn if she falls before standing anywhere else", () => {
    const guard = new FallGuard();
    guard.reset(new Vector3(1, 0, 2));
    expect(guard.update(0.016, new Vector3(1, -7, 2), false)).toEqual(new Vector3(1, 0, 2));
  });

  it("remembers footing that held for half a second", () => {
    const guard = new FallGuard();
    guard.reset(new Vector3(0, 0, 0));
    for (let i = 0; i < 40; i++) guard.update(0.016, new Vector3(5, 0.1, 5), true);
    const back = guard.update(0.016, new Vector3(5, -20, 5), false)!;
    expect(back.x).toBe(5);
    expect(back.y).toBeCloseTo(0.15);
  });

  it("ignores airborne positions and respawns outside the walls", () => {
    const guard = new FallGuard();
    guard.bounds = { minX: -10, maxX: 10, minZ: -10, maxZ: 10 };
    guard.reset(new Vector3(0, 0, 0));
    for (let i = 0; i < 60; i++)
      expect(guard.update(0.016, new Vector3(9, 2, 0), false)).toBeNull();
    expect(guard.update(0.016, new Vector3(12, 0, 0), true)).toEqual(new Vector3(0, 0, 0));
  });
});
