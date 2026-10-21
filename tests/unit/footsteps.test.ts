import { describe, expect, it } from "vitest";
import { Footsteps, pickTake, stepUrls, stepVolume } from "../../src/audio/Footsteps";
import { mudSuction, seededRandom } from "../../src/audio/synth";

describe("footsteps", () => {
  it("never plays the same take twice in a row, and uses them all", () => {
    const rand = seededRandom(3);
    const seen = new Set<number>();
    let last = -1;
    for (let i = 0; i < 200; i++) {
      const k = pickTake(5, last, rand);
      expect(k).not.toBe(last);
      expect(k).toBeGreaterThanOrEqual(0);
      expect(k).toBeLessThan(5);
      seen.add(k);
      last = k;
    }
    expect(seen.size).toBe(5);
    expect(pickTake(1, 0, rand)).toBe(0);
  });

  it("is softer crouching and louder hurrying than walking", () => {
    const walk = stepVolume(0.35);
    expect(walk).toBeCloseTo(0.3);
    expect(stepVolume(0.12)).toBeLessThan(walk);
    expect(stepVolume(0.12)).toBeGreaterThan(0);
    expect(stepVolume(1)).toBeGreaterThan(walk);
  });

  it("gives every surface a set, Opus first", () => {
    for (const surface of ["teak", "dirt", "mud", "leaves", "stone", "water"] as const)
      expect(Footsteps.setFor(surface)).toBeTruthy();
    const urls = stepUrls("mud", 3);
    expect(urls[0]).toMatch(/sfx_step_mud_003\.ogg$/);
    expect(urls[1]).toMatch(/sfx_step_mud_003\.m4a$/);
  });

  it("makes a finite, audible mud suction within the peak", () => {
    const samples = mudSuction(22050, seededRandom(9));
    let peak = 0;
    for (const s of samples) {
      expect(Number.isFinite(s)).toBe(true);
      peak = Math.max(peak, Math.abs(s));
    }
    expect(peak).toBeGreaterThan(0.3);
    expect(peak).toBeLessThanOrEqual(0.8 + 1e-6);
  });
});
