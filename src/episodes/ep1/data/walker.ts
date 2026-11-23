import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { HOUSE_FLOOR, HOUSE_WALLS, type HouseWall } from "./houseWalls";

/**
 * Act II's walker in the re-planned house (Nov 22, 2026; the gameplay map the user
 * approved): up the rear stairs from under the back block, along the long corridor to
 * Sok's study door, through the washing room and the hall, and out by the front stairs.
 * Babylon space, metres (Babylon x = -Blender x, z = -Blender y).
 */

/** Clear floor inside Sok's study, facing its door onto the long corridor. */
export const CP3_FEET = new Vector3(1.7, HOUSE_FLOOR, -25.05);
export const CP3_YAW = -Math.PI / 2;
/** The wardrobes Sora can hide in: Sok's in his bedroom (west wall), Kanha's (east wall). */
export const WARDROBES = [
  { id: "H1", at: new Vector3(7.57, HOUSE_FLOOR, -29.0), yaw: -Math.PI / 2 },
  { id: "H2", at: new Vector3(-7.57, HOUSE_FLOOR, -26.2), yaw: Math.PI / 2 },
] as const;

const F = HOUSE_FLOOR;
/** The house's real stairs and doorways (tools/areas/stilt_house.py). */
export const WALKER_ROUTE = [
  // Out of the dark under the back block, east of the house, to the rear stairs' foot.
  { at: new Vector3(-9.4, 0, -28.2) },
  { at: new Vector3(-2.75, 0, -29.6) },
  // Up the stairs (north) to the landing, then west through its doorway.
  { at: new Vector3(-2.75, F, -33.3) },
  { at: new Vector3(-1.4, F, -32.25) },
  { at: new Vector3(0, F, -32.25) },
  // Down the long corridor; it stands at Sok's study door.
  { at: new Vector3(0, F, -25.05), pause: 4 },
  { at: new Vector3(0, F, -22.7) },
  // Through the washing room behind the altar and its east door into the hall.
  { at: new Vector3(-0.85, F, -22.6) },
  { at: new Vector3(-0.85, F, -20.6) },
  { at: new Vector3(-2.45, F, -18.4) },
  { at: new Vector3(-2.45, F, -16.6) },
  { at: new Vector3(0, F, -12.4) },
  // Out of the front door, along the veranda and down the front stairs.
  { at: new Vector3(0, F, -10.75) },
  { at: new Vector3(-6.05, F, -10.75) },
  { at: new Vector3(-8.6, 0, -10.75) },
  { at: new Vector3(-11.5, 0, -8.5) },
];

export const WALKER_SPEED = 1;
export const WALKER_CATCH_DISTANCE = 1.5;
export const hearingRadius = (loudness: number): number =>
  loudness <= 0.13 ? 2 : loudness <= 0.4 ? 6 : 10;

const onFloor = (p: Vector3): boolean => Math.abs(p.y - F) < 1;

/** Where the segment a-b crosses the wall's line, as a distance along the wall, or null. */
function crossing(wall: HouseWall, a: Vector3, b: Vector3): number | null {
  const [pa, pb] = wall.along === "x" ? [a.z, b.z] : [a.x, b.x];
  if ((pa - wall.at) * (pb - wall.at) >= 0) return null;
  const t = (wall.at - pa) / (pb - pa);
  const s = wall.along === "x" ? a.x + (b.x - a.x) * t : a.z + (b.z - a.z) * t;
  const lo = Math.min(wall.from, wall.to),
    hi = Math.max(wall.from, wall.to);
  return s >= lo && s <= hi ? s : null;
}

/**
 * Can the walker see or reach b from a without going through a wall? Both on the house's
 * floor, and every wall the segment crosses crossed in a doorway (a little in from its
 * jambs). Off the floor (the stairs, the ground) the walls don't apply.
 */
export function throughDoorways(a: Vector3, b: Vector3): boolean {
  if (!onFloor(a) || !onFloor(b)) return onFloor(a) === onFloor(b);
  for (const wall of HOUSE_WALLS) {
    const s = crossing(wall, a, b);
    if (s === null) continue;
    const lo = (g: readonly [number, number]) => Math.min(g[0], g[1]) + 0.08;
    const hi = (g: readonly [number, number]) => Math.max(g[0], g[1]) - 0.08;
    if (!wall.gaps.some((g) => s >= lo(g) && s <= hi(g))) return false;
  }
  return true;
}

/** The doorways' middles, a step either side of their walls: the walker's waypoints. */
const DOOR_POINTS: Vector3[] = HOUSE_WALLS.flatMap((wall) =>
  wall.gaps.flatMap(([g0, g1]) => {
    const mid = (g0 + g1) / 2;
    return [-0.45, 0.45].map((side) =>
      wall.along === "x"
        ? new Vector3(mid, F, wall.at + side)
        : new Vector3(wall.at + side, F, mid),
    );
  }),
);

/**
 * A sound in another room draws the walker there through the doorways: the shortest
 * chain of doorways from a to b (Dijkstra over the door points), ending at b.
 */
export function doorwayPath(a: Vector3, b: Vector3): Vector3[] {
  if (throughDoorways(a, b)) return [b.clone()];
  const nodes = [a, ...DOOR_POINTS, b];
  const end = nodes.length - 1;
  const dist = nodes.map(() => Infinity);
  const prev = nodes.map(() => -1);
  const done = nodes.map(() => false);
  dist[0] = 0;
  for (;;) {
    let u = -1;
    for (let i = 0; i < nodes.length; i++)
      if (!done[i] && dist[i] < Infinity && (u < 0 || dist[i] < dist[u])) u = i;
    if (u < 0 || u === end) break;
    done[u] = true;
    for (let v = 0; v < nodes.length; v++) {
      if (done[v] || !throughDoorways(nodes[u], nodes[v])) continue;
      const d = dist[u] + Vector3.Distance(nodes[u], nodes[v]);
      if (d < dist[v]) {
        dist[v] = d;
        prev[v] = u;
      }
    }
  }
  if (prev[end] < 0) return [b.clone()];
  const points: Vector3[] = [];
  for (let i = end; i > 0; i = prev[i]) points.unshift(nodes[i].clone());
  return points;
}
