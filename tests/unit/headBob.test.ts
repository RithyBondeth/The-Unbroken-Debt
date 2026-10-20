import { describe, expect, it } from "vitest";
import { advanceStride, bobOffsetX, bobOffsetY, type StrideState } from "../../src/player/headBob";

describe("advanceStride", () => {
  it("lands a footstep at half and full stride", () => {
    const state: StrideState = { phase: 0, amplitude: 0 };
    const result = { stepped: false };
    expect(advanceStride(state, 0.3, 1, result).stepped).toBe(false);
    expect(advanceStride(state, 0.3, 1, result).stepped).toBe(true); // crosses 0.5
    expect(advanceStride(state, 0.3, 1, result).stepped).toBe(false);
    expect(advanceStride(state, 0.3, 1, result).stepped).toBe(true); // crosses 1.0
    expect(state.phase).toBeCloseTo(0.2);
  });

  it("does nothing when standing still", () => {
    const state: StrideState = { phase: 0.4, amplitude: 0 };
    expect(advanceStride(state, 0, 0.7, { stepped: false }).stepped).toBe(false);
    expect(state.phase).toBe(0.4);
  });
});

describe("bob offsets", () => {
  it("puts the eye lowest at each footfall", () => {
    expect(bobOffsetY(0, 0.02)).toBeCloseTo(-0.01);
    expect(bobOffsetY(0.5, 0.02)).toBeCloseTo(-0.01);
    expect(bobOffsetY(0.25, 0.02)).toBeCloseTo(0.01);
  });

  it("sways once per stride", () => {
    expect(bobOffsetX(0.25, 0.02)).toBeCloseTo(0.01);
    expect(bobOffsetX(0.75, 0.02)).toBeCloseTo(-0.01);
  });
});
