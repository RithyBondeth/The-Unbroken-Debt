import { describe, expect, it } from "vitest";
import { boardCreak, rattlingBreath, rms, seededRandom, wetStep } from "../../src/audio/synth";
import {
  angleError,
  isFrontBackConfusion,
  makeTrials,
  relativeAzimuth,
  summarize,
  wrapAngle,
  type TrialResult,
} from "../../src/audio/localization";

const deg = (d: number) => (d * Math.PI) / 180;

describe("synthesised sounds", () => {
  const rate = 48000;

  it("makes a footstep that starts sharply and fades", () => {
    const step = wetStep(rate, seededRandom(1));
    expect(step.length).toBe(rate * 0.5);
    expect(step.every(Number.isFinite)).toBe(true);
    expect(Math.max(...step.map(Math.abs))).toBeCloseTo(0.9, 5);
    // The onset carries the energy the ear localises by.
    const onset = rms(step, 0, rate * 0.05);
    const tail = rms(step, rate * 0.4, rate * 0.5);
    expect(onset).toBeGreaterThan(tail * 4);
  });

  it("keeps high frequencies in the step (head shadow cues)", () => {
    const step = wetStep(rate, seededRandom(2));
    let diff = 0;
    for (let i = 1; i < rate * 0.05; i++) diff += Math.abs(step[i] - step[i - 1]);
    // Sample-to-sample change: a dull low thump alone would be far smoother.
    expect(diff / (rate * 0.05)).toBeGreaterThan(0.02);
  });

  it("varies between takes", () => {
    const a = wetStep(rate, seededRandom(3));
    const b = wetStep(rate, seededRandom(4));
    expect(rms(a)).not.toBeCloseTo(rms(b), 4);
  });

  it("makes breath and creak without blowing up", () => {
    for (const s of [rattlingBreath(rate, seededRandom(5)), boardCreak(rate, seededRandom(6))]) {
      expect(s.every(Number.isFinite)).toBe(true);
      expect(rms(s)).toBeGreaterThan(0.01);
    }
  });
});

describe("pointing test maths", () => {
  it("measures direction relative to the player's facing", () => {
    expect(relativeAzimuth(0, 0, 0, 0, 5)).toBeCloseTo(0);
    expect(relativeAzimuth(0, 0, 0, 5, 0)).toBeCloseTo(deg(90));
    expect(relativeAzimuth(0, 0, deg(90), 5, 0)).toBeCloseTo(0);
    expect(Math.abs(relativeAzimuth(0, 0, 0, 0, -5))).toBeCloseTo(Math.PI);
  });

  it("wraps errors the short way round", () => {
    expect(angleError(deg(170), deg(-170))).toBeCloseTo(deg(20));
    expect(wrapAngle(deg(370))).toBeCloseTo(deg(10));
  });

  it("spots front/back confusions but not plain misses", () => {
    // Source 30° right of ahead, answered 150° (behind on the right): mirror image.
    expect(isFrontBackConfusion(deg(150), deg(30))).toBe(true);
    expect(isFrontBackConfusion(deg(-160), deg(-20))).toBe(true);
    expect(isFrontBackConfusion(deg(45), deg(30))).toBe(false);
    // Left for right is a different mistake.
    expect(isFrontBackConfusion(deg(-30), deg(30))).toBe(false);
  });

  it("spreads trials around the circle and balances the panning models", () => {
    const trials = makeTrials(10, () => 0.5);
    expect(trials.filter((t) => t.panning === "HRTF").length).toBe(5);
    const sectors = new Set(trials.map((t) => Math.round(wrapAngle(t.azimuth) / deg(36))));
    expect(sectors.size).toBe(10);
    for (const t of trials) expect(t.distance).toBeGreaterThanOrEqual(2);
  });

  it("summarises median error and confusion rate", () => {
    const r = (azimuth: number, response: number): TrialResult => ({
      azimuth: deg(azimuth),
      response: deg(response),
      distance: 4,
      panning: "HRTF",
      seconds: 3,
    });
    const s = summarize([r(0, 10), r(90, 70), r(30, 150), r(-90, -100)]);
    expect(s.medianError * (180 / Math.PI)).toBeCloseTo(15);
    expect(s.frontBackRate).toBe(0.25);
  });
});
