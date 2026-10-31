import { describe, expect, it } from "vitest";
import { rms, seededRandom } from "../../src/audio/synth";
import { FRONT_SPEED, GUST_RISE, WindState, type Gust } from "../../src/render/wind";
import type { PlantSite } from "../../src/render/plantHeights";
import {
  GUST_SECONDS,
  bambooKnock,
  carBuffet,
  crownRustle,
  frondClatter,
  gustSwell,
  leafHiss,
  trunkGroan,
  windRoar,
} from "../../src/episodes/ep1/audio/windSounds";
import {
  bedLevels,
  gustOffset,
  pickTree,
  stingGust,
  treeSound,
} from "../../src/episodes/ep1/audio/WindAudio";

const RATE = 22050;
const peak = (s: Float32Array) => s.reduce((m, v) => Math.max(m, Math.abs(v)), 0);

describe("wind sounds", () => {
  const all = {
    windRoar,
    leafHiss,
    gustSwell,
    trunkGroan,
    bambooKnock,
    frondClatter,
    crownRustle,
    carBuffet,
  };

  it("are finite, audible, never clip, and repeat exactly from the same seed", () => {
    for (const [name, make] of Object.entries(all)) {
      const a = make(RATE, seededRandom(11)),
        b = make(RATE, seededRandom(11));
      expect(a.every(Number.isFinite), name).toBe(true);
      expect(peak(a), name).toBeLessThanOrEqual(0.9);
      expect(rms(a), name).toBeGreaterThan(0.01);
      expect(Array.from(a.subarray(0, 512))).toEqual(Array.from(b.subarray(0, 512)));
    }
  });

  it("makes the beds seamless loops at the same length per seed, so takes pair as stereo", () => {
    for (const make of [windRoar, leafHiss]) {
      const left = make(RATE, seededRandom(1)),
        right = make(RATE, seededRandom(2));
      expect(left.length).toBe(right.length);
      const edge = rms(left, 0, 256) + rms(left, left.length - 256);
      // No step at the seam: the wrap is no louder than the bed itself.
      expect(Math.abs(left[0] - left[left.length - 1])).toBeLessThan(rms(left) * 4);
      expect(edge).toBeGreaterThan(0);
    }
  });

  it("swells a gust to its height where the wind's own envelope peaks", () => {
    const gust = gustSwell(RATE, seededRandom(3));
    expect(gust.length).toBe(Math.round(RATE * GUST_SECONDS));
    const at = (t: number) =>
      rms(gust, Math.round((t - 0.25) * RATE), Math.round((t + 0.25) * RATE));
    const height = at(GUST_SECONDS * GUST_RISE);
    expect(height).toBeGreaterThan(at(0.4) * 3);
    expect(height).toBeGreaterThan(at(GUST_SECONDS - 0.4) * 3);
  });

  it("keeps a trunk's groan low and bamboo's knock bright", () => {
    const zeroCrossings = (s: Float32Array) => {
      let n = 0;
      for (let i = 1; i < s.length; i++) if (s[i - 1] < 0 !== s[i] < 0) n++;
      return n / (s.length / RATE);
    };
    expect(zeroCrossings(trunkGroan(RATE, seededRandom(4)))).toBeLessThan(
      zeroCrossings(bambooKnock(RATE, seededRandom(4))),
    );
  });
});

describe("wind audio", () => {
  it("raises the beds with the wind, keeping them low and dull inside the taxi", () => {
    const calm = bedLevels(0.1),
      gusting = bedLevels(1.5),
      car = bedLevels(1.5, true);
    expect(bedLevels(0)).toEqual({ roar: 0, hiss: 0 });
    expect(gusting.roar).toBeGreaterThan(calm.roar * 5);
    expect(gusting.hiss).toBeGreaterThan(calm.hiss * 5);
    expect(car.roar).toBeLessThan(gusting.roar * 0.5);
    expect(car.hiss / car.roar).toBeLessThan(gusting.hiss / gusting.roar);
    expect(bedLevels(9).roar).toBe(bedLevels(2).roar);
  });

  it("gives each tree its own voice, dead wood groaning more as the gusts lean on it", () => {
    const random = seededRandom(1);
    expect(treeSound("bamboo", 0.5, random)).toBe("bamboo");
    expect(treeSound("palm", 0.5, random)).toBe("fronds");
    expect(treeSound("dead", 0.2, random)).toBe("groan");
    const leafy = (amount: number) =>
      Array.from({ length: 200 }, () => treeSound("leafy", amount, random));
    const light = leafy(0.5),
      hard = leafy(1.4);
    const groans = (list: string[]) => list.filter((s) => s === "groan").length;
    expect(groans(light)).toBeGreaterThan(40);
    expect(light.filter((s) => s === "rustle").length).toBeGreaterThan(80);
    expect(groans(hard)).toBeGreaterThan(groans(light) * 1.3);
  });

  it("picks trees in earshot, never underfoot, mostly where the wind is hardest", () => {
    const site = (x: number, z: number): PlantSite => ({ x, y: 0, z, height: 12, voice: "leafy" });
    const sites = [site(1, 1), site(0, 10), site(10, 0), site(60, 0)];
    const windy = (x: number) => (x > 5 ? 1.5 : 0.3);
    const random = seededRandom(2);
    const picks = new Map<PlantSite, number>();
    for (let i = 0; i < 400; i++) {
      const p = pickTree(sites, 0, 0, windy, random)!;
      picks.set(p, (picks.get(p) ?? 0) + 1);
    }
    expect(picks.has(sites[0])).toBe(false);
    expect(picks.has(sites[3])).toBe(false);
    expect(picks.get(sites[2])!).toBeGreaterThan(picks.get(sites[1])! * 5);
    expect(pickTree([site(1, 1)], 0, 0, windy, random)).toBeNull();
  });

  it("sweeps a gust's sound from upwind, over the listener, on downwind", () => {
    const gust: Gust = { start: 10, duration: 5, peak: 1, origin: -20 };
    const arrives = 10 + 20 / FRONT_SPEED + GUST_RISE * 5;
    expect(gustOffset(gust, arrives - 1, 0)).toBeCloseTo(-FRONT_SPEED);
    expect(gustOffset(gust, arrives, 0)).toBeCloseTo(0);
    expect(gustOffset(gust, arrives + 1, 0)).toBeCloseTo(FRONT_SPEED);
  });

  it("lands a sting's gust on its hit", () => {
    const wind = new WindState(seededRandom(9));
    wind.base = 0.5;
    for (let i = 0; i < 600; i++) wind.update(1 / 60, 0, 0);
    wind.gusts.length = 0;
    stingGust(wind, "rise", 1, 1.6);
    expect(wind.gusts.length).toBe(1);
    let best = { t: 0, v: 0 };
    const from = wind.time;
    for (let i = 0; i < 60 * 5; i++) {
      wind.update(1 / 60, 0, 0);
      const v = wind.gustAt(0, 0);
      if (v > best.v) best = { t: wind.time - from, v };
    }
    expect(best.t).toBeGreaterThan(1.1);
    expect(best.t).toBeLessThan(2.1);
    stingGust(wind, "drop", 1, 0);
    expect(wind.gusts.length).toBeLessThanOrEqual(1);
  });
});
