import type { AssetContainer } from "@babylonjs/core/assetContainer";
import type { Node } from "@babylonjs/core/node";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { VertexBuffer } from "@babylonjs/core/Buffers/buffer";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { Point } from "./data/pagoda";

/** A slice through a trunk: its middle and how far its bark stands out, at height `y`. */
export interface TrunkSlice {
  y: number;
  x: number;
  z: number;
  r: number;
}

/** A tall tree a corpse can come down: where its trunk stands (runtime) and how tall it is. */
export interface ClimbTree {
  x: number;
  z: number;
  height: number;
  /** The trunk measured from its bark, bottom up; empty if it could not be. */
  trunk: TrunkSlice[];
}

/** Heights the trunk is measured at, and how thick each slice is. */
const SLICES = [1.2, 2.2, 3.2, 4.2, 5.2, 6.2, 7.2];
const SLICE = 0.35;

/**
 * Measures a tree's trunk from its bark vertices: in each slice, the middle of the bark
 * and the distance most of it stands from there (a whorl of roots or a branch stub aside).
 */
export function measureTrunk(points: Float32Array, count: number): TrunkSlice[] {
  const slices: TrunkSlice[] = [];
  for (const y of SLICES) {
    let sx = 0,
      sz = 0,
      n = 0;
    for (let i = 0; i < count; i++) {
      if (Math.abs(points[i * 3 + 1] - y) > SLICE) continue;
      sx += points[i * 3];
      sz += points[i * 3 + 2];
      n++;
    }
    if (n < 8) continue;
    const cx = sx / n,
      cz = sz / n;
    const radii: number[] = [];
    for (let i = 0; i < count; i++)
      if (Math.abs(points[i * 3 + 1] - y) <= SLICE)
        radii.push(Math.hypot(points[i * 3] - cx, points[i * 3 + 2] - cz));
    radii.sort((a, b) => a - b);
    // Most of the bark, not the odd branch stub: the 70th centile out.
    const r = radii[Math.floor(radii.length * 0.7)];
    if (r > 1.6) continue;
    // Higher up, branches pull the measure out: a trunk only narrows as it rises, and
    // its middle leans only a little from one slice to the next.
    const below = slices[slices.length - 1];
    if (!below) slices.push({ y, x: cx, z: cz, r });
    else {
      const lean = Math.hypot(cx - below.x, cz - below.z);
      const k = lean > 0.2 ? 0.2 / lean : 1;
      slices.push({
        y,
        x: below.x + (cx - below.x) * k,
        z: below.z + (cz - below.z) * k,
        r: Math.min(r, below.r),
      });
    }
  }
  return slices;
}

/** The trunk's slice at height `y`, between the measured ones. */
export function trunkAt(tree: ClimbTree, y: number): TrunkSlice {
  const t = tree.trunk;
  if (!t.length) return { y, x: tree.x, z: tree.z, r: 0.35 };
  if (y <= t[0].y) return { ...t[0], y };
  for (let k = 1; k < t.length; k++)
    if (y <= t[k].y) {
      const u = (y - t[k - 1].y) / (t[k].y - t[k - 1].y);
      const a = t[k - 1],
        b = t[k];
      return { y, x: a.x + (b.x - a.x) * u, z: a.z + (b.z - a.z) * u, r: a.r + (b.r - a.r) * u };
    }
  return { ...t[t.length - 1], y };
}

/** The area's broadleaf trees (not bamboo, banyan or dead snags); the belt's templates excluded. */
const CLIMB_NODE = /^tree_\d{1,3}(\.\d+)?$/;
/** Lower than this, nothing could hang head down far enough off the ground. */
const MIN_HEIGHT = 9;

/** Reads every tall tree out of the area before it is merged into batches. */
export function captureClimbTrees(container: AssetContainer): ClimbTree[] {
  const nodes: Node[] = [...container.transformNodes, ...container.meshes].filter((n) =>
    CLIMB_NODE.test(n.name),
  );
  const trees: ClimbTree[] = [];
  for (const node of nodes) {
    if (!(node instanceof TransformNode)) continue;
    node.computeWorldMatrix(true);
    const at = node.getAbsolutePosition();
    const { min, max } = node.getHierarchyBoundingVectors(true);
    const height = max.y - Math.max(min.y, at.y);
    if (height < MIN_HEIGHT) continue;
    // Every bark vertex in world space, near enough the trunk's foot to be trunk.
    const points: number[] = [];
    const p = new Vector3();
    for (const mesh of node.getChildMeshes(false)) {
      if (!(mesh instanceof Mesh) || !/bark/i.test(mesh.material?.name ?? "")) continue;
      const positions = mesh.getVerticesData(VertexBuffer.PositionKind);
      if (!positions) continue;
      const world = mesh.computeWorldMatrix(true);
      for (let i = 0; i < positions.length; i += 3) {
        Vector3.TransformCoordinatesFromFloatsToRef(
          positions[i],
          positions[i + 1],
          positions[i + 2],
          world,
          p,
        );
        if (Math.hypot(p.x - at.x, p.z - at.z) < 2.5 && p.y < 8) points.push(p.x, p.y, p.z);
      }
    }
    const trunk = measureTrunk(Float32Array.from(points), points.length / 3);
    trees.push({ x: trunk[0]?.x ?? at.x, z: trunk[0]?.z ?? at.z, height, trunk });
  }
  return trees;
}

/**
 * How far from a trunk's middle its bark is on the side towards `toward`, judged from the
 * navigation grid: the first open cell that way, less the corpse's own clearance.
 */
export function trunkRadius(
  tree: Point,
  toward: Point,
  walkable: (p: Point) => boolean,
  clearance = 0.35,
): number {
  const dx = toward.x - tree.x,
    dz = toward.z - tree.z;
  const d = Math.hypot(dx, dz) || 1;
  for (let r = 0; r < 3; r += 0.1)
    if (walkable({ x: tree.x + (dx / d) * r, z: tree.z + (dz / d) * r }))
      return Math.min(1.4, Math.max(0.25, r - clearance));
  return 0.3;
}
