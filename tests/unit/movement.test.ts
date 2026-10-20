import { describe, expect, it } from "vitest";
import { DEFAULT_PLAYER_CONFIG } from "../../src/player/PlayerConfig";
import {
  approach,
  smoothingFactor,
  targetSpeed,
  wishVelocity,
  type MoveIntent,
} from "../../src/player/movement";

const intent = (x: number, z: number): MoveIntent => ({ x, z, hurry: false, crouch: false });

describe("wishVelocity", () => {
  it("moves along +Z when looking straight ahead", () => {
    const v = wishVelocity(intent(0, 1), 0, 2, { x: 0, z: 0 });
    expect(v.x).toBeCloseTo(0);
    expect(v.z).toBeCloseTo(2);
  });

  it("turns with yaw (left-handed: +90° faces +X)", () => {
    const v = wishVelocity(intent(0, 1), Math.PI / 2, 1, { x: 0, z: 0 });
    expect(v.x).toBeCloseTo(1);
    expect(v.z).toBeCloseTo(0);
  });

  it("strafes right towards +X at yaw 0", () => {
    const v = wishVelocity(intent(1, 0), 0, 1, { x: 0, z: 0 });
    expect(v.x).toBeCloseTo(1);
    expect(v.z).toBeCloseTo(0);
  });

  it("does not make diagonals faster", () => {
    const v = wishVelocity(intent(1, 1), 0.3, 1.6, { x: 0, z: 0 });
    expect(Math.hypot(v.x, v.z)).toBeCloseTo(1.6);
  });

  it("keeps partial stick input partial", () => {
    const v = wishVelocity(intent(0, 0.5), 0, 2, { x: 0, z: 0 });
    expect(v.z).toBeCloseTo(1);
  });
});

describe("targetSpeed", () => {
  const c = DEFAULT_PLAYER_CONFIG;
  it("walks, hurries and crouches at the configured speeds", () => {
    expect(targetSpeed("stand", false, c)).toBe(c.walkSpeed);
    expect(targetSpeed("stand", true, c)).toBe(c.hurrySpeed);
    expect(targetSpeed("crouch", false, c)).toBe(c.crouchSpeed);
  });

  it("ignores hurry while crouched", () => {
    expect(targetSpeed("crouch", true, c)).toBe(c.crouchSpeed);
  });
});

describe("approach and smoothing", () => {
  it("moves towards the target by at most maxDelta", () => {
    const out = approach({ x: 0, z: 0 }, { x: 3, z: 4 }, 1, { x: 0, z: 0 });
    expect(Math.hypot(out.x, out.z)).toBeCloseTo(1);
    expect(out.x / out.z).toBeCloseTo(0.75);
  });

  it("snaps to the target when close enough", () => {
    expect(approach({ x: 0, z: 0 }, { x: 0.1, z: 0 }, 1, { x: 0, z: 0 })).toEqual({ x: 0.1, z: 0 });
  });

  it("gives a frame-rate independent smoothing factor", () => {
    const twoHalfSteps = 1 - (1 - smoothingFactor(0.01, 0.1)) ** 2;
    expect(twoHalfSteps).toBeCloseTo(smoothingFactor(0.02, 0.1));
    expect(smoothingFactor(0.016, 0)).toBe(1);
  });
});
