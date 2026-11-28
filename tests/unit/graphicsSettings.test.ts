import { describe, expect, it } from "vitest";
import {
  DEFAULT_GRAPHICS,
  needsReload,
  parseGraphics,
  resolveGraphics,
  type GraphicsSettings,
} from "@/render/graphicsSettings";
import { QUALITY_PRESETS } from "@/render/qualityPresets";

const settings = (over: Partial<GraphicsSettings> = {}): GraphicsSettings => ({
  ...structuredClone(DEFAULT_GRAPHICS),
  ...over,
});

describe("parseGraphics", () => {
  it("falls back to the defaults for missing or broken data", () => {
    expect(parseGraphics(null)).toEqual(DEFAULT_GRAPHICS);
    expect(parseGraphics("nonsense")).toEqual(DEFAULT_GRAPHICS);
    expect(parseGraphics({ preset: "extreme", frameCap: "240", renderScale: "big" })).toEqual(
      DEFAULT_GRAPHICS,
    );
  });

  it("keeps valid choices and clamps the resolution", () => {
    const parsed = parseGraphics({
      preset: "high",
      renderScale: 0.2,
      frameCap: "30",
      dynamicResolution: false,
      effects: { ssao: false, taa: "yes" },
      showFps: true,
    });
    expect(parsed).toMatchObject({
      preset: "high",
      renderScale: 0.5,
      frameCap: "30",
      dynamicResolution: false,
      effects: { ssao: false },
      showFps: true,
    });
    expect(parsed.effects.taa).toBeUndefined();
  });
});

describe("resolveGraphics", () => {
  const laptop = { quality: "medium", formFactor: "desktop" } as const;
  const phone = { quality: "low", formFactor: "phone" } as const;

  it("uses the device's pick on Auto, as before on laptops", () => {
    const resolved = resolveGraphics(settings(), laptop);
    expect(resolved.preset).toEqual(QUALITY_PRESETS.medium);
    expect(resolved.targetFps).toBe(60);
  });

  it("gives phones a lower render height and 30 fps on Auto", () => {
    const resolved = resolveGraphics(settings(), phone);
    expect(resolved.preset.name).toBe("low");
    expect(resolved.preset.maxRenderHeight).toBe(720);
    expect(resolved.preset.minRenderScale).toBe(0.5);
    expect(resolved.targetFps).toBe(30);
  });

  it("lets the player's preset, effects and frame rate override the device", () => {
    const resolved = resolveGraphics(
      settings({ preset: "high", frameCap: "max", effects: { ssao: false } }),
      phone,
    );
    expect(resolved.preset.name).toBe("high");
    expect(resolved.preset.maxRenderHeight).toBe(QUALITY_PRESETS.high.maxRenderHeight);
    expect(resolved.preset.ssao).toBe(false);
    expect(resolved.preset.volumetricFog).toBe(true);
    expect(resolved.targetFps).toBe(0);
  });
});

describe("needsReload", () => {
  it("is only needed for the preset and the effects", () => {
    const before = settings();
    expect(needsReload(before, settings({ renderScale: 0.75, frameCap: "30" }))).toBe(false);
    expect(needsReload(before, settings({ preset: "low" }))).toBe(true);
    expect(needsReload(before, settings({ effects: { taa: false } }))).toBe(true);
  });
});
