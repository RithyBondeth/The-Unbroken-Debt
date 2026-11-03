import { describe, expect, it } from "vitest";
import * as sounds from "../../src/episodes/ep2/audio/pagodaHorror";
import { seededRandom } from "../../src/audio/synth";

const RATE = 22050;

describe("Episode 2 horror sounds", () => {
  for (const [name, make] of Object.entries(sounds)) {
    it(`${name} is finite, audible and within the peak`, () => {
      const samples = make(RATE, seededRandom(9));
      expect(samples.length).toBeGreaterThan(RATE * 0.5);
      let peak = 0,
        finite = true;
      for (const s of samples) {
        finite &&= Number.isFinite(s);
        peak = Math.max(peak, Math.abs(s));
      }
      expect(finite).toBe(true);
      expect(peak).toBeGreaterThan(0.3);
      expect(peak).toBeLessThanOrEqual(0.9 + 1e-6);
    });
  }
  it("the corrupted chant is longer-drawn and lower than the true one", () => {
    const zeroCrossings = (s: Float32Array) =>
      s.reduce((n, v, i) => n + (i && Math.sign(v) !== Math.sign(s[i - 1]) ? 1 : 0), 0) / s.length;
    const right = sounds.monkChant(RATE, seededRandom(3));
    const wrong = sounds.monkChant(RATE, seededRandom(3), true);
    expect(zeroCrossings(wrong)).toBeLessThan(zeroCrossings(right));
  });
});
