import { describe, expect, it } from "vitest";
import { getPreset, isQualityName, QUALITY_PRESETS } from "../../src/render/QualityPresets";

describe("quality presets", () => {
  it("match the TDD minimum-spec targets for Medium", () => {
    const medium = QUALITY_PRESETS.medium;
    expect(medium.lampShadowMapSize).toBe(2048);
    expect(medium.clusteredLights).toBeGreaterThanOrEqual(32);
    expect(medium.ssaoRatio).toBe(0.5);
    expect(medium.taa).toBe(true);
  });

  it("never lower quality from Medium to Ultra", () => {
    const [m, h, u] = [QUALITY_PRESETS.medium, QUALITY_PRESETS.high, QUALITY_PRESETS.ultra];
    for (const key of [
      "lampShadowMapSize",
      "shadowedFlames",
      "clusteredLights",
      "ssaoSamples",
      "fogSteps",
    ] as const) {
      expect(h[key]).toBeGreaterThanOrEqual(m[key]);
      expect(u[key]).toBeGreaterThanOrEqual(h[key]);
    }
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
