import { describe, expect, it } from "vitest";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { KrasueBrain } from "../../src/episodes/ep1/entities/KrasueBrain";
import {
  inKrasueKitchen,
  KRASUE_WINDOWS,
  throughKrasueWindow,
} from "../../src/episodes/ep1/data/krasue";
import { krasueLament, krasueShriek } from "../../src/episodes/ep1/audio/krasueSounds";
import { rms, seededRandom } from "../../src/audio/synth";

const eye = new Vector3(4.8, 4.08, -13);
function tick(brain: KrasueBrain, seconds: number, seen = true, lamp = false): void {
  for (let i = 0; i < Math.ceil(seconds * 60); i++) brain.update(1 / 60, eye, seen, lamp);
}

describe("Krasue window sight", () => {
  for (const w of KRASUE_WINDOWS) {
    it(`uses the actual ${w.id} opening, blocking boards, sill and lintel`, () => {
      const outside = w.center.add(w.normal.scale(2.5));
      const inside = w.center.subtract(w.normal.scale(1.3));
      expect(throughKrasueWindow(outside, inside, w)).toBe(true);
      expect(throughKrasueWindow(outside, inside.add(w.tangent.scale(2)), w)).toBe(false);
      expect(throughKrasueWindow(outside, inside.add(new Vector3(0, 1, 0)), w)).toBe(false);
      expect(throughKrasueWindow(outside, inside.subtract(new Vector3(0, 1.2, 0)), w)).toBe(false);
      expect(throughKrasueWindow(outside, outside.add(w.normal), w)).toBe(false);
    });
  }
  it("keeps downstairs, adjacent rooms and the veranda outside the ambush", () => {
    expect(inKrasueKitchen(eye)).toBe(true);
    for (const p of [
      new Vector3(4.8, 1.58, -13),
      new Vector3(2.8, 4.08, -13),
      new Vector3(4.8, 4.08, -15),
      new Vector3(4.8, 4.08, -11),
    ])
      expect(inKrasueKitchen(p)).toBe(false);
  });
});

describe("Krasue obstacle", () => {
  it("flies a spatial patrol outside either window with a changing heading", () => {
    for (const window of KRASUE_WINDOWS) {
      const b = new KrasueBrain();
      b.selectWindow(window);
      const side: number[] = [],
        depth: number[] = [],
        height: number[] = [];
      for (let i = 0; i < 1800; i++) {
        b.update(1 / 60, eye, false, false);
        const offset = b.position.subtract(window.center);
        side.push(Vector3.Dot(offset, window.tangent));
        depth.push(Vector3.Dot(offset, window.normal));
        height.push(offset.y);
        expect(b.direction.length()).toBeCloseTo(1, 5);
      }
      const span = (a: number[]) => Math.max(...a) - Math.min(...a);
      expect(span(side)).toBeGreaterThan(2);
      expect(span(depth)).toBeGreaterThan(1.6);
      expect(span(height)).toBeGreaterThan(0.42);
      expect(Math.min(...depth)).toBeGreaterThan(1.9);
    }
  });
  it("patrols without seeing through walls and ignores a fleeting exposure", () => {
    const b = new KrasueBrain();
    tick(b, 8, false);
    expect(b.state).toBe("patrol");
    expect(b.position.x).toBeGreaterThan(7.5);
    tick(b, 0.15);
    tick(b, 0.3, false);
    expect(b.state).toBe("patrol");
  });
  it("warns, flies to the outside of the window, then kills an exposed player even if they turn away", () => {
    const b = new KrasueBrain();
    tick(b, 0.35);
    expect(b.state).toBe("watching");
    tick(b, 0.4, true, false);
    expect(b.state).toBe("charging");
    for (let i = 0; i < 150 && b.state !== "caught"; i++) {
      b.update(1 / 60, eye, true, false);
      expect(b.position.x).toBeGreaterThanOrEqual(6.75);
    }
    expect(b.state).toBe("caught");
  });
  it("lets cover cancel suspicion and escape a charge, then rearms for later visits", () => {
    const b = new KrasueBrain();
    tick(b, 0.4);
    tick(b, 1, false);
    expect(b.state).toBe("cooldown");
    tick(b, 7, false);
    expect(b.state).toBe("patrol");
    tick(b, 0.9);
    expect(b.state).toBe("charging");
    tick(b, 0.3, false);
    expect(b.state).toBe("searching");
    tick(b, 3, false);
    expect(b.state).toBe("cooldown");
    expect(b.active).toBe(false);
    expect(b.position.x).toBeGreaterThan(6.4);
  });
  it("cannot skip its warning after a background stall and resets cleanly", () => {
    const b = new KrasueBrain();
    b.update(120, eye, true, true);
    expect(b.state).toBe("patrol");
    tick(b, 1.4);
    b.reset();
    expect(b.state).toBe("patrol");
    expect(b.suspicion).toBe(0);
    expect(b.active).toBe(false);
  });
  it("confirms one sighting, then accelerates into its rush", () => {
    const b = new KrasueBrain();
    tick(b, 0.3);
    expect(b.state).toBe("watching");
    expect(b.sightings).toBe(1);
    tick(b, 0.4);
    expect(b.state).toBe("charging");
    const speed = b.speed;
    tick(b, 0.2);
    expect(b.speed).toBeGreaterThan(speed);
    expect(b.sightings).toBe(1);
    tick(b, 1);
    expect(b.sightings).toBe(1);
  });
  it("only changes windows while disengaged and reacts faster to an exposed lamp", () => {
    const dark = new KrasueBrain(),
      lit = new KrasueBrain();
    lit.selectWindow(KRASUE_WINDOWS[1]);
    expect(lit.position.z).toBeGreaterThan(-10);
    tick(dark, 0.6, true, false);
    tick(lit, 0.6, true, true);
    expect(dark.state).toBe("watching");
    expect(lit.state).toBe("charging");
    lit.selectWindow(KRASUE_WINDOWS[0]);
    expect(lit.window.id).toBe("south");
  });
});

describe("Krasue audio", () => {
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
