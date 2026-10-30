import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import type { Material } from "@babylonjs/core/Materials/material";
import type { BaseTexture } from "@babylonjs/core/Materials/Textures/baseTexture";
import type { Scene } from "@babylonjs/core/scene";
import type { QualityName } from "./QualityPresets";

const rainDressed = new WeakSet<PBRMaterial>();

/** Keep authored surface differences when applying the episode's rain treatment. */
export function applyRainWetness(material: PBRMaterial): void {
  if (!material.name.startsWith("M_wet_") || rainDressed.has(material)) return;
  rainDressed.add(material);
  material.albedoColor.scaleInPlace(0.94);
  material.roughness = Math.max(0.45, (material.roughness ?? 1) * 0.94);
}

/** Preserve grazing-angle texture detail without increasing texture memory or geometry. */
export function keepSurfaceDetail(scene: Scene, quality: QualityName): void {
  const filtering = quality === "low" ? 4 : quality === "medium" ? 8 : 16;
  const textures = new Set<BaseTexture>(scene.textures);
  const materials = new Set<Material>(scene.materials);
  scene.onNewTextureAddedObservable.add((texture) => textures.add(texture));
  scene.onNewMaterialAddedObservable.add((material) => materials.add(material));
  // Constructors publish these events before all their properties are assigned.
  // Flush once before drawing; never rescan the forest or dirty shaders every frame.
  scene.onBeforeRenderObservable.add(() => {
    for (const texture of textures) texture.anisotropicFilteringLevel = filtering;
    textures.clear();
    for (const material of materials) {
      if (!(material instanceof PBRMaterial)) continue;
      material.enableSpecularAntiAliasing = true;
      // Thin foliage needs its back-face normal turned towards the light too.
      // Otherwise half of a banana/fern canopy becomes black under the lantern.
      if (!material.backFaceCulling) material.twoSidedLighting = true;
    }
    materials.clear();
  });
}
