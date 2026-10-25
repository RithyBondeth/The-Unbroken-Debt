import { ShaderStore } from "@babylonjs/core/Engines/shaderStore";
import { Light } from "@babylonjs/core/Lights/light";
import "@babylonjs/core/Shaders/ShadersInclude/pbrDirectLightingFalloffFunctions";
import "@babylonjs/core/ShadersWGSL/ShadersInclude/pbrDirectLightingFalloffFunctions";

/**
 * Radius (m) of the soft core of Sora's lamp. A hurricane lamp is a flame inside
 * a frosted glass globe that spreads its light, not a point: within about this
 * distance of it, surfaces stop gaining light as fast as 1/d² says.
 */
export const LAMP_SOFT_RADIUS = 1.1;

const INCLUDE = "pbrDirectLightingFalloffFunctions";

/**
 * Pure 1/d² makes anything at arm's length from the lamp ten times brighter
 * than a wall 3 m away, and the tone curve rolls it off to beige and white: the
 * hearth, Sok's desk, a mosquito net (scene pass, October 2026). The lamp is the
 * only light given Babylon's "standard" falloff, and that function becomes
 * 1/(d² + r²), windowed to zero at the light's range. From about 3 m out it follows
 * the physical falloff every other light keeps, so the darkness the lamp pushes
 * back is unchanged; close up it levels off instead of climbing without limit.
 * Call before any PBR material compiles.
 */
export function installSoftLampFalloff(radius = LAMP_SOFT_RADIUS): void {
  const r2 = (radius * radius).toFixed(4);
  const patch = (
    store: Record<string, string>,
    standard: RegExp,
    body: string,
    language: string,
  ): void => {
    const source = store[INCLUDE];
    if (!source || !standard.test(source))
      throw new Error(`[softLampFalloff] ${language} falloff include not found`);
    store[INCLUDE] = source.replace(standard, body);
  };
  // Window (1 - (d/range)^8)²: flat to about 7 m, so the lamp still ends at its range
  // without dimming its working distance.
  patch(
    ShaderStore.IncludesShadersStoreWGSL,
    /fn computeDistanceLightFalloff_Standard\(lightOffset: vec3f,range: f32\)->f32\s*\{[^}]*\}/,
    `fn computeDistanceLightFalloff_Standard(lightOffset: vec3f,range: f32)->f32
{let d2: f32=dot(lightOffset,lightOffset);let f: f32=d2/(range*range);let f2: f32=f*f;let w: f32=saturate(1.0-f2*f2);return w*w/(d2+${r2});}`,
    "WGSL",
  );
  patch(
    ShaderStore.IncludesShadersStore,
    /float computeDistanceLightFalloff_Standard\(vec3 lightOffset,float range\)\s*\{[^}]*\}/,
    `float computeDistanceLightFalloff_Standard(vec3 lightOffset,float range)
{float d2=dot(lightOffset,lightOffset);float f=d2/(range*range);float f2=f*f;float w=clamp(1.0-f2*f2,0.0,1.0);return w*w/(d2+${r2});}`,
    "GLSL",
  );
}

/** Gives a light the soft falloff (it must be the only one using FALLOFF_STANDARD). */
export function useSoftFalloff(light: Light): void {
  light.falloffType = Light.FALLOFF_STANDARD;
}

/** The soft falloff at distance d (m), for tuning and tests; matches the shader. */
export function softFalloff(d: number, range: number, radius = LAMP_SOFT_RADIUS): number {
  const f = ((d * d) / (range * range)) ** 2;
  const w = Math.max(0, Math.min(1, 1 - f * f));
  return (w * w) / (d * d + radius * radius);
}
