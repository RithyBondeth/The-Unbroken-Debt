import { expect, it } from "vitest";
import { Flags } from "../../src/core/Flags";
import { passageReady, passageRequired } from "../../src/episodes/ep1/act1/VigilPassage";
import { dreadBed, spiritRattle } from "../../src/episodes/ep1/audio/presenceSounds";
import { seededRandom } from "../../src/audio/synth";

it("cannot start on arrival, during exploration or before the completed offering and cycle", () => {
  const flags = new Flags();
  expect(passageReady(flags, true, true)).toBe(false);
  flags.set("ep1.vigil.started", true);
  flags.set("ep1.betel.done", true);
  expect(passageReady(flags, true, true)).toBe(false);
  flags.set("ep1.incense.cyclePassed", true);
  flags.set("ep1.arrival.phoneFlow", true);
  expect(passageReady(flags, true, true)).toBe(false);
  flags.set("ep1.arrival.matchesTaken", true);
  expect(passageReady(flags, false, true)).toBe(false);
  expect(passageReady(flags, true, false)).toBe(false);
  expect(passageReady(flags, true, true)).toBe(true);
  const restored = new Flags();
  restored.load(flags.toJSON());
  expect(passageReady(restored, true, true)).toBe(true);
  restored.set("ep1.early.complete", true);
  expect(passageRequired(restored)).toBe(false);
  expect(passageReady(restored, true, true)).toBe(false);
  flags.set("ep1.act2.started", true);
  expect(passageRequired(flags)).toBe(false);
});

it("keeps the tension sounds finite, bounded and click-free at loop boundaries", () => {
  for (const make of [dreadBed, spiritRattle]) {
    const samples = make(24000, seededRandom(41));
    let finite = true,
      peak = 0,
      energy = 0;
    for (const sample of samples) {
      finite &&= Number.isFinite(sample);
      peak = Math.max(peak, Math.abs(sample));
      energy += sample * sample;
    }
    expect(finite).toBe(true);
    expect(peak).toBeLessThanOrEqual(0.651);
    expect(Math.sqrt(energy / samples.length)).toBeGreaterThan(0.02);
    expect(Math.abs(samples[0])).toBeLessThan(0.001);
    expect(Math.abs(samples.at(-1)!)).toBeLessThan(0.001);
  }
});
