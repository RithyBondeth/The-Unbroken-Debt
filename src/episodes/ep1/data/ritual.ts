import { Vector3 } from "@babylonjs/core/Maths/math.vector";

/**
 * The ritual at the burner on the offering table under the house (marker_main_burner at
 * Blender (1.25, 15.1)): Sora kneels a metre in front of it, between the candle rows,
 * facing north to the coffin (Babylon's north is negative Z).
 */
export const CP6_FEET = new Vector3(-1.25, 0, -14.05);
export const CP6_YAW = Math.PI;
/** The burner's rim (marker_main_burner, at Blender (1.25, 15.1, 0.63)): where the token burns. */
export const RITUAL_BURNER = new Vector3(-1.25, 0.6, -15.1);
