import { MaterialPluginBase } from "@babylonjs/core/Materials/materialPluginBase";
import type { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { ShaderLanguage } from "@babylonjs/core/Materials/shaderLanguage";
import type { UniformBuffer } from "@babylonjs/core/Materials/uniformBuffer";

/** Ripple rings a material can carry at once (the newest replace the oldest). */
export const MAX_RIPPLES = 8;

/** One expanding ring: where it started, when (seconds on `WaterRipples.seconds`), how hard. */
export interface Ripple {
  x: number;
  z: number;
  start: number;
  strength: number;
}

/**
 * Rain and touch on still water, in the normals only (no geometry): every cell of a
 * jittered grid takes a raindrop at its own rhythm and rings out from it, and up to
 * MAX_RIPPLES rings run out from where something broke the surface (Sora's legs as she
 * wades, a step, something falling in), a train of waves that widens and fades.
 * Runs after LakeWaves (priority 180), so the mirror's ripple distortion sees it too.
 */
export class WaterRipples extends MaterialPluginBase {
  seconds = 0;
  /** 0 calm, 1 a monsoon downpour. */
  rain = 0.6;
  private readonly ripples: Ripple[] = [];
  private next = 0;

  constructor(material: PBRMaterial) {
    super(material, "WaterRipples", 181, {}, true, true);
    this.doNotSerialize = true;
  }

  /** Starts a ring at (x, z) now. */
  add(x: number, z: number, strength: number): void {
    const ripple = { x, z, start: this.seconds, strength };
    if (this.ripples.length < MAX_RIPPLES) this.ripples.push(ripple);
    else this.ripples[this.next++ % MAX_RIPPLES] = ripple;
  }

  override isCompatible(): boolean {
    return true;
  }

  override getClassName(): string {
    return "WaterRipples";
  }

  override getUniforms() {
    const ubo = [
      { name: "rippleTime", size: 1, type: "float" },
      { name: "rippleRain", size: 1, type: "float" },
      ...Array.from({ length: MAX_RIPPLES }, (_, i) => ({
        name: `ripple${i}`,
        size: 4,
        type: "vec4",
      })),
    ];
    const glsl = ["uniform float rippleTime;", "uniform float rippleRain;"]
      .concat(Array.from({ length: MAX_RIPPLES }, (_, i) => `uniform vec4 ripple${i};`))
      .join("\n");
    return { ubo, fragment: glsl };
  }

  override bindForSubMesh(buffer: UniformBuffer): void {
    buffer.updateFloat("rippleTime", this.seconds);
    buffer.updateFloat("rippleRain", this.rain);
    for (let i = 0; i < MAX_RIPPLES; i++) {
      const r = this.ripples[i];
      if (r) buffer.updateFloat4(`ripple${i}`, r.x, r.z, r.start, r.strength);
      else buffer.updateFloat4(`ripple${i}`, 0, 0, -100, 0);
    }
  }

  override getCustomCode(type: string, language: ShaderLanguage): Record<string, string> | null {
    if (type !== "fragment") return null;
    const wgsl = language === ShaderLanguage.WGSL;
    const u = wgsl ? "uniforms." : "";
    const p = wgsl ? "fragmentInputs.vPositionW" : "vPositionW";
    const v2 = wgsl ? "vec2f" : "vec2";
    const v3 = wgsl ? "vec3f" : "vec3";
    const sources = Array.from(
      { length: MAX_RIPPLES },
      (_, i) => `rippleSlope += rippleRing(rippleP, ${u}ripple${i}, ${u}rippleTime);`,
    ).join("\n");
    if (wgsl)
      return {
        CUSTOM_FRAGMENT_DEFINITIONS: `
          fn rippleHash(c: vec2f) -> vec2f {
            return fract(sin(vec2f(dot(c, vec2f(127.1, 311.7)), dot(c, vec2f(269.5, 183.3)))) * 43758.5453);
          }
          // Raindrops: one per cell of a jittered grid, each ringing out at its own beat.
          fn rippleDrops(p: vec2f, t: f32, scale: f32) -> vec2f {
            let q = p * scale;
            let cell = floor(q);
            var slope = vec2f(0.0);
            for (var oy = -1; oy <= 1; oy++) {
              for (var ox = -1; ox <= 1; ox++) {
                let c = cell + vec2f(f32(ox), f32(oy));
                let h = rippleHash(c);
                let centre = c + vec2f(0.15) + 0.7 * h;
                let age = fract(t * (0.6 + 0.5 * h.x) + h.y);
                let dv = (q - centre) / scale;
                let d = length(dv);
                let r = age * 0.24;
                let w = (d - r) / 0.016;
                let ring = exp(-w * w) * (1.0 - age) * (1.0 - age);
                slope += dv / max(d, 0.0001) * cos((d - r) * 70.0) * ring;
              }
            }
            return slope;
          }
          // A ring from where something broke the surface: a widening, fading wave train.
          fn rippleRing(p: vec2f, s: vec4f, t: f32) -> vec2f {
            let age = t - s.z;
            if (s.w <= 0.0 || age < 0.0 || age > 4.5) { return vec2f(0.0); }
            let dv = p - s.xy;
            let d = length(dv);
            let r = age * 0.62;
            let width = 0.07 + age * 0.09;
            let w = (d - r) / width;
            let wave = sin((d - r) * 24.0) * s.w * exp(-age * 0.85) * exp(-w * w);
            return dv / max(d, 0.0001) * wave;
          }
        `,
        CUSTOM_FRAGMENT_BEFORE_LIGHTS: `
          let rippleP = ${p}.xz;
          var rippleSlope = rippleDrops(rippleP, ${u}rippleTime, 2.6) * 0.42 * ${u}rippleRain;
          rippleSlope += rippleDrops(rippleP + ${v2}(0.37, 0.71), ${u}rippleTime * 1.13, 1.7) * 0.3 * ${u}rippleRain;
          ${sources}
          normalW = normalize(normalW + ${v3}(rippleSlope.x, 0.0, rippleSlope.y));
        `,
      };
    return {
      CUSTOM_FRAGMENT_DEFINITIONS: `
        vec2 rippleHash(vec2 c) {
          return fract(sin(vec2(dot(c, vec2(127.1, 311.7)), dot(c, vec2(269.5, 183.3)))) * 43758.5453);
        }
        vec2 rippleDrops(vec2 p, float t, float scale) {
          vec2 q = p * scale, cell = floor(q), slope = vec2(0.0);
          for (int oy = -1; oy <= 1; oy++)
            for (int ox = -1; ox <= 1; ox++) {
              vec2 c = cell + vec2(float(ox), float(oy));
              vec2 h = rippleHash(c);
              vec2 centre = c + vec2(0.15) + 0.7 * h;
              float age = fract(t * (0.6 + 0.5 * h.x) + h.y);
              vec2 dv = (q - centre) / scale;
              float d = length(dv), r = age * 0.24, w = (d - r) / 0.016;
              float ring = exp(-w * w) * (1.0 - age) * (1.0 - age);
              slope += dv / max(d, 0.0001) * cos((d - r) * 70.0) * ring;
            }
          return slope;
        }
        vec2 rippleRing(vec2 p, vec4 s, float t) {
          float age = t - s.z;
          if (s.w <= 0.0 || age < 0.0 || age > 4.5) return vec2(0.0);
          vec2 dv = p - s.xy;
          float d = length(dv), r = age * 0.62, width = 0.07 + age * 0.09, w = (d - r) / width;
          float wave = sin((d - r) * 24.0) * s.w * exp(-age * 0.85) * exp(-w * w);
          return dv / max(d, 0.0001) * wave;
        }
      `,
      CUSTOM_FRAGMENT_BEFORE_LIGHTS: `
        vec2 rippleP = ${p}.xz;
        vec2 rippleSlope = rippleDrops(rippleP, rippleTime, 2.6) * 0.42 * rippleRain;
        rippleSlope += rippleDrops(rippleP + vec2(0.37, 0.71), rippleTime * 1.13, 1.7) * 0.3 * rippleRain;
        ${sources}
        normalW = normalize(normalW + vec3(rippleSlope.x, 0.0, rippleSlope.y));
      `,
    };
  }
}
