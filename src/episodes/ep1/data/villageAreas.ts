/**
 * The village expansion (November 2026): the clearings and side lanes of the
 * areas built round the family compound so far. Babylon space, metres, mirrored
 * from tools/areas/village_layout.py (x = -x, z = -y; an ellipse's turn is
 * unchanged by that half-turn). Keep the two in step.
 */

export interface Ellipse {
  x: number;
  z: number;
  rx: number;
  rz: number;
  /** Turn of the ellipse's first axis (radians). */
  turn: number;
}

/** The old family yard west of the compound (ruined first house, granary, byre). */
export const WEST_YARD: Ellipse = { x: 41, z: -15.5, rx: 12.5, rz: 11, turn: (-6 * Math.PI) / 180 };

/** Open ground in the built areas: no forest grows here. */
export const CLEARINGS: readonly Ellipse[] = [WEST_YARD];

/** Trodden lanes from the compound to the areas. */
export const LANES: readonly (readonly (readonly [number, number])[])[] = [
  [
    [13, -11],
    [18, -11.2],
    [23, -12.6],
    [29, -14],
  ],
];
export const LANE_WIDTH = 1.1;

/** The authored ground before the expansion (the forest there is authored too). */
export const OLD_TERRAIN = { minX: -40, maxX: 40, minZ: -40, maxZ: 92 };

/** < 1 inside the ellipse grown by `grow` metres. */
export function ellipseValue(e: Ellipse, x: number, z: number, grow = 0): number {
  const c = Math.cos(-e.turn),
    s = Math.sin(-e.turn);
  const u = (x - e.x) * c - (z - e.z) * s;
  const v = (x - e.x) * s + (z - e.z) * c;
  return (u / (e.rx + grow)) ** 2 + (v / (e.rz + grow)) ** 2;
}

export function inClearing(x: number, z: number, grow = 0): boolean {
  return CLEARINGS.some((e) => ellipseValue(e, x, z, grow) < 1);
}

/** Distance to the nearest lane's centre line. */
export function laneDistance(x: number, z: number): number {
  let best = Infinity;
  for (const lane of LANES)
    for (let i = 0; i + 1 < lane.length; i++) {
      const [ax, az] = lane[i];
      const [bx, bz] = lane[i + 1];
      const dx = bx - ax,
        dz = bz - az;
      const t = Math.max(0, Math.min(1, ((x - ax) * dx + (z - az) * dz) / (dx * dx + dz * dz)));
      best = Math.min(best, Math.hypot(x - ax - t * dx, z - az - t * dz));
    }
  return best;
}

/** Ground the expansion added: the forest here is grown at runtime, not authored. */
export function inNewGround(x: number, z: number): boolean {
  const o = OLD_TERRAIN;
  return x < o.minX || x > o.maxX || z < o.minZ || z > o.maxZ;
}
