import type { Material } from "@babylonjs/core/Materials/material";
import { MaterialPluginBase } from "@babylonjs/core/Materials/materialPluginBase";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { ShaderLanguage } from "@babylonjs/core/Materials/shaderLanguage";

/**
 * A space the sky cannot see into (Babylon world space, metres): a room under its roof,
 * the ground under a house on stilts. Inside it the sky's and the moon's light (and the
 * lightning's) fall to `inside` of their strength; outside it they come back over `soft`
 * metres. Walls are boxed to their inner faces, so an outer face stays in the sky.
 */
export interface ShelterBox {
  minX: number;
  minY: number;
  minZ: number;
  maxX: number;
  maxY: number;
  maxZ: number;
  inside: number;
  /** Over how far (m) the sky returns outside the box, along x, y and z. */
  soft: readonly [number, number, number];
}

/** The sky left at `p` (0-1), as the shader works it out: the most sheltering box wins. */
export function shelterAt(boxes: readonly ShelterBox[], x: number, y: number, z: number): number {
  let s = 1;
  for (const b of boxes) {
    const dx = Math.max(b.minX - x, x - b.maxX, 0) / b.soft[0];
    const dy = Math.max(b.minY - y, y - b.maxY, 0) / b.soft[1];
    const dz = Math.max(b.minZ - z, z - b.maxZ, 0) / b.soft[2];
    const t = Math.min(1, Math.hypot(dx, dy, dz));
    s = Math.min(s, b.inside + (1 - b.inside) * t * t * (3 - 2 * t));
  }
  return s;
}

const f = (v: number) => {
  const s = v.toFixed(3);
  return s.includes(".") ? s : `${s}.0`;
};

function definitions(boxes: readonly ShelterBox[], wgsl: boolean): string {
  const v3 = (x: number, y: number, z: number) =>
    wgsl ? `vec3f(${f(x)}, ${f(y)}, ${f(z)})` : `vec3(${f(x)}, ${f(y)}, ${f(z)})`;
  const calls = boxes
    .map(
      (b) =>
        `s = min(s, skyShelterBox(p, ${v3(b.minX, b.minY, b.minZ)}, ${v3(b.maxX, b.maxY, b.maxZ)}, ${f(b.inside)}, ${v3(...(b.soft.map((v) => Math.max(0.001, v)) as [number, number, number]))}));`,
    )
    .join("\n");
  return wgsl
    ? `
fn skyShelterBox(p: vec3f, lo: vec3f, hi: vec3f, inside: f32, soft: vec3f) -> f32 {
  let d = length(max(max(lo - p, p - hi), vec3f(0.0)) / soft);
  return mix(inside, 1.0, smoothstep(0.0, 1.0, d));
}
fn skyShelterAt(p: vec3f) -> f32 {
  var s: f32 = 1.0;
  ${calls}
  return s;
}
`
    : `
float skyShelterBox(vec3 p, vec3 lo, vec3 hi, float inside, vec3 soft) {
  float d = length(max(max(lo - p, p - hi), vec3(0.0)) / soft);
  return mix(inside, 1.0, smoothstep(0.0, 1.0, d));
}
float skyShelterAt(vec3 p) {
  float s = 1.0;
  ${calls}
  return s;
}
`;
}

/**
 * Babylon's hemispheric and directional lights reach every surface, under a roof or
 * not: the sky lit the funeral under the house and every room's walls a cold blue the
 * approved previews never had (Nov 22, 2026). This scales those lights (the sky, the
 * moon, the lightning) by the shelter at each pixel: in PBR's light loop, each light's
 * colour (the CUSTOM_LIGHT{X}_COLOR hook) and the sky's ground colour.
 */
class SkyShelter extends MaterialPluginBase {
  constructor(
    material: PBRMaterial,
    private readonly glsl: string,
    private readonly wgsl: string,
  ) {
    super(material, "SkyShelter", 160, {});
    this.doNotSerialize = true;
    this._enable(true);
  }

  override isCompatible(): boolean {
    return true;
  }

  override getClassName(): string {
    return "SkyShelter";
  }

  override getCustomCode(type: string, language: ShaderLanguage) {
    if (type !== "fragment") return null;
    const wgsl = language === ShaderLanguage.WGSL;
    return {
      CUSTOM_FRAGMENT_DEFINITIONS: wgsl ? this.wgsl : this.glsl,
      CUSTOM_FRAGMENT_BEFORE_LIGHTS: wgsl
        ? "var skyShelter: f32 = skyShelterAt(fragmentInputs.vPositionW);"
        : "float skyShelter = skyShelterAt(vPositionW);",
      "!#define CUSTOM_LIGHT(\\d+)_COLOR": wgsl
        ? "\n#if defined(DIRLIGHT$1) || defined(HEMILIGHT$1)\ndiffuse$1 = vec4f(diffuse$1.rgb * skyShelter, diffuse$1.a);\n#endif\n"
        : "\n#if defined(DIRLIGHT$1) || defined(HEMILIGHT$1)\ndiffuse$1.rgb *= skyShelter;\n#endif\n",
      "!info\\.diffuse=computeHemisphericDiffuseLighting\\(preInfo,diffuse(\\d+)\\.rgb,light(\\d+)\\.vLightGround\\);":
        "info.diffuse=computeHemisphericDiffuseLighting(preInfo,diffuse$1.rgb,light$2.vLightGround*skyShelter);",
    };
  }
}

/** Gives every PBR material in `materials` the shelter of `boxes` (once each). Returns how many. */
export function applySkyShelter(
  materials: readonly Material[],
  boxes: readonly ShelterBox[],
): number {
  if (!boxes.length) return 0;
  const glsl = definitions(boxes, false);
  const wgsl = definitions(boxes, true);
  let n = 0;
  for (const material of materials) {
    if (!(material instanceof PBRMaterial) || material.pluginManager?.getPlugin("SkyShelter"))
      continue;
    new SkyShelter(material, glsl, wgsl);
    n++;
  }
  return n;
}
