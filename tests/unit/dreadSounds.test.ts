import { describe, expect, it } from "vitest";
import {
  STING_HIT,
  pressureBed,
  ringingEars,
  sting,
  studioRoom,
  type Sting,
} from "../../src/episodes/ep1/audio/dreadSounds";

const RATE = 22050;

function peak(sides: Float32Array[], from = 0, to = sides[0].length): number {
  let max = 0;
  for (const side of sides) {
    for (let i = from; i < to; i++) {
      expect(Number.isFinite(side[i])).toBe(true);
      max = Math.max(max, Math.abs(side[i]));
    }
  }
  return max;
}

describe("in-game dread", () => {
  it.each(["rise", "shock", "drop", "swell"] as Sting[])(
    "the %s sting is stereo, bounded and ends in silence",
    (kind) => {
      const [left, right] = sting(RATE, kind);
      expect(left.length).toBe(right.length);
      expect(peak([left, right])).toBeLessThanOrEqual(0.95 + 1e-6);
      expect(peak([left, right])).toBeGreaterThan(0.3);
      expect(Math.abs(left[left.length - 1])).toBeLessThan(0.01);
      expect(Math.abs(right[right.length - 1])).toBeLessThan(0.01);
    },
  );

  it.each(["rise", "shock", "drop"] as Sting[])(
    "the %s sting is loudest just after its hit",
    (kind) => {
      const sides = sting(RATE, kind);
      const hit = Math.round(STING_HIT[kind] * RATE);
      const before = hit > RATE * 0.2 ? peak(sides, 0, hit - Math.round(RATE * 0.2)) : 0;
      const after = peak(sides, hit, hit + Math.round(RATE * 0.5));
      expect(after).toBeGreaterThan(before);
    },
  );

  it.each([
    ["pressureBed", pressureBed],
    ["studioRoom", studioRoom],
  ] as const)("the %s loop joins end to start without a jump", (_, make) => {
    for (const side of make(RATE)) {
      let step = 0;
      for (let i = 1; i < side.length; i++) step = Math.max(step, Math.abs(side[i] - side[i - 1]));
      expect(Math.abs(side[0] - side[side.length - 1])).toBeLessThanOrEqual(step);
      expect(side.length).toBeGreaterThan(RATE * 30);
    }
  });

  it("the ringing fades away and stays quiet under the mix", () => {
    const sides = ringingEars(RATE);
    expect(peak(sides)).toBeLessThanOrEqual(0.22 + 1e-6);
    expect(peak(sides, sides[0].length - RATE, sides[0].length)).toBeLessThan(0.02);
  });
});
