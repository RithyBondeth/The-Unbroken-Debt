import { LoadAssetContainerAsync } from "@babylonjs/core/Loading/sceneLoader";
import { InstancedMesh } from "@babylonjs/core/Meshes/instancedMesh";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import type { Node } from "@babylonjs/core/node";
import { mergeStaticMeshes } from "../render/StaticBatcher";
import type { AssetContainer } from "@babylonjs/core/assetContainer";
import type { Scene } from "@babylonjs/core/scene";
import { registerBuiltInLoaders } from "@babylonjs/loaders/dynamic";
import { buildLevel, type Level } from "./LevelBuilder";

let loadersRegistered = false;

export interface Area {
  id: string;
  container: AssetContainer;
  level: Level;
  dispose(): void;
}

/**
 * Loads an area's optimised .glb (`public/assets/<episode>/<id>.glb`), adds it
 * to the scene and builds its colliders, spawns and interactables from the
 * Blender names (Technical Design Document, sections 3 and 7).
 */
export interface AreaOptions {
  /** Nodes a script finds or moves (e.g. "window_glass", /^letter_/), kept out of batching. */
  keep?: (string | RegExp)[];
  /** Batching cell size in metres (default 3): larger for open areas with scattered props. */
  cellSize?: number;
  /** A larger cell size for meshes whose material name matches (scattered plants). */
  coarse?: { pattern: RegExp; cellSize: number };
}

export async function loadArea(
  scene: Scene,
  episode: string,
  id: string,
  options: AreaOptions = {},
): Promise<Area> {
  if (!loadersRegistered) {
    registerBuiltInLoaders();
    loadersRegistered = true;
  }
  const url = `${import.meta.env.BASE_URL}assets/${episode}/${id}.glb`;
  const container = await LoadAssetContainerAsync(url, scene);
  container.addAllToScene();
  dropTransmission(scene, container);
  realiseInstances(container);
  const level = buildLevel(scene, [...container.transformNodes, ...container.meshes]);
  for (const warning of level.warnings) console.warn(`[area ${id}] ${warning}`);
  batchStatics(container, options.keep ?? [], options.cellSize ?? 3, options.coarse);
  return {
    id,
    container,
    level,
    dispose() {
      container.removeAllFromScene();
      container.dispose();
    },
  };
}

/**
 * Turns instanced meshes into ordinary meshes that share the original's
 * geometry. Identical objects arrive as instances (the asset pipeline merges
 * them, and Blender's linked duplicates do the same), and TAA's pre-pass
 * builds an invalid WebGPU pipeline for them (vertex slot 9 missing), which
 * renders the whole frame black (Phase 2 studio). Revisit with thin instances
 * if a crowded area needs instancing for speed.
 */
export function realiseInstances(container: AssetContainer): void {
  for (const instance of container.meshes.filter((m) => m instanceof InstancedMesh)) {
    const source = instance.sourceMesh;
    const mesh: Mesh = source.clone(instance.name, instance.parent, true);
    mesh.position.copyFrom(instance.position);
    if (instance.rotationQuaternion) mesh.rotationQuaternion = instance.rotationQuaternion.clone();
    else mesh.rotation.copyFrom(instance.rotation);
    mesh.scaling.copyFrom(instance.scaling);
    mesh.metadata = instance.metadata as unknown;
    mesh.isVisible = instance.isVisible;
    container.meshes.splice(container.meshes.indexOf(instance), 1, mesh);
    instance.dispose();
  }
}

/**
 * Some library models arrive with KHR_materials_transmission (Poly Haven's
 * Lantern_01, even on its brass). Babylon then re-renders every opaque mesh into
 * a texture each frame for the refraction: in the village 600 extra draws a
 * frame, 18 ms of CPU instead of 8. By lamplight, glass and brass look the same
 * without it, so refraction is turned off and the helper that rendered it goes.
 */
function dropTransmission(scene: Scene, container: AssetContainer): void {
  let found = false;
  for (const material of container.materials) {
    if (material instanceof PBRMaterial && material.subSurface.isRefractionEnabled) {
      material.subSurface.isRefractionEnabled = false;
      found = true;
    }
  }
  const internals = scene as unknown as { _transmissionHelper?: { dispose(): void } };
  if (found && internals._transmissionHelper) {
    internals._transmissionHelper.dispose();
    internals._transmissionHelper = undefined;
  }
}

/** Is this node, or one of its parents, something the game moves or uses? */
function isDynamic(node: Node, keep: readonly (string | RegExp)[]): boolean {
  for (let n: Node | null = node; n; n = n.parent) {
    const name = n.name;
    if (keep.some((k) => (typeof k === "string" ? k === name : k.test(name)))) return true;
    if (/^(interact|col|ladder|trigger|hide|spawn|marker)_/.test(name)) return true;
  }
  return false;
}

/**
 * Merges the area's static meshes by material in grid cells (S2: one draw call
 * per batch instead of one per object). The Phase 2 studio had 1,810 draw calls
 * from hundreds of small props and trim pieces; the village's scattered plants
 * and posts each sat alone in a 3 m cell (2,260 calls), so it uses 8 m cells.
 */
function batchStatics(
  container: AssetContainer,
  keep: readonly (string | RegExp)[],
  cellSize: number,
  coarse?: { pattern: RegExp; cellSize: number },
): void {
  const statics = container.meshes.filter(
    (m): m is Mesh =>
      m instanceof Mesh && m.isVisible && m.getTotalVertices() > 0 && !isDynamic(m, keep),
  );
  const batches = mergeStaticMeshes(statics, {
    cellSize,
    cellSizeFor: (mesh) =>
      coarse && coarse.pattern.test(mesh.material?.name ?? "") ? coarse.cellSize : undefined,
  });
  const merged = new Set(statics.filter((m) => m.isDisposed()));
  container.meshes = [
    ...container.meshes.filter((m) => !merged.has(m as Mesh)),
    ...batches.filter((b) => !container.meshes.includes(b)),
  ];
}
