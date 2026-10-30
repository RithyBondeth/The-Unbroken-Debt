import { Vector3 } from "@babylonjs/core/Maths/math.vector";

/** Blender's west/south kitchen openings, converted to the game's coordinates. */
export const KRASUE_WINDOWS = [
  {
    id: "west",
    center: new Vector3(6, 3.86, -13),
    normal: new Vector3(1, 0, 0),
    tangent: new Vector3(0, 0, 1),
  },
  {
    id: "south",
    center: new Vector3(4.2, 3.86, -11.44),
    normal: new Vector3(0, 0, 1),
    tangent: new Vector3(1, 0, 0),
  },
] as const;
export type KrasueWindow = (typeof KRASUE_WINDOWS)[number];

/** A sight segment must fit the actual 80 × 95 cm hole, never the wall beside it. */
export function throughKrasueWindow(from: Vector3, to: Vector3, window: KrasueWindow): boolean {
  const a = Vector3.Dot(from.subtract(window.center), window.normal);
  const b = Vector3.Dot(to.subtract(window.center), window.normal);
  if (a <= 0 || b >= 0) return false;
  const hit = Vector3.Lerp(from, to, a / (a - b)).subtract(window.center);
  return Math.abs(Vector3.Dot(hit, window.tangent)) < 0.37 && hit.y > -0.53 && hit.y < 0.36;
}

export function inKrasueKitchen(eye: Vector3): boolean {
  return (
    eye.x > 3.05 && eye.x < 5.96 && eye.z > -14.46 && eye.z < -11.5 && eye.y > 3.05 && eye.y < 4.7
  );
}
