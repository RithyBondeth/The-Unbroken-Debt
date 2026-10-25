import { describe, expect, it } from "vitest";
import { ShaderStore } from "@babylonjs/core/Engines/shaderStore";
import { installSoftLampFalloff, softFalloff } from "../../src/render/softLampFalloff";

const RANGE = 9;
/** Calibrated as VillageLights does: equal to plain 1/d² at 4 m. */
const gain = 1 / (16 * softFalloff(4, RANGE));
const soft = (d: number) => gain * softFalloff(d, RANGE);

describe("soft lamp falloff", () => {
  it("lights everything from 3 m out as the physical lamp did", () => {
    for (const d of [3, 4, 5, 6]) expect(soft(d) * d * d).toBeGreaterThan(0.9);
    for (const d of [3, 4, 5, 6]) expect(soft(d) * d * d).toBeLessThan(1.1);
  });

  it("levels off at arm's length instead of climbing without limit", () => {
    expect(soft(1)).toBeLessThan(0.6); // physical: 1
    expect(soft(0.5)).toBeLessThan(0.25 * 4); // physical: 4
    expect(soft(0)).toBeLessThan(1); // physical: infinite
    // Still brighter the closer you go: nothing turns dark in the hand.
    expect(soft(0.5)).toBeGreaterThan(soft(1));
    expect(soft(1)).toBeGreaterThan(soft(2));
  });

  it("ends at the light's range", () => {
    expect(softFalloff(RANGE, RANGE)).toBe(0);
    expect(softFalloff(RANGE + 1, RANGE)).toBe(0);
  });

  it("patches the standard falloff in both shader languages, and nothing else", async () => {
    await import("@babylonjs/core/Shaders/ShadersInclude/pbrDirectLightingFalloffFunctions");
    await import("@babylonjs/core/ShadersWGSL/ShadersInclude/pbrDirectLightingFalloffFunctions");
    const name = "pbrDirectLightingFalloffFunctions";
    const before = ShaderStore.IncludesShadersStoreWGSL[name];
    installSoftLampFalloff(1.1);
    const wgsl = ShaderStore.IncludesShadersStoreWGSL[name];
    const glsl = ShaderStore.IncludesShadersStore[name];
    expect(wgsl).toContain("/(d2+1.2100)");
    expect(glsl).toContain("/(d2+1.2100)");
    // The physical falloff every other light uses is untouched.
    const physical = /fn computeDistanceLightFalloff_Physical[^}]*\}/;
    expect(wgsl.match(physical)?.[0]).toBe(before.match(physical)?.[0]);
  });
});
