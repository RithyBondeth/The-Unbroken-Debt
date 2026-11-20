import { seededRandom } from "@/audio/synth";
import { inSaveShrineClearing } from "./saveShrine";
import {
  PLAY,
  ROAD_Z,
  YARD,
  inBelt,
  inBund,
  inWild,
  inside,
  outside,
  pathDistance,
} from "./forestBorder";
import { CLEARINGS, ellipseValue, inPond, laneDistance } from "./villageAreas";

/**
 * Tall grass (smau) round the village: thick on the road bank, along the
 * paddies' bunds and at the edge of the swept yard, where light reaches the
 * ground; only a thin fringe along the forest path under the old canopy. The
 * expansion's abandoned clearings have grown over with it, all but their lanes.
 * The trodden path, the road, the yard, the shrine clearing, the pond and the
 * wells stay bare. Babylon space, metres.
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

/** 0-1 in soft-edged patches a few metres across (light gaps in the canopy). */
function patch(x: number, z: number): number {
  const n =
    0.5 +
    0.3 * Math.sin(x * 0.41 + 1.3) * Math.cos(z * 0.37 - 0.7) +
    0.2 * Math.sin(x * 0.93 - z * 0.71 + 2.1);
  return Math.max(0, Math.min(1, (n - 0.55) / 0.25));
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
  const lane = laneDistance(x, z);
  if (path < 0.9 || road < 2.4 || lane < 0.6) return 0;
  // The pond and its wet bank: reeds there are authored (east_pond.py).
  if (inPond(x, z, 2.6)) return 0;
  let chance = 0;
  // A thick fringe of grass along the trodden path, thinning into the forest (the user,
  // Nov 19: "there should be more and more grasses").
  if (z > 2 && z < 61) chance = Math.max(chance, 0.72 * verge(path, 0.9, 5.5));
  if (Math.abs(x) < 54) chance = Math.max(chance, 0.95 * verge(road, 2.4, 4.6));
  // The overgrown clearings: thick in the open, thinning under the trees at their edge.
  for (const e of CLEARINGS) {
    const k = ellipseValue(e, x, z);
    if (k < 1.3) chance = Math.max(chance, 0.8 * (1 - Math.max(0, k - 0.7) / 0.6));
  }
  if (lane < 4) chance = Math.max(chance, 0.6 * verge(lane, 0.6, 3.4));
  if (inWild(x, z)) chance = Math.max(chance, 0.26);
  if (inBund(x, z)) chance = Math.max(chance, 0.85);
  const yard = outside(YARD, x, z);
  if (yard > 0 && yard < 5) chance = Math.max(chance, 0.7 * (1 - yard / 5));
  if (inBelt(x, z)) chance = Math.max(chance, 0.42);
  // Patches under the trees where a gap in the canopy lets light down.
  if (z > 2 && z < 61 && path < 24) chance = Math.max(chance, 0.4 * patch(x, z));
  // The countryside round the house (Nov 19): grass on every bit of dry ground, the
  // mounds, the dikes' crowns and the banks (the game keeps it out of the water).
  chance = Math.max(chance, 0.42 + 0.3 * patch(x, z));
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
