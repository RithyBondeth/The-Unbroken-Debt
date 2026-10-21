import { describe, expect, it } from "vitest";
import * as sounds from "../../src/episodes/ep1/audio/prologueSounds";
import { seededRandom } from "../../src/audio/synth";

const RATE = 22050;
const LOOPS = new Set(["rainLoop", "clockLoop", "phoneRing", "lineStatic"]);

describe("prologue placeholder sounds", () => {
  for (const [name, make] of Object.entries(sounds)) {
    it(`${name} is finite, audible and within the peak`, () => {
      const samples = make(RATE, seededRandom(7));
      expect(samples.length).toBeGreaterThan(RATE * 0.2);
      let peak = 0;
      for (const s of samples) {
        expect(Number.isFinite(s)).toBe(true);
        peak = Math.max(peak, Math.abs(s));
      }
      expect(peak).toBeGreaterThan(0.3);
      expect(peak).toBeLessThanOrEqual(0.9 + 1e-6);
      if (LOOPS.has(name)) {
        // Loops wrap without a click: both ends near silence.
        expect(Math.abs(samples[0])).toBeLessThan(0.05);
        expect(Math.abs(samples[samples.length - 1])).toBeLessThan(0.05);
      }
    });
  }
});
