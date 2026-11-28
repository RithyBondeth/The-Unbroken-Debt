import { describe, expect, it } from "vitest";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import {
  KRASUE_FIRST_WAIT,
  KRASUE_PASS_RANGE,
  KrasueBrain,
} from "@/episodes/ep1/entities/KrasueBrain";
import { KRASUE_PADDY_PATHS, exposedToPaddies } from "@/episodes/ep1/data/krasue";
import { krasueLament, krasueShriek, krasueSting } from "@/audio/sounds/krasueSounds";
import { rms, seededRandom } from "@/audio/synth";

function tick(
  brain: KrasueBrain,
  seconds: number,
  eye: Vector3,
  looking = false,
  lampOpen = false,
  exposed = true,
): void {
  for (let i = 0; i < Math.ceil(seconds * 60); i++) {
    brain.update(1 / 60, eye, looking, lampOpen, exposed);
  }
}

describe("Krasue rice-field exposure", () => {
  it("treats the road, paddies, and open yard as exposed while sheltering indoors", () => {
    expect(exposedToPaddies({ x: 0, y: 0, z: 32 })).toBe(true);
    expect(exposedToPaddies({ x: 18, y: 0, z: 22 })).toBe(true);
    expect(exposedToPaddies({ x: 0, y: 2.5, z: -15 })).toBe(false);
    expect(exposedToPaddies({ x: 24, y: 0, z: -18 })).toBe(false);
    expect(exposedToPaddies({ x: -24, y: 0, z: -22 })).toBe(false);
  });
});

describe("Rice-Field Krasue brain", () => {
  it("stays dormant until the sighting wait expires, then drifts over the rice paddies", () => {
    const brain = new KrasueBrain();
    const roadEye = new Vector3(0, 1.58, 32);
    expect(brain.state).toBe("dormant");
    expect(brain.hidden).toBe(true);

    tick(brain, KRASUE_FIRST_WAIT - 1, roadEye, false, false, true);
    expect(brain.state).toBe("dormant");

    tick(brain, 2, roadEye, false, false, true);
    expect(brain.state).toBe("drifting");
    expect(brain.hidden).toBe(false);
    expect(brain.sightings).toBe(1);
    expect(brain.redness).toBeCloseTo(KRASUE_PADDY_PATHS[0].baseRedness, 1);
  });

  it("shifts emerald-green to blood-red when Sora holds an open lamp nearby, and calms when doused", () => {
    const brain = new KrasueBrain();
    brain.summon(0); // west_paddies_green (baseRedness 0)
    // Stand near the first waypoint with an open lamp and watch it
    const nearEye = brain.position.add(new Vector3(-12, -1, 0));
    expect(brain.redness).toBeLessThan(0.1);

    tick(brain, 2.2, nearEye, true, true, true);
    expect(brain.state).toBe("alert");
    expect(brain.alerts).toBe(1);
    expect(brain.redness).toBeGreaterThan(0.6);

    // Dousing the lamp and looking away calms it into retreating
    tick(brain, 1.8, nearEye, false, false, true);
    expect(brain.state).toBe("retreating");
  });

  it("approaches and makes a close pass if Sora keeps the lamp open after turning red", () => {
    const brain = new KrasueBrain();
    brain.summon(0);
    // Stand ~18m away in the open fields so alert -> approaching -> pass steps are clearly observable
    const nearEye = brain.position.add(new Vector3(0, -1, 18));

    // Agitate to alert
    tick(brain, 2.0, nearEye, true, true, true);
    expect(brain.state).toBe("alert");

    // Continue shining lamp past the 1.9s alert warning into approaching
    tick(brain, 2.2, nearEye, true, true, true);
    expect(brain.state).toBe("approaching");

    for (let i = 0; i < 60 * 10 && brain.state === "approaching"; i++) {
      brain.update(1 / 60, nearEye, true, true, true);
    }
    expect(brain.passes).toBe(1);
    expect(brain.state).toBe("pass");
    expect(Vector3.Distance(brain.position, nearEye)).toBeLessThanOrEqual(KRASUE_PASS_RANGE + 0.5);

    // After pass it retreats and eventually returns to dormant
    tick(brain, 10, nearEye, false, false, true);
    expect(brain.state).toBe("dormant");
  });

  it("breaks off an approach immediately when Sora steps under shelter and resets cleanly", () => {
    const brain = new KrasueBrain();
    brain.summon(1);
    const nearEye = brain.position.add(new Vector3(0, -1, 18));
    tick(brain, 4.1, nearEye, true, true, true);
    expect(brain.state).toBe("approaching");

    // Step indoors (playerExposed = false)
    tick(brain, 0.2, nearEye, false, true, false);
    expect(brain.state).toBe("retreating");

    brain.reset();
    expect(brain.state).toBe("dormant");
    expect(brain.hidden).toBe(true);
    expect(brain.agitation).toBe(0);
    expect(brain.redness).toBe(0);
  });
});

describe("Krasue audio", () => {
  it("krasueSting stabs at once, starts and ends silent, and stays under its peak", () => {
    const rate = 16000;
    const samples = krasueSting(rate, seededRandom(25));
    expect(samples.every(Number.isFinite)).toBe(true);
    expect(samples.every((s) => Math.abs(s) <= 0.850001)).toBe(true);
    expect(rms(samples, 0, rate * 0.5)).toBeGreaterThan(rms(samples, rate * 2.5));
    expect(samples.at(-1)).toBe(0);
    expect(samples).toEqual(krasueSting(rate, seededRandom(25)));
  });
  for (const make of [krasueLament, krasueShriek]) {
    it(`${make.name} is audible, finite, deterministic and peak limited`, () => {
      const samples = make(16000, seededRandom(25));
      expect(samples.every(Number.isFinite)).toBe(true);
      expect(rms(samples)).toBeGreaterThan(0.02);
      expect(samples.every((s) => Math.abs(s) <= 0.600001)).toBe(true);
      expect(samples).toEqual(make(16000, seededRandom(25)));
      if (make === krasueShriek) {
        expect(samples[0]).toBe(0);
        expect(samples.at(-1)).toBe(0);
      }
    });
  }
});
