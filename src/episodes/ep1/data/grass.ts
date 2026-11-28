import { seededRandom } from "@/audio/synth";
import { FARM } from "./farmLayout";
import { farmWildness } from "./farmGround";
import { fbm } from "./pathGround";

/**
 * Tall grass (smau) on the farmstead (Nov 22, 2026): patches of it thick where nobody
 * walks (away from the paths and the doors, at the feet of the fences, on the fields'
 * bunds), a few clumps elsewhere; none on the paths, the cart track, in the buildings or
 * on the fields' stubble. The same measure of wildness as the authored weeds
 * (tools/areas/farmstead.py ground_cover). Babylon space, metres.
 */

export interface GrassClump {
  x: number;
  z: number;
  yaw: number;
  /** Height of the clump (m). */
  scale: number;
  /** 0, 1 green; 2 dry, straw-tipped (more of it in the open). */
  variant: number;
}

export interface GrassOptions {
  /** Grid spacing (m); lower presets space clumps further apart. */
  spacing: number;
  seed?: number;
  /** False where buildings and other art stand. */
  clear: (x: number, z: number, radius: number) => boolean;
}

/** How likely tall grass is to grow at a point, 0-1. */
export function grassChance(x: number, z: number): number {
  const wild = farmWildness(x, z);
  if (wild <= 0) return 0;
  // Thick in patches a few metres across (the previews' smau), and the yard between them
  // grown over too (the approved previews: grass to the house's feet, Nov 22, 2026).
  const patch = fbm(x / 7 + 31, z / 7 - 17);
  if (wild > 0.45 && patch > 0.42) return 0.95;
  return 0.22 + 0.55 * wild * smooth01((patch - 0.22) / 0.3);
}

function smooth01(t: number): number {
  const c = Math.max(0, Math.min(1, t));
  return c * c * (3 - 2 * c);
}

/** Clumps on a jittered grid, kept where `grassChance` allows. Deterministic. */
export function layoutGrass(options: GrassOptions): GrassClump[] {
  const random = seededRandom(options.seed ?? 6242070);
  const s = options.spacing;
  const clumps: GrassClump[] = [];
  for (let gx = FARM.minX; gx < FARM.maxX; gx += s)
    for (let gz = FARM.minZ; gz < FARM.maxZ; gz += s) {
      const x = gx + s * random(),
        z = gz + s * random();
      const u = random(),
        yaw = random() * Math.PI * 2,
        k = random(),
        v = random();
      const chance = grassChance(x, z);
      if (u > chance || !options.clear(x, z, 0.3)) continue;
      // Straw-tipped clumps where the sun reaches: on the fields' bunds and the open yard.
      const open = chance > 0.9 ? 0.3 : 0.18;
      clumps.push({
        x,
        z,
        yaw,
        scale: (0.45 + 0.65 * k) * (0.65 + 0.35 * chance),
        variant: v < open ? 2 : v < 0.6 ? 0 : 1,
      });
    }
  return clumps;
}
