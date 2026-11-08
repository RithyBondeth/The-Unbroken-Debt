import type { AssetContainer } from "@babylonjs/core/assetContainer";
import type { Mesh } from "@babylonjs/core/Meshes/mesh";
import type { Node } from "@babylonjs/core/node";
import type { Scene } from "@babylonjs/core/scene";
import { seededRandom } from "@/audio/synth";
import { capturePlant, plantCopies, type PlantTemplate } from "@/render/plantCopies";
import { LOST_GARDEN } from "./data/pagoda";

/** Ground Sora can walk on (runtime X east, Z south): the compound, the sala's clearing, the zones. */
export const WALKABLE: { minX: number; maxX: number; minZ: number; maxZ: number }[] = [
  { minX: -30, maxX: 30, minZ: -42, maxZ: 40 },
  { minX: 28, maxX: 45, minZ: -1.2, maxZ: 21 },
  ...LOST_GARDEN,
];

/** Metres from (x, z) to the nearest walkable ground, 0 on it. */
export function toWalkable(x: number, z: number): number {
  let best = Infinity;
  for (const r of WALKABLE) {
    const dx = Math.max(r.minX - x, 0, x - r.maxX),
      dz = Math.max(r.minZ - z, 0, z - r.maxZ);
    best = Math.min(best, Math.hypot(dx, dz));
  }
  return best;
}

/** One tree of the belt: which template, where, turned and scaled. */
export interface BeltTree {
  template: number;
  x: number;
  z: number;
  yaw: number;
  scale: number;
}

/** The belt lies this far out from walkable ground: past the authored ranks, in front of the far cards. */
export const BELT = { near: 5, far: 19, spacing: 6.2 };

/**
 * A belt of old trees all round the map, just outside everything Sora can reach: the
 * authored edge trees stand in front of it and the painted far forest behind, so wherever
 * she looks past a wall there are trunks behind trunks behind trunks.
 */
export function layoutBelt(templates: number, seed = 5517): BeltTree[] {
  const random = seededRandom(seed);
  const trees: BeltTree[] = [];
  const { near, far, spacing } = BELT;
  for (let x = -81 - far; x <= 63 + far; x += spacing)
    for (let z = -97 - far; z <= 40 + far; z += spacing) {
      const px = x + (random() - 0.5) * spacing * 0.8,
        pz = z + (random() - 0.5) * spacing * 0.8;
      const d = toWalkable(px, pz);
      // Thinning out towards the far side of the belt, where the cards take over.
      if (d < near || d > far || random() > 1 - ((d - near) / (far - near)) * 0.45) continue;
      trees.push({
        template: Math.floor(random() * templates),
        x: px,
        z: pz,
        yaw: random() * Math.PI * 2,
        scale: 0.85 + random() * 0.35,
      });
    }
  return trees;
}

/** Undergrowth patches along the belt's near edge, where the lamp and the eye reach. */
export function layoutUndergrowth(templates: number, seed = 5521): BeltTree[] {
  const random = seededRandom(seed);
  const patches: BeltTree[] = [];
  const step = 8;
  for (let x = -81 - 14; x <= 63 + 14; x += step)
    for (let z = -97 - 14; z <= 40 + 14; z += step) {
      const px = x + (random() - 0.5) * 3,
        pz = z + (random() - 0.5) * 3;
      const d = toWalkable(px, pz);
      if (d < BELT.near || d > BELT.near + 7) continue;
      patches.push({
        template: Math.floor(random() * templates),
        x: px,
        z: pz,
        yaw: random() * Math.PI * 2,
        scale: 1,
      });
    }
  return patches;
}

/** Authored trees copied for the belt: outer-rank giants and bamboo, never zone trees (they switch off). */
const TEMPLATE_NODE = /^(tree_7\d\d|bamboo_\d+)$/;

/**
 * Copies a handful of the area's own trees before batching, for the belt. Taken from the
 * compound's outer ranks, which are always present.
 */
export function captureBeltTemplates(
  container: AssetContainer,
  count = 9,
): {
  trees: PlantTemplate[];
  undergrowth: PlantTemplate[];
} {
  const nodes = [...container.transformNodes, ...container.meshes].filter((n) =>
    TEMPLATE_NODE.test(n.name),
  );
  const trees = nodes.filter((n) => n.name.startsWith("tree_"));
  const bamboo = nodes.filter((n) => n.name.startsWith("bamboo_"));
  // Spread the picks over the list, so the belt mixes tall and short, broad and narrow.
  const pick = <T>(list: T[], n: number) =>
    Array.from(
      { length: Math.min(n, list.length) },
      (_, i) => list[Math.floor((i * list.length) / n)],
    );
  const capture = (list: Node[]) =>
    list.map((node) => capturePlant(node)).filter((t): t is PlantTemplate => t !== null);
  // Mid-sized undergrowth patches from outside the zones: the densest are too heavy to repeat.
  const patches = container.meshes.filter(
    (m) =>
      /^pagoda_jungle_understory_/.test(m.name) &&
      m.getTotalVertices() > 7000 &&
      m.getTotalVertices() < 14000,
  );
  return {
    trees: capture([...pick(trees, count - 2), ...pick(bamboo, 2)]),
    undergrowth: capture(pick(patches, 3)),
  };
}

/**
 * Plants the belt on the far forest's floor, merged per material in 32 m cells: trees hidden
 * past 70 m (the far cards stand there), undergrowth past 40 m.
 */
export function buildBelt(
  scene: Scene,
  templates: { trees: readonly PlantTemplate[]; undergrowth: readonly PlantTemplate[] },
): Mesh[] {
  const plant = (
    list: BeltTree[],
    from: readonly PlantTemplate[],
    flex: (t: PlantTemplate) => number,
  ) =>
    list.map((t) => ({
      template: from[t.template],
      x: t.x,
      y: -0.06,
      z: t.z,
      yaw: t.yaw,
      scale: t.scale,
      flex: flex(from[t.template]),
    }));
  const { trees, undergrowth } = templates;
  return [
    ...(trees.length
      ? plantCopies(
          scene,
          "ep2_forest_belt",
          plant(layoutBelt(trees.length), trees, (t) =>
            t.name.startsWith("bamboo") ? 1.15 : 0.85,
          ),
          32,
          70,
        )
      : []),
    ...(undergrowth.length
      ? plantCopies(
          scene,
          "ep2_forest_belt_undergrowth",
          plant(layoutUndergrowth(undergrowth.length), undergrowth, () => 1.4),
          32,
          40,
        )
      : []),
  ];
}
