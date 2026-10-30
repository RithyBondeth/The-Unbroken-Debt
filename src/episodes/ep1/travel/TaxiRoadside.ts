import type { AssetContainer } from "@babylonjs/core/assetContainer";
import type { Scene } from "@babylonjs/core/scene";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { realiseInstances } from "../../../core/AreaLoader";
import { mergeStaticMeshes } from "../../../render/StaticBatcher";
import { bakePlantHeights } from "../../../render/plantHeights";

/** One continuous authored route. Plants never recycle through the camera's view. */
export function buildTaxiRoadside(roadside: AssetContainer, scene: Scene) {
  realiseInstances(roadside);
  roadside.addAllToScene();
  bakePlantHeights(roadside);
  const meshes = roadside.meshes.filter(
    (m): m is Mesh => m instanceof Mesh && m.getTotalVertices() > 0,
  );
  const landscape = mergeStaticMeshes(meshes, {
    cellSize: 18,
    group: (mesh) => (mesh.name.includes("far_tree_") ? "distant" : "near"),
  });
  const root = new TransformNode("taxi_continuous_route", scene);
  for (const mesh of landscape) {
    mesh.unfreezeWorldMatrix();
    mesh.parent = root;
    mesh.isPickable = false;
    mesh.receiveShadows = true;
  }
  return { root, landscape };
}
