import { expect, it } from "vitest";
import { taxiMotor, taxiWipers } from "../../src/episodes/ep1/audio/taxiSounds";
import { seededRandom } from "../../src/audio/synth";
it.each([taxiMotor, taxiWipers])(
  "generates bounded audible taxi ambience without invalid samples",
  (synth) => {
    const samples = synth(12000, seededRandom(7));
    let energy = 0,
      max = 0;
    for (const sample of samples) {
      expect(Number.isFinite(sample)).toBe(true);
      energy += sample * sample;
      max = Math.max(max, Math.abs(sample));
    }
    expect(max).toBeLessThanOrEqual(1);
    expect(energy / samples.length).toBeGreaterThan(0.00001);
  },
);
