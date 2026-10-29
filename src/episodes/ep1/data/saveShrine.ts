import { Vector3 } from "@babylonjs/core/Maths/math.vector";

/** Beyond the compound's front-right fence corner (x=-13, z=3).
 * Reachable from the existing main gate along the outside of the front fence.
 */
export const SAVE_SHRINE_POSITION = new Vector3(-15.2, 0, 10.5);
export const SAVE_SHRINE_APPROACH = SAVE_SHRINE_POSITION.add(new Vector3(0, 0, 1.45));
export const SAVE_SHRINE_LOCATION = "Outside compound · Spirit house";
export const SAVE_SHRINE_ROUTE = [
  new Vector3(0, 0, 5.4),
  new Vector3(0, 0, 10.5),
  new Vector3(-13.6, 0, 10.5),
  SAVE_SHRINE_APPROACH,
];

/** Reserve a small clearing and a walkable strip outside the front fence. */
export function inSaveShrineClearing(x: number, z: number, radius = 0): boolean {
  if (Math.hypot(x - SAVE_SHRINE_POSITION.x, z - SAVE_SHRINE_POSITION.z) < 2.1 + radius)
    return true;
  return SAVE_SHRINE_ROUTE.slice(1).some((b, i) => {
    const a = SAVE_SHRINE_ROUTE[i],
      dx = b.x - a.x,
      dz = b.z - a.z;
    const t = Math.max(0, Math.min(1, ((x - a.x) * dx + (z - a.z) * dz) / (dx * dx + dz * dz)));
    return Math.hypot(x - a.x - dx * t, z - a.z - dz * t) < 0.95 + radius;
  });
}
