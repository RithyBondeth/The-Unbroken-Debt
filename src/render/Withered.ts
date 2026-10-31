import { MaterialPluginBase } from "@babylonjs/core/Materials/materialPluginBase";
import type { Material } from "@babylonjs/core/Materials/material";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import type { UniformBuffer } from "@babylonjs/core/Materials/uniformBuffer";
import { ShaderLanguage } from "@babylonjs/core/Materials/shaderLanguage";
import { foliageKind, type FoliageKind } from "./FoliageWind";

/**
 * How the cursed forest drains each kind of plant (Episode 1's haunted
 * forest, 31 October 2026): [tint over the plant's own luminance, how far].
 * Leaves turn dead brown, grass to straw, bark to ash grey; nothing green
 * survives except what the lamp warms.
 */
export const WITHER: Partial<Record<FoliageKind, readonly [number, number, number, number]>> = {
  leaf: [1.3, 1.02, 0.72, 0.92],
  frond: [1.3, 1.0, 0.7, 0.92],
  grass: [1.3, 1.1, 0.8, 0.9],
  bark: [1.0, 0.98, 0.97, 0.65],
};

/**
 * Mixes a material's albedo towards its own luminance times a tint, after the
 * albedo texture is read: dead leaves keep their veins and shading but lose
 * their colour. One uniform per material; no texture is repainted.
 */
export class Withered extends MaterialPluginBase {
  constructor(
    material: Material,
    readonly tint: readonly [number, number, number, number] = WITHER.leaf!,
  ) {
    super(material, "Withered", 190, {}, true, true);
    this.doNotSerialize = true;
  }

  override isCompatible(): boolean {
    return true;
  }

  override getUniforms() {
    return {
      ubo: [{ name: "witherTint", size: 4, type: "vec4" }],
      fragment: "uniform vec4 witherTint;",
    };
  }

  override bindForSubMesh(buffer: UniformBuffer): void {
    const t = this.tint;
    buffer.updateFloat4("witherTint", t[0], t[1], t[2], t[3]);
  }

  override getCustomCode(type: string, language: ShaderLanguage) {
    if (type !== "fragment") return null;
    const code =
      language === ShaderLanguage.WGSL
        ? "surfaceAlbedo = mix(surfaceAlbedo, vec3f(dot(surfaceAlbedo, vec3f(0.299, 0.587, 0.114))) * uniforms.witherTint.rgb, uniforms.witherTint.a);"
        : "surfaceAlbedo = mix(surfaceAlbedo, vec3(dot(surfaceAlbedo, vec3(0.299, 0.587, 0.114))) * witherTint.rgb, witherTint.a);";
    return { CUSTOM_FRAGMENT_UPDATE_ALPHA: code };
  }
}

/**
 * Withers every plant material once. The village's own forest surfaces
 * (M_forest_*) are already painted dead; pass `repainted: false` where they
 * are not (the taxi's roadside).
 */
export function witherPlants(materials: readonly Material[], repainted = true): Withered[] {
  const plugins: Withered[] = [];
  for (const material of materials) {
    if (!(material instanceof PBRMaterial) || material.pluginManager?.getPlugin("Withered"))
      continue;
    if (repainted && material.name.startsWith("M_forest_")) continue;
    const kind = foliageKind(material.name);
    const tint = kind && WITHER[kind];
    if (tint) plugins.push(new Withered(material, tint));
  }
  return plugins;
}
