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

/** The pond east of the compound: its clearing, and its water. */
export const EAST_POND: Ellipse = {
  x: -38,
  z: -12.5,
  rx: 15.5,
  rz: 11.5,
  turn: (4 * Math.PI) / 180,
};
export const POND_WATER: Ellipse = { x: -38.5, z: -12, rx: 9.5, rz: 6, turn: (4 * Math.PI) / 180 };

/** Open ground in the built areas: no forest grows here. */
export const CLEARINGS: readonly Ellipse[] = [WEST_YARD, EAST_POND];

/** Trodden lanes from the compound to the areas. */
export const LANES: readonly (readonly (readonly [number, number])[])[] = [
  [
    [13, -11],
    [18, -11.2],
    [23, -12.6],
    [29, -14],
  ],
  [
    [-13, -8],
    [-18, -9],
    [-22.5, -12.3],
    [-27.2, -11.6],
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

/**
 * A lane as it is walked: a smooth curve through its control points (Catmull-Rom)
 * that wanders a little from side to side, fading out at both ends. The same
 * curve as village_layout.lane_curve in Blender space (this takes Babylon points).
 */
export function laneCurve(points: readonly (readonly [number, number])[]): [number, number][] {
  const ext = [points[0], ...points, points[points.length - 1]];
  const dense: [number, number][] = [];
  for (let i = 1; i < ext.length - 2; i++) {
    const [p0, p1, p2, p3] = [ext[i - 1], ext[i], ext[i + 1], ext[i + 2]];
    for (let k = 0; k < 8; k++) {
      const t = k / 8,
        t2 = t * t,
        t3 = t2 * t;
      const c = (j: 0 | 1) =>
        0.5 *
        (2 * p1[j] +
          (-p0[j] + p2[j]) * t +
          (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2 +
          (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3);
      dense.push([c(0), c(1)]);
    }
  }
  dense.push([points[points.length - 1][0], points[points.length - 1][1]]);
  const s = [0];
  for (let i = 1; i < dense.length; i++)
    s.push(s[i - 1] + Math.hypot(dense[i][0] - dense[i - 1][0], dense[i][1] - dense[i - 1][1]));
  const total = s[s.length - 1];
  // Seeded from the first point in Blender space, so both sides draw the same lane.
  const seed = -points[0][0] * 0.37 - points[0][1] * 0.21;
  return dense.map(([x, z], i) => {
    const a = dense[Math.max(i - 1, 0)],
      b = dense[Math.min(i + 1, dense.length - 1)];
    const dx = b[0] - a[0],
      dz = b[1] - a[1];
    const n = Math.hypot(dx, dz) || 1;
    const taper = Math.min(1, s[i] / 3, (total - s[i]) / 3);
    const off =
      taper * (0.55 * Math.sin(s[i] * 0.42 + seed) + 0.25 * Math.sin(s[i] * 1.13 + 2 * seed));
    return [x - (dz / n) * off, z + (dx / n) * off] as [number, number];
  });
}

const CURVES = LANES.map(laneCurve);

/** Distance to the nearest lane's (curved) centre line. */
export function laneDistance(x: number, z: number): number {
  let best = Infinity;
  for (const lane of CURVES)
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

/** In the pond's water (grown by `grow` metres). */
export function inPond(x: number, z: number, grow = 0): boolean {
  return ellipseValue(POND_WATER, x, z, grow) < 1;
}

/** Ground the expansion added: the forest here is grown at runtime, not authored. */
export function inNewGround(x: number, z: number): boolean {
  const o = OLD_TERRAIN;
  return x < o.minX || x > o.maxX || z < o.minZ || z > o.maxZ;
}
