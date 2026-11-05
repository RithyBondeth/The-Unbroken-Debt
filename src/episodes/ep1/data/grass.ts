import { seededRandom } from "../../../audio/synth";
import { inSaveShrineClearing } from "./saveShrine";
import { PLAY, ROAD_Z, YARD, inBelt, inBund, inside, outside, pathDistance } from "./forestBorder";

/**
 * Tall grass (smau) round the village: thick on the road bank, along the
 * paddies' bunds and at the edge of the swept yard, where light reaches the
 * ground; only a thin fringe along the forest path under the old canopy. The trodden path, the road, the yard, the shrine
 * clearing, the pond and the wells stay bare. Babylon space, metres.
 */

export interface GrassClump {
  x: number;
  z: number;
  yaw: number;
  /** Height of the clump (m). */
  scale: number;
  /** 0, 1 green; 2 dry, straw-tipped (more of it on the road's sunny bank). */
  variant: number;
}

export interface GrassOptions {
  /** Grid spacing (m); lower presets space clumps further apart. */
  spacing: number;
  seed?: number;
  /** False where buildings and other art stand. */
  clear: (x: number, z: number, radius: number) => boolean;
}

const POND = { x: 20, z: -19, rx: 5.5, rz: 4.5 };
const WELLS: readonly (readonly [number, number])[] = [
  [17, -7.5],
  [-9.5, 33],
];

/** A verge: none on the trodden ground, thickest a step off it, thinning away. */
function verge(d: number, edge: number, width: number): number {
  if (d < edge || d > edge + width) return 0;
  const t = (d - edge) / width;
  return Math.min(1, t * 5) * (1 - t * t);
}

/** How likely tall grass is to grow at a point, 0–1. */
export function grassChance(x: number, z: number): number {
  if (!inside(PLAY, x, z, 0.5)) return 0;
  if (inSaveShrineClearing(x, z, 0.5)) return 0;
  if (inside(YARD, x, z, 0.4)) return 0;
  if (((x - POND.x) / POND.rx) ** 2 + ((z - POND.z) / POND.rz) ** 2 < 1) return 0;
  if (WELLS.some(([wx, wz]) => Math.hypot(x - wx, z - wz) < 1.8)) return 0;
  const path = pathDistance(x, z);
  const road = Math.abs(z - ROAD_Z);
  if (path < 0.9 || road < 2.4) return 0;
  let chance = 0;
  // Under the old-growth canopy little grass grows: a thin fringe along the trodden path.
  if (z > 2 && z < 61) chance = Math.max(chance, 0.45 * verge(path, 0.9, 3.4));
  if (Math.abs(x) < 34) chance = Math.max(chance, 0.85 * verge(road, 2.4, 3.2));
  if (inBund(x, z)) chance = Math.max(chance, 0.6);
  const yard = outside(YARD, x, z);
  if (yard > 0 && yard < 3) chance = Math.max(chance, 0.45 * (1 - yard / 3));
  if (inBelt(x, z)) chance = Math.max(chance, 0.22);
  return chance;
}

/** Clumps on a jittered grid, kept where `grassChance` allows. Deterministic. */
export function layoutGrass(options: GrassOptions): GrassClump[] {
  const random = seededRandom(options.seed ?? 6242070);
  const s = options.spacing;
  const clumps: GrassClump[] = [];
  for (let gx = PLAY.minX; gx < PLAY.maxX; gx += s)
    for (let gz = PLAY.minZ; gz < PLAY.maxZ; gz += s) {
      const x = gx + s * random(),
        z = gz + s * random();
      const u = random(),
        yaw = random() * Math.PI * 2,
        k = random(),
        v = random();
      const chance = grassChance(x, z);
      if (u > chance || !options.clear(x, z, 0.3)) continue;
      const roadside = Math.abs(z - ROAD_Z) < 6;
      clumps.push({
        x,
        z,
        yaw,
        scale: (0.45 + 0.65 * k) * (0.65 + 0.35 * chance),
        variant: v < (roadside ? 0.45 : 0.18) ? 2 : v < 0.6 ? 0 : 1,
      });
    }
  return clumps;
}
