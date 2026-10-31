import type { AssetContainer } from "@babylonjs/core/assetContainer";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { VertexBuffer } from "@babylonjs/core/Buffers/buffer";
import type { Node } from "@babylonjs/core/node";
import { foliageKind } from "./FoliageWind";

/** What the wind makes a tree sound like (WindAudio): leaves, bamboo, fronds or a bare trunk. */
export type TreeVoice = "leafy" | "bamboo" | "palm" | "dead";

/** A tree standing in the wind, for the sounds it makes. */
export interface PlantSite {
  x: number;
  /** Ground at its foot. */
  y: number;
  z: number;
  height: number;
  voice: TreeVoice;
  /** The trunk at chest height, where thread can be wound round it. */
  trunk?: TrunkProfile;
}

/** A trunk's cross-section between `from` and `to` (world y): its centre and radius by angle. */
export interface TrunkProfile {
  x: number;
  z: number;
  from: number;
  to: number;
  /** Bark's reach from the centre in TRUNK_BINS equal sectors, starting along +x. */
  radii: number[];
}

export const TRUNK_BINS = 16;

/** Bark radius at angle `a` (radians), interpolated round the profile. */
export function trunkRadius(trunk: TrunkProfile, a: number): number {
  const f = ((((a / (Math.PI * 2)) % 1) + 1) % 1) * TRUNK_BINS;
  const i = Math.floor(f),
    t = f - i;
  return trunk.radii[i % TRUNK_BINS] * (1 - t) + trunk.radii[(i + 1) % TRUNK_BINS] * t;
}

/** Measures a trunk from its bark vertices (world x, y, z triples) in a band of heights. */
export function measureTrunk(
  points: ArrayLike<number>,
  from: number,
  to: number,
): TrunkProfile | null {
  let sx = 0,
    sz = 0,
    n = 0;
  for (let i = 0; i < points.length; i += 3)
    if (points[i + 1] >= from && points[i + 1] <= to) {
      sx += points[i];
      sz += points[i + 2];
      n++;
    }
  if (n < 6) return null;
  const x = sx / n,
    z = sz / n;
  const radii = new Array<number>(TRUNK_BINS).fill(0);
  for (let i = 0; i < points.length; i += 3) {
    if (points[i + 1] < from || points[i + 1] > to) continue;
    const dx = points[i] - x,
      dz = points[i + 2] - z;
    const turn = (((Math.atan2(dz, dx) / (Math.PI * 2)) % 1) + 1) % 1;
    const bin = Math.floor(turn * TRUNK_BINS) % TRUNK_BINS;
    radii[bin] = Math.max(radii[bin], Math.hypot(dx, dz));
  }
  const known = radii.filter((r) => r > 0);
  const mean = known.reduce((a, b) => a + b, 0) / known.length;
  // A trunk too thick for its band is a fork or a buttress, not something to wind thread round.
  if (mean > 0.9) return null;
  return { x, z, from, to, radii: radii.map((r) => (r > 0 ? r : mean)) };
}

/** The voice of a tree by its node name, or null for undergrowth too low to be heard. */
export function treeVoice(name: string): TreeVoice | null {
  if (/^bamboo/.test(name)) return "bamboo";
  if (/^(palm|coco|banana)/.test(name)) return "palm";
  if (/^dead/.test(name)) return "dead";
  if (/^(tree|pachira|island_tree)/.test(name)) return "leafy";
  return null;
}

/** How readily a plant bends, by its node name (1 is a broadleaf crown's 0.85 scaled up). */
const FLEX: [RegExp, number][] = [
  [/^bamboo/, 1.15],
  [/^banana/, 1.1],
  [/^(palm|coco)/, 0.8],
  [/^dead/, 0.6],
  [/^tree_(10|11|317)\b/, 1.2],
  [/^(fern|shrub|grass|pachira)/, 1.4],
];

export function flexOf(name: string): number {
  for (const [pattern, flex] of FLEX) if (pattern.test(name)) return flex;
  return 0.85;
}

/** A plant's own sway phase (0–2π) from where it stands: neighbours never move in step. */
export function plantPhase(x: number, z: number): number {
  const s = Math.sin(x * 12.9898 + z * 78.233) * 43758.5453;
  return (s - Math.floor(s)) * Math.PI * 2;
}

/** The plant a mesh belongs to: its ancestor just below the file's root. */
function plantRoot(mesh: Node): Node {
  let node = mesh;
  while (node.parent && node.parent.name !== "__root__") node = node.parent;
  return node;
}

/**
 * Writes every plant's height above its foot (scaled by how readily it
 * bends) and its phase into uv6, before batching merges the plants into large
 * meshes: FoliageWind then bends a trunk and its crown as one, from the
 * ground up, wherever the batch has put them. Returns the trees, for their sound.
 */
export function bakePlantHeights(container: AssetContainer): PlantSite[] {
  const plants = new Map<Node, Mesh[]>();
  for (const mesh of container.meshes) {
    if (!(mesh instanceof Mesh) || !mesh.material || mesh.getTotalVertices() === 0) continue;
    if (!foliageKind(mesh.material.name)) continue;
    const root = plantRoot(mesh);
    let list = plants.get(root);
    if (!list) plants.set(root, (list = []));
    list.push(mesh);
  }
  const sites: PlantSite[] = [];
  for (const [root, meshes] of plants) {
    let foot = Infinity,
      top = -Infinity;
    for (const mesh of meshes) {
      mesh.computeWorldMatrix(true);
      const box = mesh.getBoundingInfo().boundingBox;
      foot = Math.min(foot, box.minimumWorld.y);
      top = Math.max(top, box.maximumWorld.y);
    }
    const flex = flexOf(root.name);
    const centre = meshes[0].getBoundingInfo().boundingBox.centerWorld;
    const phase = plantPhase(centre.x, centre.z);
    const voice = treeVoice(root.name);
    const bark: number[] = [];
    for (const mesh of meshes) {
      // Copies placed from one source share its vertex buffers: give each its own.
      if (mesh.geometry && mesh.geometry.meshes.length > 1) mesh.makeGeometryUnique();
      const positions = mesh.getVerticesData(VertexBuffer.PositionKind);
      if (!positions) continue;
      const m = mesh.getWorldMatrix().m;
      const barky = voice !== null && foliageKind(mesh.material!.name) === "bark";
      const uv6 = new Float32Array((positions.length / 3) * 2);
      for (let i = 0, j = 0; i < positions.length; i += 3, j += 2) {
        const y = positions[i] * m[1] + positions[i + 1] * m[5] + positions[i + 2] * m[9] + m[13];
        uv6[j] = Math.max(0, y - foot) * flex;
        uv6[j + 1] = phase;
        if (barky && y > foot + 0.7 && y < foot + 1.9) {
          const [px, py, pz] = [positions[i], positions[i + 1], positions[i + 2]];
          bark.push(
            px * m[0] + py * m[4] + pz * m[8] + m[12],
            y,
            px * m[2] + py * m[6] + pz * m[10] + m[14],
          );
        }
      }
      mesh.setVerticesData(VertexBuffer.UV6Kind, uv6, false, 2);
    }
    if (voice)
      sites.push({
        x: centre.x,
        y: foot,
        z: centre.z,
        height: top - foot,
        voice,
        trunk: measureTrunk(bark, foot + 0.8, foot + 1.8) ?? undefined,
      });
  }
  return sites;
}
