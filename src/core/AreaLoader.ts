import { LoadAssetContainerAsync } from "@babylonjs/core/Loading/sceneLoader";
import { InstancedMesh } from "@babylonjs/core/Meshes/instancedMesh";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
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
  realiseInstances(container);
  const level = buildLevel(scene, [...container.transformNodes, ...container.meshes]);
  for (const warning of level.warnings) console.warn(`[area ${id}] ${warning}`);
  batchStatics(container, options.keep ?? []);
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
function realiseInstances(container: AssetContainer): void {
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
 * Merges the area's static meshes by material in 3 m cells (S2: one draw call
 * per batch instead of one per object). The Phase 2 studio had 1,810 draw calls
 * from hundreds of small props and trim pieces.
 */
function batchStatics(container: AssetContainer, keep: readonly (string | RegExp)[]): void {
  const statics = container.meshes.filter(
    (m): m is Mesh =>
      m instanceof Mesh && m.isVisible && m.getTotalVertices() > 0 && !isDynamic(m, keep),
  );
  const batches = mergeStaticMeshes(statics, { cellSize: 3 });
  const merged = new Set(statics.filter((m) => m.isDisposed()));
  container.meshes = [
    ...container.meshes.filter((m) => !merged.has(m as Mesh)),
    ...batches.filter((b) => !container.meshes.includes(b)),
  ];
}
