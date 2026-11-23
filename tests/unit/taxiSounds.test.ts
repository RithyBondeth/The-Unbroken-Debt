import { expect, it } from "vitest";
import { taxiMeter, taxiMotor, taxiWipers } from "@/episodes/ep1/audio/taxiSounds";
import {
  anxiousHeartbeat,
  brakeSlither,
  branchSnap,
  cabinStormBed,
  driverGasp,
  electricalArcZap,
  ghostRush,
  ghostScreechSting,
  mudSprint,
  neckBreathWhisper,
  radioStatic,
  subTensionDrone,
  thunderCrack,
  windowSlap,
} from "@/episodes/ep1/audio/taxiDreadSounds";
import { seededRandom } from "@/audio/synth";

it.each([
  taxiMotor,
  taxiWipers,
  taxiMeter,
  radioStatic,
  mudSprint,
  windowSlap,
  driverGasp,
  brakeSlither,
  anxiousHeartbeat,
  subTensionDrone,
  neckBreathWhisper,
  ghostScreechSting,
  electricalArcZap,
  branchSnap,
  cabinStormBed,
  thunderCrack,
])("generates bounded audible taxi ambience and dread audio without invalid samples", (synth) => {
  const samples = synth(12000, seededRandom(7));
  let energy = 0,
    max = 0,
    allFinite = true;
  for (const sample of samples) {
    if (!Number.isFinite(sample)) allFinite = false;
    energy += sample * sample;
    const mag = Math.abs(sample);
    if (mag > max) max = mag;
  }
  expect(allFinite).toBe(true);
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
  let allFinite = true,
    max = 0;
  for (const c of [left, right])
    for (const v of c) {
      if (!Number.isFinite(v)) allFinite = false;
      const mag = Math.abs(v);
      if (mag > max) max = mag;
    }
  expect(allFinite).toBe(true);
  expect(max).toBeLessThanOrEqual(1);
  expect(energy(left, 0.2, 0.45)).toBeGreaterThan(energy(right, 0.2, 0.45));
  expect(energy(right, 0.85, 1.1)).toBeGreaterThan(energy(left, 0.85, 1.1));
  const near = energy(left, 0.5, 0.7) + energy(right, 0.5, 0.7),
    far = energy(left, 1.3, 1.5) + energy(right, 1.3, 1.5);
  expect(near).toBeGreaterThan(far * 4);
});
