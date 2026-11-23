import { Vector3 } from "@babylonjs/core/Maths/math.vector";

/**
 * Where Sok lies (the user, Nov 21, 2026: the funeral moves to the ground under the
 * house, between its stilts, as at a modern Cambodian village funeral). Built by
 * tools/areas/funeral_under.py: the coffin under its canopy at Blender (1.5, 17.7), its
 * long axis east-west, the wreath and the offering table south of it. Babylon space,
 * metres (Babylon x = -Blender x, y = Blender z, z = -Blender y).
 *
 * Positions were first authored against the old yard tent (its coffin at (0, 0, -5.9)),
 * then moved into the hall; they now move under the house by FUNERAL_SHIFT, so a
 * tent-authored position is `tent.add(FUNERAL_SHIFT)`. The burners, the thread and the
 * people's places are read from their markers.
 */
export const FUNERAL_SHIFT = new Vector3(-1.5, 0, -11.8);

/** A tent-authored position, moved under the house. */
export function inHall(x: number, y: number, z: number): Vector3 {
  return new Vector3(x, y, z).addInPlace(FUNERAL_SHIFT);
}

/**
 * The funeral's ground under the house's front block, between its outer stilts (the
 * name is the old hall's: the funeral's room). `floor` is the ground's height there.
 */
export const HALL = { minX: -5.6, maxX: 5.6, minZ: -21.0, maxZ: -12.0, floor: 0 } as const;

/** Is Sora at the funeral (on the ground under the house's front block)? */
export function inFuneralRoom(feet: { x: number; y: number; z: number }): boolean {
  return (
    feet.x > HALL.minX &&
    feet.x < HALL.maxX &&
    feet.z > HALL.minZ &&
    feet.z < HALL.maxZ &&
    feet.y > HALL.floor - 0.6 &&
    feet.y < HALL.floor + 1.5
  );
}

/** The coffin's centre on its stand, at the ground. */
export const COFFIN = inHall(0, 0, -5.9);

/** A tent-authored [x, y, z], moved under the house (for builders taking arrays). */
export function hallAt(p: readonly [number, number, number]): [number, number, number] {
  return [p[0] + FUNERAL_SHIFT.x, p[1] + FUNERAL_SHIFT.y, p[2] + FUNERAL_SHIFT.z];
}

/**
 * The two incense pots smoking before the wreath (funeral_under.incense_and_candles: the
 * wreath at Blender (1.5, 16.2), the pots 0.55 m to either side and 0.35 m in front), at
 * the sticks' burning tips. The coffin's four corner pots are the vigil's (Vigil.ts).
 */
export const WREATH_INCENSE: readonly Vector3[] = [
  new Vector3(-0.95, 0.36, -15.85),
  new Vector3(-2.05, 0.36, -15.85),
];
