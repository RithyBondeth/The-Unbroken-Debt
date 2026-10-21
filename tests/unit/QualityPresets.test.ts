import { describe, expect, it } from "vitest";
import {
  getPreset,
  isQualityName,
  QUALITY_ORDER,
  QUALITY_PRESETS,
} from "../../src/render/QualityPresets";

describe("quality presets", () => {
  it("match the TDD minimum-spec targets for Medium", () => {
    const medium = QUALITY_PRESETS.medium;
    expect(medium.lampShadowMapSize).toBe(2048);
    expect(medium.clusteredLights).toBeGreaterThanOrEqual(32);
    expect(medium.ssaoRatio).toBe(0.5);
    expect(medium.taa).toBe(true);
  });

  it("never lower quality from Low to Ultra", () => {
    const presets = QUALITY_ORDER.map((name) => QUALITY_PRESETS[name]);
    const keys = [
      "maxRenderHeight",
      "textureSize",
      "lampShadowMapSize",
      "shadowedFlames",
      "clusteredLights",
      "ssaoSamples",
      "fogSteps",
    ] as const;
    for (let i = 1; i < presets.length; i++) {
      for (const key of keys) expect(presets[i][key]).toBeGreaterThanOrEqual(presets[i - 1][key]);
    }
  });

  it("keeps Low cheap but still gives the lamp a shadow (it is gameplay)", () => {
    const low = QUALITY_PRESETS.low;
    expect(low).toMatchObject({ ssao: false, volumetricFog: false, taa: false, shadowedFlames: 0 });
    expect(low.lampShadowMapSize).toBeGreaterThan(0);
  });

  it("applies overrides without changing the table", () => {
    const tested = getPreset("medium", { shadowedFlames: 4 });
    expect(tested.shadowedFlames).toBe(4);
    expect(QUALITY_PRESETS.medium.shadowedFlames).toBe(2);
  });

  it("recognises preset names", () => {
    expect(isQualityName("ultra")).toBe(true);
    expect(isQualityName("potato")).toBe(false);
    expect(isQualityName(null)).toBe(false);
  });
});
