import { BUILDINGS, FARM, FARM_PATHS, FENCES, FIELDS } from "./farmLayout";
import type { Rect } from "./forestBorder";

/**
 * Distances over the farmstead's plan (data/farmLayout.ts), for what grows on its
 * ground: the same measures tools/areas/farmstead.py's ground cover uses, so the game's
 * tall grass stands where the Cycles previews put the authored weeds. Babylon space.
 */

function segmentDistance(
  px: number,
  pz: number,
  ax: number,
  az: number,
  bx: number,
  bz: number,
): number {
  const dx = bx - ax,
    dz = bz - az;
  const l2 = dx * dx + dz * dz;
  const t = l2 === 0 ? 0 : Math.max(0, Math.min(1, ((px - ax) * dx + (pz - az) * dz) / l2));
  return Math.hypot(px - ax - t * dx, pz - az - t * dz);
}

/** Metres to the nearest path's (or the cart track's) trodden edge; < 0 on it. */
export function farmPathDistance(x: number, z: number): number {
  let best = Infinity;
  for (const { points, half } of FARM_PATHS)
    for (let i = 1; i < points.length; i++) {
      const [a, b] = [points[i - 1], points[i]];
      best = Math.min(best, segmentDistance(x, z, a[0], a[1], b[0], b[1]) - half);
    }
  return best;
}

/** Metres to the nearest of the rectangles; < 0 inside one. */
export function rectDistance(x: number, z: number, rects: readonly Rect[]): number {
  let best = Infinity;
  for (const r of rects) {
    const dx = Math.max(r.minX - x, 0, x - r.maxX),
      dz = Math.max(r.minZ - z, 0, z - r.maxZ);
    best = Math.min(
      best,
      dx || dz ? Math.hypot(dx, dz) : -Math.min(x - r.minX, r.maxX - x, z - r.minZ, r.maxZ - z),
    );
  }
  return best;
}

/** Metres to the nearest fence line. */
export function fenceDistance(x: number, z: number): number {
  let best = Infinity;
  for (const [a, b] of FENCES) best = Math.min(best, segmentDistance(x, z, a[0], a[1], b[0], b[1]));
  return best;
}

export function smooth(a: number, b: number, x: number): number {
  const t = Math.max(0, Math.min(1, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
}

/**
 * How wild the ground is, 0-1: trodden bare by the doors and along the paths, thick at
 * the feet of the fences and on the fields' bunds, where nobody walks. 0 on a path, a
 * building or a field.
 */
export function farmWildness(x: number, z: number): number {
  if (x < FARM.minX || x > FARM.maxX || z < FARM.minZ || z > FARM.maxZ) return 0;
  const field = rectDistance(x, z, FIELDS);
  if (field < -0.7) return 0;
  const path = farmPathDistance(x, z);
  const building = rectDistance(x, z, BUILDINGS);
  if (path < 0.08 || building < 0.2) return 0;
  const wild = smooth(0.1, 2.8, path) * smooth(0.3, 3.2, building);
  const edge = Math.max(
    1 - smooth(0.1, 1.0, fenceDistance(x, z)),
    1 - smooth(0, 0.9, Math.abs(field)),
  );
  return Math.max(wild, 0.9 * edge * smooth(0, 0.5, path));
}
