import { describe, expect, it } from "vitest";
import * as house from "../../src/episodes/ep1/audio/houseSounds";
import * as actThree from "../../src/episodes/ep1/audio/actThreeSounds";
import { seededRandom } from "../../src/audio/synth";

const RATE = 22050;
/** Loops that fall quiet at their ends. */
const LOOPS = new Set(["heartbeat", "shellacNoise", "ritualDrone"]);
/** Loops that never fall silent: they must join end to start without a jump. */
const BEDS = new Set(["roofRain", "shutterWind", "floorDrips"]);

describe("house and Act III placeholder sounds", () => {
  for (const [name, make] of Object.entries({ ...house, ...actThree })) {
    it(`${name} is finite, audible and within the peak`, () => {
      const samples = make(RATE, seededRandom(13));
      expect(samples.length).toBeGreaterThan(RATE * 0.3);
      let peak = 0;
      for (const s of samples) {
        expect(Number.isFinite(s)).toBe(true);
        peak = Math.max(peak, Math.abs(s));
      }
      expect(peak).toBeGreaterThan(0.15);
      expect(peak).toBeLessThanOrEqual(0.9 + 1e-6);
      if (LOOPS.has(name)) {
        expect(Math.abs(samples[0])).toBeLessThan(0.05);
        expect(Math.abs(samples[samples.length - 1])).toBeLessThan(0.05);
      }
      if (BEDS.has(name)) {
        let step = 0;
        for (let i = 1; i < samples.length; i++)
          step = Math.max(step, Math.abs(samples[i] - samples[i - 1]));
        expect(Math.abs(samples[0] - samples[samples.length - 1])).toBeLessThanOrEqual(step);
      }
    });
  }

  it("keeps the shellac scratch on the record's turn", () => {
    // Five turns at 78 rpm, so the loop never skips a beat.
    expect(house.shellacNoise(RATE, seededRandom(1)).length).toBe(Math.round((60 / 78) * 5 * RATE));
  });
});
