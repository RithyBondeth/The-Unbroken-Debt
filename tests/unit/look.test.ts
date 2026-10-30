import { describe, expect, it } from "vitest";
import {
  buildLut,
  gradeColor,
  NEUTRAL_GRADE,
  tintFromHex,
  type GradeParams,
} from "../../src/render/grade";
import { decayScare, EyeAdaptation, lookValues, targetExposure } from "../../src/render/look";
import { EP1_GRADE } from "../../src/episodes/ep1/data/grade";

describe("grade", () => {
  it("leaves colours alone when neutral", () => {
    for (const c of [
      [0, 0, 0],
      [0.5, 0.25, 0.75],
      [1, 1, 1],
    ] as [number, number, number][]) {
      const out = gradeColor(c, NEUTRAL_GRADE);
      out.forEach((v, i) => expect(v).toBeCloseTo(c[i], 6));
    }
  });

  it("bakes a neutral table that maps each cell to itself", () => {
    const size = 8;
    const lut = buildLut(NEUTRAL_GRADE, size);
    expect(lut.length).toBe(size ** 3 * 4);
    // Cell (r = 3, g = 5, b = 6), red fastest.
    const i = (6 * size * size + 5 * size + 3) * 4;
    expect([lut[i], lut[i + 1], lut[i + 2]]).toEqual(
      [3, 5, 6].map((v) => Math.round((v / 7) * 255)),
    );
  });

  it("makes palette tints as bright as white", () => {
    const [r, g, b] = tintFromHex("#C9A46A");
    expect(0.2126 * r + 0.7152 * g + 0.0722 * b).toBeCloseTo(1, 6);
    expect(r).toBeGreaterThan(b);
  });

  it("gives Episode 1 warm mid-tones and cool shadows while retaining dark detail", () => {
    const mid = gradeColor([0.5, 0.5, 0.5], EP1_GRADE);
    expect(mid[0]).toBeGreaterThan(mid[2] + 0.02);
    const shadow = gradeColor([0.12, 0.12, 0.12], EP1_GRADE);
    expect(shadow[2]).toBeGreaterThan(shadow[0]);
    const dark = gradeColor([0.015, 0.015, 0.015], EP1_GRADE);
    expect(dark.every((channel) => channel > 0)).toBe(true);
    expect(gradeColor([0, 0, 0], EP1_GRADE)).toEqual([0, 0, 0]);
  });

  it("desaturates", () => {
    const grey: GradeParams = { ...NEUTRAL_GRADE, saturation: -1 };
    const [r, g, b] = gradeColor([0.8, 0.2, 0.1], grey);
    expect(r).toBeCloseTo(g, 6);
    expect(g).toBeCloseTo(b, 6);
  });
});

describe("EyeAdaptation", () => {
  const run = (eye: EyeAdaptation, seconds: number, target: number) => {
    for (let t = 0; t < seconds - 1e-9; t += 1 / 60) eye.update(1 / 60, target);
    return eye.exposure;
  };
  const progress = (from: number, to: number, now: number) =>
    (Math.log(now) - Math.log(from)) / (Math.log(to) - Math.log(from));

  it("adjusts to darkness 90% of the way in 2.5 s", () => {
    const eye = new EyeAdaptation(1.5);
    expect(progress(1.5, 6, run(eye, 1, 6))).toBeLessThan(0.7);
    expect(progress(1.5, 6, run(eye, 1.5, 6))).toBeCloseTo(0.9, 1);
  });

  it("recovers from darkness faster when the light comes back", () => {
    const eye = new EyeAdaptation(6);
    expect(progress(6, 1.5, run(eye, 0.8, 1.5))).toBeCloseTo(0.9, 1);
  });
});

describe("targetExposure", () => {
  it("wins back only a quarter of the lost light, and stays capped", () => {
    expect(targetExposure(1, 1.5, 4.5)).toBeCloseTo(1.5);
    // 16 times less light (4 stops): one stop more exposure.
    expect(targetExposure(1 / 16, 1.5, 4.5)).toBeCloseTo(3);
    expect(targetExposure(0, 1.5, 4.5)).toBe(4.5);
    expect(targetExposure(50, 1.5, 4.5)).toBeCloseTo(0.9);
  });
});

describe("lookValues", () => {
  const settings = { grain: true, aberration: true, brightness: 0 };
  const calm = { fear: 0, scare: 0, memory: false };

  it("keeps film effects subtle during ordinary play", () => {
    const v = lookValues(calm, settings);
    expect(v.vignetteWeight).toBeLessThan(1);
    expect(v.grain).toBeLessThan(2);
    expect(v.aberration).toBeLessThan(0.5);
  });

  it("deepens the vignette with fear and spikes aberration on a scare", () => {
    const v = lookValues({ fear: 1, scare: 1, memory: false }, settings);
    const base = lookValues(calm, settings);
    expect(v.vignetteWeight).toBeGreaterThan(base.vignetteWeight);
    expect(v.vignetteWeight).toBeLessThan(3);
    expect(v.aberration).toBeGreaterThan(base.aberration * 4);
    expect(v.aberration).toBeLessThan(4);
  });

  it("honours the settings toggles", () => {
    const v = lookValues(
      { fear: 1, scare: 1, memory: true },
      { ...settings, grain: false, aberration: false },
    );
    expect(v.grain).toBe(0);
    expect(v.aberration).toBe(0);
  });

  it("lets a scare fade within a second", () => {
    let s = 1;
    for (let i = 0; i < 60; i++) s = decayScare(s, 1 / 60);
    expect(s).toBeLessThan(0.02);
  });
});
