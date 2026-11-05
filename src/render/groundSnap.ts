import type { AssetContainer } from "@babylonjs/core/assetContainer";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { VertexBuffer } from "@babylonjs/core/Buffers/buffer";
import type { Node } from "@babylonjs/core/node";

/**
 * Things that stand on the ground: plants, dead wood, mounds, rocks and the
 * poles of the old flags. The area scripts set them down at height 0, and the
 * terrain rises and dips under them (ruts, banks, flooded paddies), so some
 * hovered. Buildings, the wells' frames and anything hung are left alone.
 */
export const GROUNDED =
  /^(tree_\d|dead_\d|coco_\d|palm_\d|banana_\d|bamboo_\d|termite_\d|pachira|shrub_|fern_|island_tree|dead_tree_trunk|tree_stump|root_cluster|rock_moss|dry_branches|moss_01|grass_medium|old_flag_\d|rag_tree)/;

/** How far a thing sinks into the ground once it touches it (m): no light shows under a root. */
const SINK = 0.02;

/**
 * The smallest gap between a set of world points (x, y, z triples) and the
 * ground under each: positive if nothing touches, negative if something is
 * already below the surface.
 */
export function clearance(
  points: ArrayLike<number>,
  groundAt: (x: number, z: number) => number,
): number {
  let gap = Infinity;
  for (let i = 0; i < points.length; i += 3)
    gap = Math.min(gap, points[i + 1] - groundAt(points[i], points[i + 2]));
  return gap;
}

/** The ancestor just below the file's root: the object as the area script placed it. */
function placed(node: Node): Node {
  let n = node;
  while (n.parent && n.parent.name !== "__root__") n = n.parent;
  return n;
}

/**
 * Lowers every grounded object that floats until its lowest point is just
 * under the terrain. Points come from its lowest vertices and an even sample
 * of the rest, so a leaning trunk or a slope is judged where it actually
 * meets the ground. Returns the objects moved and by how much.
 */
export function snapToGround(
  container: AssetContainer,
  groundAt: (x: number, z: number) => number,
  tolerance = 0.03,
): { name: string; drop: number }[] {
  const roots = new Map<Node, Mesh[]>();
  for (const mesh of container.meshes) {
    if (!(mesh instanceof Mesh) || mesh.getTotalVertices() === 0) continue;
    const root = placed(mesh);
    if (!GROUNDED.test(root.name)) continue;
    let list = roots.get(root);
    if (!list) roots.set(root, (list = []));
    list.push(mesh);
  }
  const moved: { name: string; drop: number }[] = [];
  for (const [root, meshes] of roots) {
    if (!(root instanceof TransformNode)) continue;
    const points: number[] = [];
    for (const mesh of meshes) {
      const positions = mesh.getVerticesData(VertexBuffer.PositionKind);
      if (!positions) continue;
      const m = mesh.computeWorldMatrix(true).m;
      const n = positions.length / 3;
      const world = (i: number) => {
        const [x, y, z] = [positions[i * 3], positions[i * 3 + 1], positions[i * 3 + 2]];
        return [
          x * m[0] + y * m[4] + z * m[8] + m[12],
          x * m[1] + y * m[5] + z * m[9] + m[13],
          x * m[2] + y * m[6] + z * m[10] + m[14],
        ];
      };
      const all = Array.from({ length: n }, (_, i) => world(i));
      all.sort((a, b) => a[1] - b[1]);
      const step = Math.max(1, Math.floor(n / 200));
      for (let i = 0; i < n; i += i < 60 ? 1 : step) points.push(...all[i]);
    }
    const gap = clearance(points, groundAt);
    if (!(gap > tolerance) || gap > 2) continue;
    const drop = gap + SINK;
    // __root__ only mirrors z, so a drop in its space is a drop in the world.
    root.position.y -= drop;
    root.computeWorldMatrix(true);
    for (const mesh of meshes) mesh.computeWorldMatrix(true);
    moved.push({ name: root.name, drop });
  }
  return moved;
}
