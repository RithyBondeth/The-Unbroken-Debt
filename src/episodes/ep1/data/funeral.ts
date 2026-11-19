import { Vector3 } from "@babylonjs/core/Maths/math.vector";

/**
 * Where Sok lies (the user, Nov 19, 2026: "I want the whole funeral, cuffin, etc inside
 * the house"): the funeral moved out of the yard tent into the house's central hall,
 * upstairs (tools/areas/funeral_indoors.py). Babylon space, metres.
 *
 * Everything that stood in the tent moved as one piece by FUNERAL_SHIFT (Blender's
 * (-0.25, +10, +2.5): Babylon x = -x, y = z, z = -y), so a position authored against the
 * tent is `tent.add(FUNERAL_SHIFT)`. The dais was narrowed and the corner burners and
 * lanterns pulled in to fit the room; the game reads those from their markers.
 */
export const FUNERAL_SHIFT = new Vector3(0.25, 2.5, -10);

/** A tent-authored position, moved into the hall. */
export function inHall(x: number, y: number, z: number): Vector3 {
  return new Vector3(x, y, z).addInPlace(FUNERAL_SHIFT);
}

/** The central hall's floor (the house's FLOOR) and walls' inner faces. */
export const HALL = { minX: -2.94, maxX: 2.94, minZ: -21.94, maxZ: -11.56, floor: 2.5 } as const;

/** Is Sora in the funeral room (the hall, on its floor)? */
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

/** The coffin's centre on its dais, at the hall's floor. */
export const COFFIN = inHall(0, 0, -5.9);

/** A tent-authored [x, y, z], moved into the hall (for builders taking arrays). */
export function hallAt(p: readonly [number, number, number]): [number, number, number] {
  return [p[0] + FUNERAL_SHIFT.x, p[1] + FUNERAL_SHIFT.y, p[2] + FUNERAL_SHIFT.z];
}
