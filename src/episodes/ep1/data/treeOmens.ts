/**
 * Where the forest has been marked (Art Bible 3; Khmer folk belief, advisor
 * review pending): cotton thread wound round the trunks beside the path, as a
 * kru binds what lives in a tree; a cord strung across the path where the
 * village ends, its ties fluttering; blood on the bark; and the old strangler
 * fig (chrey) a Neak Ta or a preay is said to live in, wrapped in cloth, with
 * a pot and burnt-down incense at its roots. Babylon space, metres.
 */

export type ThreadColour = "red" | "white";

export interface DressedTrunk {
  /** Near the authored tree to dress; the trunk itself is measured at load. */
  x: number;
  z: number;
  threads: readonly ThreadColour[];
  /** Blood on the side that faces the path. */
  blood?: "hand" | "drips";
}

/** Real trunks a step or two off the path, from the road to the compound. */
export const DRESSED_TRUNKS: readonly DressedTrunk[] = [
  { x: -10.1, z: 47.8, threads: ["red"] },
  { x: 6.5, z: 44.3, threads: ["white", "red"] },
  { x: -4.2, z: 37.1, threads: ["red"], blood: "drips" },
  { x: 3.7, z: 15.4, threads: ["red", "white"] },
  { x: -3.1, z: 14.9, threads: ["red"], blood: "hand" },
];

/** The fig, right of the path halfway down the walk. */
export const OMEN_FIG = { x: 8.5, z: 29 } as const;

/** Bamboo stakes either side of the path where the forest walk begins; the cord between them. */
export const BOUNDARY_CORD = {
  from: [-4.6, 55.5],
  to: [0.7, 55.2],
  height: 2.15,
} as const;
