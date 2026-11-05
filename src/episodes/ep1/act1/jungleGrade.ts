import type { Material } from "@babylonjs/core/Materials/material";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { foliageKind, type FoliageKind } from "../../../render/FoliageWind";

/**
 * The old-growth night palette (tools/areas/forest_detail.py) for plants that
 * were not repainted with it: library shrubs, ferns and saplings, the
 * bananas and palms by the houses, the taxi's roadside. Cold, deep, barely
 * saturated greens; bark darker and greyer with the wet.
 */
export const JUNGLE_TINT: Partial<Record<FoliageKind, readonly [number, number, number]>> = {
  leaf: [0.46, 0.6, 0.58],
  frond: [0.46, 0.6, 0.6],
  grass: [0.6, 0.72, 0.68],
  bark: [0.78, 0.8, 0.83],
};

const graded = new WeakSet<Material>();

/**
 * Tints each plant material once. The village's own forest surfaces (M_forest_*)
 * already carry the palette; pass `repainted: false` where they do not (the taxi).
 */
export function gradeJungle(materials: readonly Material[], repainted = true): number {
  let count = 0;
  for (const material of materials) {
    if (!(material instanceof PBRMaterial) || graded.has(material)) continue;
    if (repainted && material.name.startsWith("M_forest_")) continue;
    const kind = foliageKind(material.name);
    const tint = kind && JUNGLE_TINT[kind];
    if (!tint) continue;
    material.albedoColor.set(
      material.albedoColor.r * tint[0],
      material.albedoColor.g * tint[1],
      material.albedoColor.b * tint[2],
    );
    graded.add(material);
    count++;
  }
  return count;
}
