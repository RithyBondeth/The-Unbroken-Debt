import { fbm } from "./pathGround";
import { PLAY, ROAD_Z, TERRAIN, VILLAGE_ROAD, outside } from "./forestBorder";
import { BUILDINGS } from "./farmLayout";
import { farmPathDistance, rectDistance } from "./farmGround";

/**
 * Where the night mist lies in the village and how high it stands (the user, Nov 19:
 * "implement the mist along with the forest to make thing very scary"). Babylon x/z.
 *
 * - Over the farm's open ground and dry fields it lies low, as it does at night in the
 *   countryside; here and there a taller bank drifts across and the sheds and the tree
 *   line go into it.
 * - Past the walls it thickens into a wall of its own: the fields have no edge to see,
 *   they go on into the mist.
 * - The paths, the cart track and the ground round the buildings keep only a thin
 *   ground mist, so the way stays readable and the house and the funeral stand clear.
 * - The village road outside the gate lies under a low mist between its fallen trees.
 */

/** Map texels per metre, and the margin (m) the map runs past the authored terrain. */
export const MIST_RESOLUTION = 0.5;
export const MIST_MARGIN = 40;

export const MIST_BOUNDS = {
  minX: TERRAIN.minX - MIST_MARGIN,
  minZ: TERRAIN.minZ - MIST_MARGIN,
  width: TERRAIN.maxX - TERRAIN.minX + 2 * MIST_MARGIN,
  depth: TERRAIN.maxZ - TERRAIN.minZ + 2 * MIST_MARGIN,
};

/** Tallest mist (m) at height 1. */
export const MIST_HEIGHT = 7;

function smoothstep(a: number, b: number, x: number): number {
  const t = Math.max(0, Math.min(1, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
}

export interface MistAt {
  /** 0-1 thickness. */
  density: number;
  /** 0-1 of MIST_HEIGHT. */
  height: number;
}

/** The mist at (x, z). */
export function mistAt(x: number, z: number): MistAt {
  const banks = fbm(x * 0.06 + 13, z * 0.06 - 5);
  const breakup = fbm(x * 0.21 - 3, z * 0.21 + 17);
  const wall = outside(PLAY, x, z);
  // The farm's open ground and its dry fields (Nov 22): mist lying low everywhere, waist
  // to chest high, and here and there a bank of it standing taller, drifting across so
  // the sheds and the tree line go and come back.
  let density = 0.5 + 0.45 * smoothstep(0.4, 0.75, banks);
  let height = (0.9 + 1.2 * banks + 2.4 * smoothstep(0.68, 0.85, banks)) / MIST_HEIGHT;

  // Past the walls: a wall of mist, taller than the tree line's undergrowth.
  if (wall > -6) {
    const k = smoothstep(-6, 10, wall);
    density = Math.max(density, 0.55 + 0.45 * k);
    height = Math.max(height, (3.5 + 3.5 * k) / MIST_HEIGHT);
  }

  // The road and its bank: thinner, low.
  const road = 1 - smoothstep(2.5, 5, Math.abs(z - ROAD_Z));
  density *= 1 - 0.55 * road;
  height = height * (1 - road) + (0.9 / MIST_HEIGHT) * road;

  // The village road outside the gate and the shop fronts along it (Nov 25, 2026): thin
  // and low where Sora walks, so the shops' lamps and posters read from the gate; past
  // the fallen trees at its ends the mist closes over it again.
  const along = 1 - smoothstep(VILLAGE_ROAD.walkX - 4, VILLAGE_ROAD.walkX + 8, Math.abs(x));
  const village = (1 - smoothstep(6, 11, Math.abs(z - VILLAGE_ROAD.z))) * along;
  density *= 1 - 0.5 * village;
  height = height * (1 - village) + (1.1 / MIST_HEIGHT) * village;

  // The farm's paths, its cart track and round its buildings: a thin ground mist only.
  const path = 1 - smoothstep(1.2, 4.5, farmPathDistance(x, z));
  const yard = 1 - smoothstep(-1, 4, rectDistance(x, z, BUILDINGS));
  const clear = Math.max(path * 0.8, yard);
  density *= 1 - 0.7 * clear;
  height = height * (1 - clear) + (0.6 / MIST_HEIGHT) * clear;

  return {
    density: Math.max(0, Math.min(1, density * (0.75 + 0.25 * breakup))),
    height: Math.max(0, Math.min(1, height)),
  };
}

/** The map as RGBA bytes (R thickness, G height), rows along +z. */
export function bakeMistField(): { data: Uint8Array; width: number; height: number } {
  const width = Math.round(MIST_BOUNDS.width * MIST_RESOLUTION);
  const height = Math.round(MIST_BOUNDS.depth * MIST_RESOLUTION);
  const data = new Uint8Array(width * height * 4);
  for (let j = 0; j < height; j++)
    for (let i = 0; i < width; i++) {
      const x = MIST_BOUNDS.minX + (i + 0.5) / MIST_RESOLUTION;
      const z = MIST_BOUNDS.minZ + (j + 0.5) / MIST_RESOLUTION;
      const m = mistAt(x, z);
      const k = (j * width + i) * 4;
      data[k] = Math.round(m.density * 255);
      data[k + 1] = Math.round(m.height * 255);
      data[k + 3] = 255;
    }
  return { data, width, height };
}
