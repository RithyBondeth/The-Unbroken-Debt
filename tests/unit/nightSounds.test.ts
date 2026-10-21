import { describe, expect, it } from "vitest";
import * as sounds from "../../src/episodes/ep1/audio/nightSounds";
import { seededRandom } from "../../src/audio/synth";

const RATE = 22050;
const LOOPS = new Set(["frogsLoop", "cricketsLoop", "chantDrone"]);
/** Loops that never fall silent: they must join end to start without a jump. */
const BEDS = new Set(["villageRain"]);

describe("night placeholder sounds", () => {
  for (const [name, make] of Object.entries(sounds)) {
    it(`${name} is finite, audible and within the peak`, () => {
      const samples = make(RATE, seededRandom(5));
      expect(samples.length).toBeGreaterThan(RATE * 0.5);
      let peak = 0;
      for (const s of samples) {
        expect(Number.isFinite(s)).toBe(true);
        peak = Math.max(peak, Math.abs(s));
      }
      expect(peak).toBeGreaterThan(0.3);
      expect(peak).toBeLessThanOrEqual(0.9 + 1e-6);
      if (LOOPS.has(name)) {
        expect(Math.abs(samples[0])).toBeLessThan(0.05);
        expect(Math.abs(samples[samples.length - 1])).toBeLessThan(0.05);
      }
      if (BEDS.has(name)) {
        // The step across the seam is no bigger than steps within the sound.
        let step = 0;
        for (let i = 1; i < samples.length; i++)
          step = Math.max(step, Math.abs(samples[i] - samples[i - 1]));
        expect(Math.abs(samples[0] - samples[samples.length - 1])).toBeLessThanOrEqual(step);
      }
    });
  }
});
