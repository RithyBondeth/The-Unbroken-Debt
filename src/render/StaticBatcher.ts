import { Mesh } from "@babylonjs/core/Meshes/mesh";

export interface BatchOptions {
  /** Size of the grid cells (m). Smaller cells cull better; larger cells mean fewer draw calls. */
  cellSize: number;
  /** A different cell size for some meshes (scattered plants want larger cells). */
  cellSizeFor?: (mesh: Mesh) => number | undefined;
  /** Meshes to keep apart (for example, ones that must not cast shadows). Merged only with each other. */
  group?: (mesh: Mesh) => string;
}

/**
 * Merges static meshes that share a material and a grid cell into one mesh.
 * This is the "merge by material where possible" rule (TDD section 11): far
 * fewer draw calls, while cells stay small enough for camera and shadow-face
 * culling to skip what is out of view or out of a light's range.
 * Meshes with physics bodies are left alone. Returns the resulting meshes; each
 * has `metadata.batchGroup` set to its group name.
 */
export function mergeStaticMeshes(meshes: readonly Mesh[], options: BatchOptions): Mesh[] {
  const groups = new Map<string, Mesh[]>();
  const groupNames = new Map<string, string>();
  for (const mesh of meshes) {
    if (!mesh.material || mesh.physicsBody || mesh.getTotalVertices() === 0) continue;
    mesh.computeWorldMatrix(true);
    const c = mesh.getBoundingInfo().boundingSphere.centerWorld;
    const size = options.cellSizeFor?.(mesh) ?? options.cellSize;
    const cell = [c.x, c.y, c.z].map((v) => Math.floor(v / size)).join(",");
    const key = `${mesh.material.uniqueId}|${cell}|${options.group?.(mesh) ?? ""}`;
    groupNames.set(key, options.group?.(mesh) ?? "");
    let list = groups.get(key);
    if (!list) groups.set(key, (list = []));
    list.push(mesh);
  }

  const merged: Mesh[] = [];
  for (const [key, list] of groups) {
    const batchGroup = groupNames.get(key) ?? "";
    if (list.length < 2) {
      list[0].metadata = { ...(list[0].metadata as object | null), batchGroup };
      merged.push(list[0]);
      continue;
    }
    const receiveShadows = list.some((m) => m.receiveShadows);
    const result = Mesh.MergeMeshes(list, true, true);
    if (!result) continue;
    result.name = `batch_${key}`;
    result.metadata = { batchGroup };
    result.receiveShadows = receiveShadows;
    result.isPickable = false;
    result.freezeWorldMatrix();
    merged.push(result);
  }
  return merged;
}
