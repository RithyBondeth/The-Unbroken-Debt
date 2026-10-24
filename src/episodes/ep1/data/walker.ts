import { Vector3 } from "@babylonjs/core/Maths/math.vector";

/** Clear floor inside Sok's room, facing the open hall door. */
export const CP3_FEET = new Vector3(-4.15, 2.5, -13.55);
export const CP3_YAW = Math.PI / 2;
export const WARDROBES = [
  { id: "H1", at: new Vector3(-3.48, 2.5, -15.2), yaw: -Math.PI / 2 },
  { id: "H2", at: new Vector3(2.45, 2.5, -14.25), yaw: -Math.PI / 2 },
] as const;

/** Actual village stair / door positions, not the schematic drawing's route. */
export const WALKER_ROUTE = [
  { at: new Vector3(-8.6, 0, -10.75) },
  { at: new Vector3(-6.05, 2.5, -10.75) },
  { at: new Vector3(0, 2.5, -10.75) },
  { at: new Vector3(0, 2.5, -12) },
  { at: new Vector3(-0.25, 2.5, -13.45) },
  { at: new Vector3(-2.5, 2.5, -13.45), pause: 4 },
  { at: new Vector3(-1.65, 2.5, -13.45) },
  { at: new Vector3(-1.65, 2.5, -17.1) },
  { at: new Vector3(-2.35, 2.5, -17.1) },
  { at: new Vector3(-2.35, 2.5, -18.15) },
  { at: new Vector3(-2.35, 0, -20.8) },
];

export const WALKER_SPEED = 1;
export const WALKER_CATCH_DISTANCE = 1.5;
export const hearingRadius = (loudness: number): number =>
  loudness <= 0.13 ? 2 : loudness <= 0.4 ? 6 : 10;

/** Avoid catching through the room partitions; the segment must pass through a doorway. */
export function throughDoorways(a: Vector3, b: Vector3): boolean {
  for (const x of [-3, 3]) {
    if ((a.x - x) * (b.x - x) >= 0) continue;
    const z = a.z + (b.z - a.z) * ((x - a.x) / (b.x - a.x));
    if (x === -3 ? z < -13.9 || z > -13 : z < -13.4 || z > -12.5) return false;
  }
  return true;
}

/** A sound in a side room draws the walker through its door, in either direction. */
export function doorwayPath(a: Vector3, b: Vector3): Vector3[] {
  const points: Vector3[] = [];
  if (a.x < -3 && b.x >= -3)
    points.push(new Vector3(-3.6, 2.5, -13.45), new Vector3(-2.4, 2.5, -13.45));
  if (a.x > 3 && b.x <= 3)
    points.push(new Vector3(3.6, 2.5, -12.95), new Vector3(2.4, 2.5, -12.95));
  if (b.x < -3 && a.x >= -3)
    points.push(new Vector3(-2.4, 2.5, -13.45), new Vector3(-3.6, 2.5, -13.45));
  if (b.x > 3 && a.x <= 3)
    points.push(new Vector3(2.4, 2.5, -12.95), new Vector3(3.6, 2.5, -12.95));
  points.push(b.clone());
  return points;
}
