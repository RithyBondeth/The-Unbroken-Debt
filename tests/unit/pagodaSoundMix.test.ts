import { existsSync, readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { Game } from "@/core/Game";
import { WindState } from "@/render/wind";
import { seededRandom } from "@/audio/synth";
import { SPACES } from "@/audio/acoustics";
import { LIMITER, compressorMakeupDb, limiterOutputDb } from "@/audio/AudioSystem";
import {
  DISTANCES,
  GAPS,
  approach,
  breathVoices,
  closeness,
  heartbeat,
  nightDuck,
  pagodaSpace,
  pickTake,
  pitchJitter,
  windLevels,
} from "@/episodes/ep2/audio/pagodaMix";
import {
  BEDS,
  SHOTS,
  SMOT,
  TAKE_TRIM,
  allRecordings,
  soundUrls,
} from "@/episodes/ep2/audio/recordings";
import { PagodaSoundscape } from "@/episodes/ep2/PagodaSoundscape";

describe("Episode 2's mix rules", () => {
  it("spaces repeats out at the gaps the night needs", () => {
    expect(GAPS.whisper).toEqual([60, 150]);
    expect(DISTANCES.whisper).toEqual([4, 8]);
    expect(GAPS.escapeSnap).toEqual([5, 11]);
    expect(DISTANCES.far[0]).toBeGreaterThanOrEqual(30);
    expect(DISTANCES.far[1]).toBeLessThanOrEqual(60);
    expect(GAPS.knock[0]).toBeGreaterThanOrEqual(120);
  });

  it("pitches every repeat a few percent off, both ways", () => {
    const rand = seededRandom(4);
    const rates = Array.from({ length: 400 }, () => pitchJitter(rand));
    expect(Math.min(...rates)).toBeGreaterThanOrEqual(0.95);
    expect(Math.max(...rates)).toBeLessThanOrEqual(1.05);
    expect(Math.min(...rates)).toBeLessThan(0.97);
    expect(Math.max(...rates)).toBeGreaterThan(1.03);
  });

  it("never plays the same take twice running", () => {
    const rand = seededRandom(9);
    let last = 0;
    for (let i = 0; i < 200; i++) {
      const next = pickTake(4, last, rand);
      expect(next).not.toBe(last);
      expect(next).toBeGreaterThanOrEqual(0);
      expect(next).toBeLessThan(4);
      last = next;
    }
  });

  it("fades the same at any frame rate", () => {
    let fast = 0,
      slow = 0;
    for (let i = 0; i < 120; i++) fast = approach(fast, 1, 1 / 120, 0.2);
    for (let i = 0; i < 30; i++) slow = approach(slow, 1, 1 / 30, 0.2);
    expect(fast).toBeCloseTo(slow, 5);
    // A 0.6 s breath fade (tau 0.2) is all but done after 0.6 s.
    expect(fast).toBeGreaterThan(0.95);
  });

  it("beats the heart only with a Pret within about eight metres", () => {
    expect(heartbeat(99).level).toBe(0);
    expect(heartbeat(8.5).level).toBe(0);
    expect(heartbeat(6).level).toBeGreaterThan(0);
    expect(heartbeat(2).level).toBeGreaterThan(heartbeat(6).level);
    expect(heartbeat(2).rate).toBeGreaterThan(heartbeat(7).rate);
    expect(heartbeat(1).level).toBeLessThanOrEqual(0.25);
  });

  it("hushes the night as a Pret draws near", () => {
    expect(nightDuck(99, false)).toBe(0);
    expect(nightDuck(14, false)).toBe(0);
    expect(nightDuck(9, false)).toBeGreaterThan(0);
    expect(nightDuck(3, false)).toBeCloseTo(0.8);
    expect(nightDuck(99, true)).toBeGreaterThan(0);
    expect(closeness(5, 4, 14)).toBeGreaterThan(closeness(10, 4, 14));
  });

  it("lets the wind beds rise with the wind", () => {
    const calm = windLevels(0.3);
    const gust = windLevels(1);
    expect(gust.canopy).toBeGreaterThan(calm.canopy);
    expect(gust.leaves).toBeGreaterThan(calm.leaves);
    expect(windLevels(5).canopy).toBe(windLevels(2).canopy);
  });

  it("keeps five Pret breathing out of step", () => {
    const voices = breathVoices(5, 1.6, seededRandom(2));
    const rates = voices.map((v) => v.rate);
    expect(new Set(rates.map((r) => r.toFixed(3))).size).toBe(5);
    for (const r of rates) expect(Math.abs(r - 1)).toBeLessThanOrEqual(0.08);
    for (const v of voices) expect(v.offset).toBeLessThan(1.6);
    const offsets = voices.map((v) => v.offset).sort((a, b) => a - b);
    expect(offsets.at(-1)! - offsets[0]).toBeGreaterThan(0.3);
  });

  it("knows which room Sora is in", () => {
    expect(pagodaSpace(-18, 12, { safe: true, inHall: false })).toBe("kuti");
    expect(pagodaSpace(22, -2, { safe: false, inHall: true })).toBe("hall");
    expect(pagodaSpace(0, -32, { safe: false, inHall: false })).toBe("library");
    expect(pagodaSpace(0, -22, { safe: false, inHall: false })).toBe("jungle"); // on the bridge
    expect(pagodaSpace(0, 0, { safe: false, inHall: false })).toBe("jungle");
  });
});

describe("Episode 2's rooms", () => {
  it("rings longest in the hall and muffles the night most in the kuti", () => {
    expect(SPACES.hall.rt60[1]).toBeGreaterThan(SPACES.library.rt60[1]);
    expect(SPACES.library.rt60[1]).toBeGreaterThan(SPACES.kuti.rt60[1]);
    expect(SPACES.kuti.occlusion[0]).toBeLessThan(SPACES.hall.occlusion[0]);
    expect(SPACES.jungle.occlusion).toEqual([20000, 1]);
  });
});

describe("the master limiter", () => {
  it("passes everything under its threshold untouched", () => {
    for (const db of [-60, -30, -12, -6, LIMITER.threshold])
      expect(limiterOutputDb(db)).toBeCloseTo(db, 6);
  });

  it("holds full-scale and stacked peaks below -1 dBFS", () => {
    expect(limiterOutputDb(0)).toBeLessThan(-1);
    expect(limiterOutputDb(6)).toBeLessThan(-1);
    expect(limiterOutputDb(12)).toBeLessThan(-1);
  });

  it("knows the make-up gain the browser adds, so it can take it off", () => {
    // Web Audio: (1 / curve(1.0)) ^ 0.6; curve(1.0) = threshold + (0 - threshold) / ratio.
    expect(compressorMakeupDb(-4, 20)).toBeCloseTo(0.6 * 3.8, 6);
    expect(compressorMakeupDb(0, 20)).toBeCloseTo(0, 6);
  });
});

describe("Episode 2's recordings", () => {
  const manifest = JSON.parse(readFileSync("tools/audio/ep2-freesound.json", "utf8")) as {
    licence: string;
    sources: { id: number; user: string; file: string }[];
  };
  const script = readFileSync("tools/audio/make-ep2-audio.sh", "utf8");

  it("has every file the game asks for, Opus and AAC", () => {
    const names = allRecordings();
    expect(names.length).toBeGreaterThan(40);
    for (const name of names)
      for (const ext of ["ogg", "m4a"])
        expect(existsSync(`public/assets/ep2/audio/${name}.${ext}`), `${name}.${ext}`).toBe(true);
    for (const ext of ["ogg", "m4a"]) expect(existsSync(`public/${SMOT}.${ext}`)).toBe(true);
  });

  it("makes every file the game asks for from a listed CC0 source", () => {
    expect(manifest.licence).toBe("CC0 1.0");
    const ids = new Set(manifest.sources.map((s) => String(s.id)));
    for (const name of allRecordings()) {
      const line = script.split("\n").find((l) => new RegExp(`^(loop|shot) ${name} `).test(l));
      expect(line, name).toBeDefined();
      expect(ids.has(line!.split(" ")[2]), `${name} source`).toBe(true);
    }
  });

  it("asks for Opus first and AAC as the fallback", () => {
    expect(soundUrls("amb_ep2_pond", "/")).toEqual([
      "/assets/ep2/audio/amb_ep2_pond.ogg",
      "/assets/ep2/audio/amb_ep2_pond.m4a",
    ]);
    expect(soundUrls(SMOT, "/")[0]).toBe("/assets/ep1/audio/amb_ep1_smot.ogg");
  });

  it("has three insect takes to drift between and one take per bell", () => {
    expect(BEDS.insects.length).toBe(3);
    expect(SHOTS.bells.length).toBe(3);
    for (const kind of ["knock", "splinter", "dog", "owl", "clay", "gust"] as const)
      expect(SHOTS[kind].length, kind).toBeGreaterThanOrEqual(3);
    for (const name of Object.keys(TAKE_TRIM)) expect(allRecordings()).toContain(name);
  });
});

describe("Episode 2's soundscape without audio", () => {
  it("loads and runs silently (the browser fixtures start with audio off)", async () => {
    const game = {
      audio: null,
      footsteps: null,
      threatActive: false,
      wind: new WindState(),
      camera: { globalPosition: new Vector3(0, 1.6, 0) },
      scene: { onDisposeObservable: { addOnce: () => undefined } },
    } as unknown as Game;
    const sounds = new PagodaSoundscape(game);
    await sounds.load();
    const listener = {
      x: 0,
      z: 0,
      yaw: 0,
      stage: "garden",
      safe: false,
      inHall: false,
      fear: 0.5,
      moving: false,
    };
    for (let i = 0; i < 300; i++) {
      sounds.update(1 / 30, [{ x: 3, z: 0 }], true, i > 150);
      sounds.haunt(1 / 30, listener, true);
    }
    expect(() => {
      sounds.ring(0);
      sounds.throw(new Vector3(1, 0, 1));
      sounds.behind(new Vector3(0, 0, 2));
      sounds.crack(Vector3.Zero());
      sounds.laugh(Vector3.Zero());
      sounds.thud(3, Vector3.Zero());
      sounds.groan(1, Vector3.Zero());
      sounds.grind(Vector3.Zero());
      sounds.scare();
      sounds.unease();
      sounds.crash();
      sounds.dawnBell();
      sounds.memory("harvest");
      sounds.cinematicPause(true);
      sounds.dawn();
      sounds.dawn();
    }).not.toThrow();
  });
});
