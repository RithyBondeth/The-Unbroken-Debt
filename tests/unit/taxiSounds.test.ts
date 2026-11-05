import { expect, it } from "vitest";
import { taxiMeter, taxiMotor, taxiWipers } from "../../src/episodes/ep1/audio/taxiSounds";
import {
  brakeSlither,
  driverGasp,
  ghostRush,
  mudSprint,
  radioStatic,
  windowSlap,
} from "../../src/episodes/ep1/audio/taxiDreadSounds";
import { seededRandom } from "../../src/audio/synth";
it.each([
  taxiMotor,
  taxiWipers,
  taxiMeter,
  radioStatic,
  mudSprint,
  windowSlap,
  driverGasp,
  brakeSlither,
])("generates bounded audible taxi ambience without invalid samples", (synth) => {
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
});

it("rushes past from one side to the other, loudest at its nearest point", () => {
  const rate = 12000,
    [left, right] = ghostRush(rate, seededRandom(9), -1, 1);
  const energy = (c: Float32Array, from: number, to: number) => {
    let sum = 0;
    for (let i = Math.round(from * rate); i < Math.round(to * rate); i++) sum += c[i] * c[i];
    return sum;
  };
  for (const c of [left, right])
    for (const v of c) {
      expect(Number.isFinite(v)).toBe(true);
      expect(Math.abs(v)).toBeLessThanOrEqual(1);
    }
  expect(energy(left, 0.2, 0.45)).toBeGreaterThan(energy(right, 0.2, 0.45));
  expect(energy(right, 0.85, 1.1)).toBeGreaterThan(energy(left, 0.85, 1.1));
  const near = energy(left, 0.5, 0.7) + energy(right, 0.5, 0.7),
    far = energy(left, 1.3, 1.5) + energy(right, 1.3, 1.5);
  expect(near).toBeGreaterThan(far * 4);
});
