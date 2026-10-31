/**
 * Where the forest has been marked (Art Bible 3; Khmer folk belief, advisor
 * review pending): cotton thread wound round the trunks beside the path, as a
 * kru binds what lives in a tree; a web of cords strung over the path where
 * the village ends, hung with hair tassels, ties and cloth effigies, as the
 * title screen shows it; blood on the bark; and the old strangler fig
 * (chrey) a Neak Ta or a preay is said to live in, wrapped in cloth, with a
 * pot and burnt-down incense at its roots. Babylon space, metres.
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

/**
 * The web over the path where the forest walk begins, a few steps from where
 * Sora arrives: bamboo poles either side, cords sagging between them overhead.
 */
export const CORD_WEB = {
  /** [x, z, height] of each pole. */
  poles: [
    [-5.0, 55.8, 4.4],
    [1.3, 55.2, 4.0],
    [3.3, 52.3, 3.5],
    [-5.7, 52.1, 3.7],
  ],
  /** [pole, height up it, pole, height up it, sag]: every cord stays above head height. */
  spans: [
    [0, 4.2, 1, 3.8, 0.55],
    [0, 3.3, 1, 3.1, 0.5],
    [0, 2.6, 1, 2.65, 0.3],
    [0, 4.0, 2, 3.3, 0.5],
    [3, 3.5, 1, 3.7, 0.6],
    [3, 2.7, 2, 3.0, 0.42],
    [0, 3.7, 3, 3.4, 0.25],
    [1, 3.9, 2, 3.4, 0.3],
  ],
  /** [span, how far along it (0–1), drop below the cord]: the first hangs just over the path. */
  effigies: [
    [1, 0.47, 0.32],
    [4, 0.62, 0.75],
    [5, 0.3, 0.17],
  ],
} as const;
