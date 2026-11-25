import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import type { Material } from "@babylonjs/core/Materials/material";
import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { VILLAGE_ROAD } from "../data/forestBorder";

/** The shops' own lights and glass, kept as authored (bulbs, tubes, the TV, the windows). */
const AUTHORED =
  /^M_vroad_shop_(bulb|fluoro|crt|mirror|window_glow|noodle_glow|shrine_glow|foliage)$/;

/**
 * The village road's shops and poster boards (tools/areas/village_road.py, the user, Nov 25,
 * 2026: "just like driving scene") are built by the driving scene's own roadside builder, so
 * their materials get the dressing TaxiVisuals gives that roadside: the real 1990s Khmer
 * posters a rain-soaked patina with a damp sheen, the Poly Haven props darkened from their
 * daylight albedo and wetted, the shops' timber, tin and plaster a little damper. Returns how
 * many materials it dressed.
 */
export function dressVillageRoad(materials: readonly Material[]): number {
  let dressed = 0;
  for (const material of materials) {
    if (!(material instanceof PBRMaterial) || !material.name.startsWith("M_vroad_")) continue;
    const name = material.name;
    if (name === "M_vroad_khmer_posters") {
      material.albedoColor.set(0.58, 0.56, 0.52);
      material.metallic = 0;
      material.roughness = 0.6;
      material.clearCoat.isEnabled = true;
      material.clearCoat.intensity = 0.16;
      material.clearCoat.roughness = 0.3;
    } else if (AUTHORED.test(name)) {
      if (name === "M_vroad_shop_mirror") material.metallic = 0.96;
    } else if (name.startsWith("M_vroad_shop_ph_")) {
      material.albedoColor.scaleInPlace(0.66);
      material.roughness = Math.max(0.42, (material.roughness ?? 0.8) * 0.9);
      material.specularIntensity = Math.min(0.45, material.specularIntensity ?? 0.35);
    } else if (name.startsWith("M_vroad_shop_")) {
      material.albedoColor.scaleInPlace(0.94);
      material.roughness = Math.max(0.32, (material.roughness ?? 0.8) * 0.94);
    } else continue;
    dressed++;
  }
  return dressed;
}

/** Past this distance (m) the road's shops and its jungle are not drawn. */
export const ROAD_DRAW_DISTANCE = 40;
/**
 * Past this distance (m) the shops' goods are not drawn: thousands of bottles, tins and tools
 * a few pixels across cost the GPU far more than they show. From the gate the noodle shop
 * opposite (about 16 m) keeps its goods; the others fill in as Sora walks up the road.
 */
export const GOODS_DRAW_DISTANCE = 18;
/** The goods' materials: the dressing kit's and the real props placed in the rooms. */
const GOODS = /^M_vroad_(goods_|shop_ph_)/;
/**
 * Batches lying wholly south of this (Babylon z) belong to the village road outside the gate:
 * the road's north ditch is at about VILLAGE_ROAD.z - 4.6.
 */
export const ROAD_NORTH_EDGE = VILLAGE_ROAD.z - 6.3;

/**
 * The road's shops are furnished down to the last comb and bottle (shop_interiors.py), some
 * 0.4 M triangles with the jungle round them: drawn only when Sora is near the gate, where the
 * farm's own buildings are behind her, and the goods only nearer still. Returns how many
 * meshes it limited.
 */
export function cullVillageRoad(meshes: readonly AbstractMesh[]): number {
  let limited = 0;
  for (const mesh of meshes) {
    if (
      !(mesh instanceof Mesh) ||
      mesh.hasLODLevels ||
      mesh.skeleton ||
      mesh.getTotalVertices() === 0
    )
      continue;
    mesh.computeWorldMatrix(true);
    if (mesh.getBoundingInfo().boundingBox.minimumWorld.z < ROAD_NORTH_EDGE) continue;
    mesh.addLODLevel(
      GOODS.test(mesh.material?.name ?? "") ? GOODS_DRAW_DISTANCE : ROAD_DRAW_DISTANCE,
      null,
    );
    limited++;
  }
  return limited;
}
