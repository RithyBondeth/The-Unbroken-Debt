import { describe, expect, it } from "vitest";
import * as sounds from "../../src/episodes/ep1/audio/vigilSounds";
import { seededRandom } from "../../src/audio/synth";

const RATE = 22050;

describe("vigil placeholder sounds", () => {
  for (const [name, make] of Object.entries(sounds)) {
    it(`${name} is finite, audible and within the peak`, () => {
      const samples = make(RATE, seededRandom(11));
      expect(samples.length).toBeGreaterThan(RATE * 0.2);
      let peak = 0;
      for (const s of samples) {
        expect(Number.isFinite(s)).toBe(true);
        peak = Math.max(peak, Math.abs(s));
      }
      expect(peak).toBeGreaterThan(0.3);
      expect(peak).toBeLessThanOrEqual(0.9 + 1e-6);
    });
  }

  it("whispers loop without a click", () => {
    const samples = sounds.whispers(RATE, seededRandom(3));
    expect(Math.abs(samples[0])).toBeLessThan(0.05);
    expect(Math.abs(samples[samples.length - 1])).toBeLessThan(0.05);
  });
});
