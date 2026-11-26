/**
 * The moment after the altar falls (Episode 1 studio, November 2026): every light in
 * Sora's floor dies at once, the oil lamps with the electric ones, and comes back
 * stuttering. Shared by the lights (StudioLights.powerCut) and the sounds that go with
 * it (studioSounds.powerDown and powerUp), so each snap is heard as the light catches.
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

/** Where the lights start coming back (studioSounds.powerUp is played from here). */
export const POWER_RETURN = 1.2;
/** Seconds from POWER_RETURN until the lights hold steady. */
export const POWER_RETURN_LENGTH = POWER_CUT.length - POWER_RETURN;

/** The light `seconds` after the cut (1 before it starts and once it is over). */
export function powerAt(seconds: number): number {
  if (seconds < 0) return 1;
  let level = 1;
  for (const [at, value] of POWER_CUT.steps) if (seconds >= at) level = value;
  return level;
}
