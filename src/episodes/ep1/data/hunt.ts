import { Vector3 } from "@babylonjs/core/Maths/math.vector";

/**
 * The jar hunt (Act III) under the re-planned house (Nov 22, 2026): four jars among the
 * stilts under the back block, two in the rice barn behind its chained gate, whose key
 * lies in J3. The roamer hunts in both, coming after Sora when she goes from one to the
 * other. Babylon space, metres (Babylon x = -Blender x, z = -Blender y);
 * tools/areas/rebuild-farmstead.py puts the jars' meshes at these places.
 */

/** At the funeral's north edge, facing the dark under the back block. */
export const CP5_FEET = new Vector3(-1.0, 0, -21.4);
export const CP5_YAW = Math.PI;
export const JARS = [
  { id: "J1", at: new Vector3(6.2, 0, -24.0), contents: "oil", piece: -1 },
  { id: "J2", at: new Vector3(2.6, 0, -28.2), contents: "key", piece: 0 },
  // The barn gate's key (O3, the approved gameplay map): the barn's two jars lie behind it.
  { id: "J3", at: new Vector3(-2.4, 0, -24.6), contents: "gate", piece: -1 },
  { id: "J4", at: new Vector3(-6.1, 0, -31.8), contents: "key", piece: 1 },
  // The rice barn's floor, 1.2 m up.
  // Sok's folded pages (lore L2), carried to the barn with the jar they were hidden in.
  { id: "J5", at: new Vector3(-28.3, 1.2, -21.0), contents: "lore", piece: -1 },
  { id: "J6", at: new Vector3(-28.35, 1.2, -24.9), contents: "key", piece: 2 },
] as const;
export const FRAGMENT_IDS = ["brass_key_bow", "brass_key_shaft", "brass_key_bit"] as const;
/**
 * The Preay's pace under the house (m/s): an unhurried walk on patrol, and her stumbling
 * hurry when she has Sora, never faster than a person (build-preay.py: walk 0.81 and hurry
 * 1.08 m/s at 1x, played at most 1.6x).
 */
export const ROAMER_PATROL_SPEED = 1.0;
export const ROAMER_CHASE_SPEED = 1.7;

/** The ground under the back block, between its outer stilts. */
export const HUNT_AREA = { minX: -8.3, maxX: 8.3, minZ: -34.3, maxZ: -22.0 } as const;

/** Her round among the stilts, clear of the posts, the jars and the rear stairs. */
export const ROAMER_ROUTE = [
  new Vector3(-6.1, 0, -23.3),
  new Vector3(-2.1, 0, -26.5),
  new Vector3(2.6, 0, -23.4),
  new Vector3(6.0, 0, -27.9),
  new Vector3(2.3, 0, -31.8),
  new Vector3(-1.6, 0, -32.2),
  new Vector3(-4.9, 0, -32.2),
];
/** The rice barn's floor (farmstead.BARN: Blender x 21..29, y 19.5..25.5, 1.2 m up), inside its walls. */
export const BARN_AREA = { minX: -28.8, maxX: -21.2, minZ: -25.3, maxZ: -19.7 } as const;
export const BARN_FLOOR = 1.2;
/** In by the barn's open doors (its west wall), round the bins, the sacks and the loft ladder. */
export const BARN_ROUTE = [
  new Vector3(-21.8, BARN_FLOOR, -22.5),
  new Vector3(-24.0, BARN_FLOOR, -21.4),
  new Vector3(-27.3, BARN_FLOOR, -21.9),
  new Vector3(-26.6, BARN_FLOOR, -23.6),
  new Vector3(-24.4, BARN_FLOOR, -23.6),
  new Vector3(-22.2, BARN_FLOOR, -23.5),
];

/** A space the roamer hunts in: under the back block, or the rice barn's floor. */
export interface HuntArena {
  readonly id: "house" | "barn";
  readonly area: {
    readonly minX: number;
    readonly maxX: number;
    readonly minZ: number;
    readonly maxZ: number;
  };
  readonly floor: number;
  readonly route: readonly Vector3[];
  readonly obstacles: readonly GroundObstacle[];
}

const inside = (at: Vector3, arena: HuntArena) =>
  at.y < arena.floor + 0.7 &&
  at.y > arena.floor - 0.7 &&
  at.x > arena.area.minX &&
  at.x < arena.area.maxX &&
  at.z > arena.area.minZ &&
  at.z < arena.area.maxZ;
/** The arena `at` stands in, if any. */
export const arenaAt = (at: Vector3): HuntArena | null =>
  HUNT_ARENAS.find((arena) => inside(at, arena)) ?? null;
export const inHunt = (at: Vector3): boolean => arenaAt(at) !== null;
export const huntHearing = (loudness: number, jar = false): number =>
  jar ? 7 : loudness <= 0.13 ? 3 : loudness <= 0.4 ? 8 : 10;

/** The exported physical posts, jars and low storage, in Babylon world coordinates. */
export interface GroundObstacle {
  minX: number;
  maxX: number;
  minZ: number;
  maxZ: number;
}
const post = (x: number, z: number, r = 0.24): GroundObstacle => ({
  minX: x - r,
  maxX: x + r,
  minZ: z - r,
  maxZ: z + r,
});
export const HUNT_OBSTACLES: GroundObstacle[] = [
  // The back block's stilts (stilt_house.BACK_POSTS) and the front block's back row.
  ...[-8, -4.35, -0.7, 0.7, 4.35, 8].flatMap((x) => [-26, -30, -34].map((z) => post(x, z))),
  post(-8, -22),
  post(8, -22),
  ...[-6, -3, 0, 3, 6].map((x) => post(x, -22)),
  ...JARS.filter(({ at }) => at.y < 0.5).map(({ at }) => post(at.x, at.z, 0.36)),
  // The rear stairs (stilt_house.STAIR_HOLE), too low to pass under.
  { minX: -3.2, maxX: -2.3, minZ: -33.8, maxZ: -30.1 },
];

/** The barn's floor: the grain bins along the north wall, the sacks along the south, the loft ladder, the baskets, its jars. */
export const BARN_OBSTACLES: GroundObstacle[] = [
  { minX: -23.25, maxX: -21.55, minZ: -25.35, maxZ: -24.2 },
  { minX: -25.15, maxX: -23.45, minZ: -25.35, maxZ: -24.2 },
  { minX: -27.05, maxX: -25.35, minZ: -25.35, maxZ: -24.2 },
  { minX: -26.3, maxX: -21.3, minZ: -20.85, maxZ: -19.7 },
  { minX: -25.8, maxX: -25.05, minZ: -22.75, maxZ: -22.25 },
  post(-27.6, -23.5, 0.28),
  post(-28.2, -23.2, 0.25),
  post(-23.2, -23.1, 0.25),
  ...JARS.filter(({ at }) => at.y > 0.5).map(({ at }) => post(at.x, at.z, 0.36)),
];

export const HOUSE_ARENA: HuntArena = {
  id: "house",
  area: HUNT_AREA,
  floor: 0,
  route: ROAMER_ROUTE,
  obstacles: HUNT_OBSTACLES,
};
export const BARN_ARENA: HuntArena = {
  id: "barn",
  area: BARN_AREA,
  floor: BARN_FLOOR,
  route: BARN_ROUTE,
  obstacles: BARN_OBSTACLES,
};
export const HUNT_ARENAS: readonly HuntArena[] = [HOUSE_ARENA, BARN_ARENA];
/** Seconds after Sora changes arena before the roamer comes in after her. */
export const ROAMER_FOLLOWS_AFTER = 6;
