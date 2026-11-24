import { Vector3 } from "@babylonjs/core/Maths/math.vector";

/**
 * Episode 1's five jump scares (the user approved them from Cycles previews, Nov 24,
 * 2026; the approved gameplay map's J1-J5, named here by place because the hunt's jars
 * are J1-J6 in data/hunt.ts). Each fires once per playthrough. Babylon space, metres
 * (Babylon x = -Blender x, y = Blender z, z = -Blender y).
 */
export const SCARES = ["kitchen", "washing", "backdoor", "jar", "loft"] as const;
export type ScareId = (typeof SCARES)[number];

/** The flag that remembers a scare has happened (it is saved with the others). */
export const scareFlag = (id: ScareId): string => `ep1.scare.${id}`;

/** The house's main floor (stilt_house.FLOOR) and the kitchen house's, on stilts beside it. */
export const HOUSE_FLOOR = 2.5;

interface Box {
  readonly minX: number;
  readonly maxX: number;
  readonly minZ: number;
  readonly maxZ: number;
}

const inside = (b: Box, p: { x: number; z: number }) =>
  p.x > b.minX && p.x < b.maxX && p.z > b.minZ && p.z < b.maxZ;

/** How squarely `forward` (Sora's look, any length) points from `from` to `to`, on the ground (-1..1). */
export function facing(
  forward: { x: number; z: number },
  from: { x: number; z: number },
  to: { x: number; z: number },
): number {
  const dx = to.x - from.x,
    dz = to.z - from.z;
  const d = Math.hypot(dx, dz),
    f = Math.hypot(forward.x, forward.z);
  if (d < 1e-4 || f < 1e-4) return 1;
  return (dx * forward.x + dz * forward.z) / (d * f);
}

const onFloor = (feet: { y: number }, floor: number) => Math.abs(feet.y - floor) < 0.6;

// ------------------------------------------------------------------ the kitchen house
/** The kitchen house (farmstead.KITCHEN: Blender x -28..-20, y 15.65..22.65), on stilts at the house's floor. */
export const KITCHEN_HOUSE: Box = { minX: 20.0, maxX: 28.0, minZ: -22.65, maxZ: -15.65 };
/** Its east door, the walkway's (Blender (-20, 19.15)): she comes in by it. */
export const KITCHEN_DOOR = new Vector3(20.0, HOUSE_FLOOR, -19.15);

/** The betel leaves are taken and Sora, in the kitchen house, has turned to its east door. */
export function kitchenTrigger(
  feet: Vector3,
  forward: { x: number; z: number },
  leavesTaken: boolean,
): boolean {
  return (
    leavesTaken &&
    inside(KITCHEN_HOUSE, feet) &&
    onFloor(feet, HOUSE_FLOOR) &&
    Math.hypot(feet.x - KITCHEN_DOOR.x, feet.z - KITCHEN_DOOR.z) > 1.6 &&
    facing(forward, feet, KITCHEN_DOOR) > 0.85
  );
}

// ------------------------------------------------------------------ the washing room
/** Behind the hall's altar (Blender x -3..3, y 17.5..22). */
export const WASHING_ROOM: Box = { minX: -3.0, maxX: 3.0, minZ: -22.0, maxZ: -17.5 };
/** The sheet thrown over the washing board's foot (house_new_rooms: Blender (-0.17, 19.85)). */
export const WASHING_SHEET = new Vector3(0.17, HOUSE_FLOOR + 0.46, -19.85);
/** Where the sheeted figure sits up, as in the J2 preview (Blender (0.75, 19.0), feet 9 cm under the floor). */
export const WASHING_FIGURE = new Vector3(-0.75, HOUSE_FLOOR - 0.09, -19.0);

/** Act II: Sora is in the washing room, near the board and looking at it. */
export function washingTrigger(
  feet: Vector3,
  forward: { x: number; z: number },
  actTwo: boolean,
): boolean {
  return (
    actTwo &&
    inside(WASHING_ROOM, feet) &&
    onFloor(feet, HOUSE_FLOOR) &&
    Math.hypot(feet.x - WASHING_FIGURE.x, feet.z - WASHING_FIGURE.z) < 2.2 &&
    facing(forward, feet, WASHING_FIGURE) > 0.55
  );
}

// ------------------------------------------------------------------ the nailed back door
/** The long corridor's nailed back door (stilt_house: Blender (0, 34)). */
export const BACK_DOOR = new Vector3(0, HOUSE_FLOOR, -34.0);
/** Where she stands behind it, on the porch's bare joists (the J3 preview: Blender (0.05, 34.42)). */
// (12 cm nearer than the preview's: there her hands came through the planks; at the
// preview's place the game's leaf hid them.)
export const BACK_DOOR_FIGURE = new Vector3(-0.05, HOUSE_FLOOR, -34.3);

/** Act II: Sora has come up the long corridor to the door and is facing it. */
export function backDoorTrigger(
  feet: Vector3,
  forward: { x: number; z: number },
  actTwo: boolean,
): boolean {
  return (
    actTwo &&
    Math.abs(feet.x - BACK_DOOR.x) < 0.75 &&
    feet.z < BACK_DOOR.z + 1.7 &&
    feet.z > BACK_DOOR.z - 0.2 &&
    onFloor(feet, HOUSE_FLOOR) &&
    facing(forward, feet, BACK_DOOR) > 0.7
  );
}

// ------------------------------------------------------------------ the jar
/** The hunt's jar under the back block that holds the first key piece (data/hunt.ts). */
export const SCARE_JAR = "J2";
/** The black water's height in the jar, above its foot (the J4 preview's). */
export const JAR_WATER = 0.7;
/** The water's radius there, just inside the jar's wall (HuntModels' profile). */
export const JAR_WATER_RADIUS = 0.255;

// ------------------------------------------------------------------ the barn loft
/** The rice barn's loft floor (farmstead: the barn floor 1.2 m up, the loft 2.35 m over it). */
export const LOFT_FLOOR = 1.2 + 2.35;
/** The barn, inside its walls (data/hunt's BARN_AREA). */
export const BARN: Box = { minX: -28.8, maxX: -21.2, minZ: -25.3, maxZ: -19.7 };

/** Act III: climbing the loft ladder, Sora's head has come up over the loft's edge. */
export function loftTrigger(eye: Vector3, climbing: boolean, actThree: boolean): boolean {
  return actThree && climbing && inside(BARN, eye) && eye.y > LOFT_FLOOR + 0.22;
}
