/**
 * The moment the headless dancer goes (Episode 1 studio, November 2026): every light
 * in Sora's floor dies at once, the oil lamps with the electric ones, and comes back
 * stuttering. Shared by the lights (StudioLights.powerCut) and the sound that goes
 * with it (dancerSounds.blackout), so each snap is heard as the light catches.
 */
export const POWER_CUT = {
  /** Seconds from the cut until the lights hold steady again. */
  length: 1.75,
  /** [seconds after the cut, how much light (0–1)] from then until the next step. */
  steps: [
    [0, 0],
    [1.28, 1],
    [1.36, 0.08],
    [1.47, 0.85],
    [1.55, 0],
    [1.72, 1],
  ] as const satisfies readonly (readonly [number, number])[],
};

/** The light `seconds` after the cut (1 before it starts and once it is over). */
export function powerAt(seconds: number): number {
  if (seconds < 0) return 1;
  let level = 1;
  for (const [at, value] of POWER_CUT.steps) if (seconds >= at) level = value;
  return level;
}
