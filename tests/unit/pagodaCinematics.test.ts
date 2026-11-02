import { describe, it, expect } from "vitest";
import { CinematicClock, dialogueScript } from "../../src/episodes/ep2/cinematics/Timeline";
import {
  SOPHAL_SCENE,
  HARVEST_SCENE,
  FAMINE_SCENE,
  BARGAIN_SCENE,
  COLLAPSE_SCENE,
  DAWN_SCENE,
  PHOTO_SCENE,
} from "../../src/episodes/ep2/cinematics/scripts";
import { fallingHeight } from "../../src/episodes/ep2/cinematics/LibraryCollapse";
import { harvestMusic } from "../../src/episodes/ep2/cinematics/harvestMusic";
import {
  PAGODA_BALANCE as B,
  EscapeClock,
  inKuti,
  hearingRadius,
  simulationStep,
} from "../../src/episodes/ep2/data/balance";
import { gardenClear, gardenPath, PretBrain } from "../../src/episodes/ep2/PretBrain";
import { PATROLS } from "../../src/episodes/ep2/data/pagoda";

describe("Episode 2 cinematic playback", () => {
  it("keeps every English caption visible at a readable pace, without overlapping cues", () => {
    for (const script of [
      SOPHAL_SCENE,
      HARVEST_SCENE,
      FAMINE_SCENE,
      BARGAIN_SCENE,
      COLLAPSE_SCENE,
      DAWN_SCENE,
      PHOTO_SCENE,
    ]) {
      let end = 0;
      for (const c of script.cues) {
        expect(c.at).toBeGreaterThanOrEqual(end);
        expect(c.duration).toBeGreaterThanOrEqual(3);
        expect(c.text.split(/\s+/).length / c.duration).toBeLessThanOrEqual(3.4);
        expect(/[\u1780-\u17ff]/.test(c.text)).toBe(false);
        end = c.at + c.duration;
      }
      expect(end).toBeLessThanOrEqual(script.duration);
    }
  });
  it("pauses both captions and animation time when hidden or paused, and skips cleanly", () => {
    const s = dialogueScript("test", "Test", [["Sora", "The roof is splitting."]]);
    const c = new CinematicClock(s);
    for (let i = 0; i < 10; i++) c.update(0.1);
    const at = c.elapsed,
      cue = c.cue;
    c.paused = true;
    c.update(0.1);
    expect(c.elapsed).toBe(at);
    expect(c.cue).toBe(cue);
    c.paused = false;
    c.update(0.1, false);
    expect(c.elapsed).toBe(at);
    c.skip();
    expect(c.finished).toBe(true);
    expect(c.cue).toBeNull();
    expect(c.skipped).toBe(true);
  });
  it("caps stalls and never sends debris below the library floor", () => {
    const c = new CinematicClock(HARVEST_SCENE);
    c.update(90);
    expect(c.elapsed).toBe(0.1);
    for (let t = 0; t < 20; t += 0.05) expect(fallingHeight(t, 5.5)).toBeGreaterThanOrEqual(1.4);
    expect(fallingHeight(0, 5.5)).toBe(5.5);
    expect(fallingHeight(2, 5.5)).toBe(1.4);
  });
  it("provides a finite original instrumental score with quiet loop boundaries", () => {
    const music = harvestMusic(8000);
    expect(music.length).toBe(24 * 8000);
    expect(music.every(Number.isFinite)).toBe(true);
    expect(music.some((v) => Math.abs(v) > 0.02)).toBe(true);
    expect(Math.abs(music[0]) + Math.abs(music.at(-1)!)).toBeLessThan(0.001);
    expect(Math.max(...music.slice(0, 8000).map(Math.abs))).toBeLessThan(1);
  });
});

describe("Episode 2 fairness and escape allowance", () => {
  it("keeps the kuti a sanctuary, including catches through its wall", () => {
    expect(inKuti({ x: -18, z: 12 })).toBe(true);
    expect(inKuti({ x: -14, z: 12 })).toBe(false);
    expect(gardenClear({ x: -16, z: 12 })).toBe(false);
    expect(gardenClear({ x: -14, z: 12 })).toBe(true);
    const brain = new PretBrain(PATROLS[0]);
    brain.position.x = -14.2;
    brain.position.z = 12;
    expect(brain.hear({ x: -14.7, z: 12 }, 2)).toBe(false);
    expect(brain.catches({ x: -14.7, z: 12 })).toBe(false);
    for (const p of gardenPath({ x: -14, z: 12 }, { x: -16, z: 12 }))
      expect(gardenClear(p)).toBe(true);
  });
  it("lets a crouched dirt step remain quiet while a bowl carries much further", () => {
    const quiet = hearingRadius(0.12 * 0.65),
      walk = hearingRadius(0.35 * 0.65),
      leaves = hearingRadius(0.35 * 1.8),
      bowl = hearingRadius(B.bowlLoudness);
    expect(quiet).toBeLessThan(2.1);
    expect(walk).toBeLessThan(4);
    expect(leaves).toBeGreaterThan(walk);
    expect(bowl).toBeGreaterThan(15);
    expect(hearingRadius(0)).toBe(0);
  });
  it("does not make enemies faster than the physics controller on a slow frame", () => {
    for (const frame of [1 / 120, 1 / 60, 1 / 30, 1 / 15, 0.5])
      expect(simulationStep(frame)).toBe(Math.min(frame, 1 / 30));
    expect(simulationStep(-1)).toBe(0);
  });
  it("gives a walkable escape budget and no lost time in menus or a hidden tab", () => {
    const clock = new EscapeClock();
    clock.update(30, false);
    expect(clock.remaining).toBe(90);
    expect(clock.update(31, true)).toEqual([60]);
    expect(clock.update(1, true)).toEqual([]);
    expect(clock.update(35, true)).toEqual([30]);
    expect(clock.update(12, true)).toEqual([12]);
    clock.update(30, true);
    expect(clock.expired).toBe(true);
    expect(clock.update(10, true)).toEqual([]);
    // The real bridge + west aisle route is ~62m; even an ordinary walk has ample margin.
    expect(B.escapeSeconds - 62 / 1.6).toBeGreaterThan(45);
  });
});
