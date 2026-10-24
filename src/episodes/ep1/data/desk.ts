import { Vector3 } from "@babylonjs/core/Maths/math.vector";

/** Clear south aisle: CP4 always restores under the tent facing the house. */
export const CP4_FEET = new Vector3(0, 0, -2);
export const CP4_YAW = Math.PI;

/** Episode 1 script, required journal page B (A2-07). */
export const JOURNAL_B = [
  {
    title: "The first seal",
    text: "The first seal is the bronze token Grandfather wore. It is in the iron chest behind the planks of this room.",
  },
  {
    title: "The jars beneath the house",
    text: "I broke the chest key into three and gave the pieces to the water jars beneath the house, where only family would look. Burn the token in the incense at the coffin, with matches blessed at our altar, before the third hour. Do not turn around while it burns. Whatever stands behind you, do not turn around.",
  },
  {
    title: "Then the pagoda",
    text: "Then the map. Then the pagoda. Then the rest. I am sorry it falls to you.",
  },
] as const;

/** Remaining practical lamps; the pavilion lamps were already snuffed in A2-01. */
export const FAILING_LAMPS = [
  { light: "veranda", mesh: /^(veranda_lantern_flame|veranda_lamp_flame)(\.|$)/ },
  { light: "hall", mesh: /^hall_altar_lamp_flame(\.|$)/ },
  { light: "kitchen", mesh: /^kitchen_lamp_flame(\.|$)/ },
] as const;
