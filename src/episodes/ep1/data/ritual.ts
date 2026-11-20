import { inHall } from "./funeral";

/** Clear aisle in front of the main burner in the hall; Babylon's north is negative Z. */
export const CP6_FEET = inHall(0, 0, -2.5);
export const CP6_YAW = Math.PI;
export const RITUAL_BURNER = inHall(0, 0.57, -3.55);
