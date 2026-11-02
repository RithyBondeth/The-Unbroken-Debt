import { Vector3 } from "@babylonjs/core/Maths/math.vector";

export const CP5_FEET = new Vector3(1.25, 0, -9.15);
export const CP5_YAW = Math.PI;
export const JARS = [
  { id: "J1", at: new Vector3(4.5, 0, -11), contents: "oil", piece: -1 },
  { id: "J2", at: new Vector3(1.5, 0, -16.5), contents: "key", piece: 0 },
  { id: "J3", at: new Vector3(-1.5, 0, -11.5), contents: "lore", piece: -1 },
  { id: "J4", at: new Vector3(-4.5, 0, -16.8), contents: "key", piece: 1 },
  { id: "J5", at: new Vector3(4.8, 0, -16.8), contents: "oil", piece: -1 },
  { id: "J6", at: new Vector3(-4.6, 0, -11.2), contents: "key", piece: 2 },
] as const;
export const FRAGMENT_IDS = ["brass_key_bow", "brass_key_shaft", "brass_key_bit"] as const;
export const ROAMER_ROUTE = [
  new Vector3(-3.6, 0, -16.6),
  new Vector3(-4.1, 0, -12.3),
  new Vector3(-1.5, 0, -10.65),
  new Vector3(4.1, 0, -11.9),
  new Vector3(3.8, 0, -15.3),
  new Vector3(0.4, 0, -16.6),
  new Vector3(-0.6, 0, -20.4),
];
export const inHunt = (at: Vector3): boolean =>
  at.y < 0.7 && at.y > -0.7 && Math.abs(at.x) < 5.85 && at.z < -9.65 && at.z > -22.2;
export const huntHearing = (loudness: number, jar = false): number =>
  jar ? 7 : loudness <= 0.13 ? 3 : loudness <= 0.4 ? 8 : 10;

/** The exported physical posts, jars and low storage, in Babylon world coordinates. */
export interface GroundObstacle {
  minX: number;
  maxX: number;
  minZ: number;
  maxZ: number;
}
export const HUNT_OBSTACLES: GroundObstacle[] = [
  ...[-6, -3, 0, 3, 6].flatMap((x) =>
    [-10, -14, -18, -22].map((z) => ({
      minX: x - 0.24,
      maxX: x + 0.24,
      minZ: z - 0.24,
      maxZ: z + 0.24,
    })),
  ),
  ...JARS.map(({ at }) => ({
    minX: at.x - 0.36,
    maxX: at.x + 0.36,
    minZ: at.z - 0.36,
    maxZ: at.z + 0.36,
  })),
  { minX: 4.2, maxX: 5.8, minZ: -13.6, maxZ: -13 },
  { minX: -2.6, maxX: -1, minZ: -15.4, maxZ: -14.6 },
  { minX: 4.95, maxX: 5.85, minZ: -15.95, maxZ: -14.95 },
  // The bathing corner's bamboo screens (open to the west) and its rainwater jar.
  { minX: -5.75, maxX: -3.25, minZ: -21.75, maxZ: -21.7 },
  { minX: -5.75, maxX: -5.7, minZ: -21.75, maxZ: -18.75 },
  { minX: -5.75, maxX: -3.25, minZ: -18.8, maxZ: -18.75 },
  { minX: -3.3, maxX: -3.25, minZ: -21.75, maxZ: -20.1 },
  { minX: -3.3, maxX: -3.25, minZ: -19.1, maxZ: -18.75 },
  { minX: -5.72, maxX: -4.88, minZ: -21.72, maxZ: -20.88 },
];
