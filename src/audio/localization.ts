/**
 * The S4 pointing test (Development Plan, section 2.2: "eyes closed, you can
 * point to a footstep source"). Angles are yaws in radians as the player
 * controller uses them: 0 looks along +z, positive turns right (towards +x).
 */

export type Panning = "HRTF" | "equalpower";

export interface Trial {
  /** Direction of the source from where the player faces at the start, -π to π. */
  azimuth: number;
  /** Metres from the listener. */
  distance: number;
  panning: Panning;
}

export interface TrialResult extends Trial {
  /** Where the player pointed, relative to where they faced at the start. */
  response: number;
  /** Seconds from the first step to the answer. */
  seconds: number;
}

export interface Summary {
  trials: number;
  medianError: number;
  /** Share of trials answered in the mirror direction (front for back or back for front). */
  frontBackRate: number;
}

/** Wraps an angle to -π…π. */
export function wrapAngle(a: number): number {
  return Math.atan2(Math.sin(a), Math.cos(a));
}

/** Yaw from a listener at (x, z) to a source at (sx, sz), relative to the listener's yaw. */
export function relativeAzimuth(x: number, z: number, yaw: number, sx: number, sz: number): number {
  return wrapAngle(Math.atan2(sx - x, sz - z) - yaw);
}

export function angleError(response: number, azimuth: number): number {
  return Math.abs(wrapAngle(response - azimuth));
}

/**
 * A front/back confusion: the answer is far from the source but close to its
 * mirror image across the line through the ears (the classic spatial audio
 * failure, worst with generic HRTFs and without head movement).
 */
export function isFrontBackConfusion(response: number, azimuth: number): boolean {
  const mirror = wrapAngle(Math.sign(azimuth || 1) * Math.PI - azimuth);
  return (
    angleError(response, azimuth) > Math.PI / 3 &&
    angleError(response, mirror) < angleError(response, azimuth)
  );
}

/**
 * `count` trials with sources spread evenly around the listener (one per
 * sector, jittered), distances 2–8 m, and each panning model used equally,
 * in a shuffled order.
 */
export function makeTrials(count: number, rand: () => number): Trial[] {
  const trials: Trial[] = [];
  for (let i = 0; i < count; i++) {
    const sector = (2 * Math.PI) / count;
    trials.push({
      azimuth: wrapAngle(i * sector + (rand() - 0.5) * sector * 0.8),
      distance: 2 + rand() * 6,
      panning: i % 2 === 0 ? "HRTF" : "equalpower",
    });
  }
  for (let i = trials.length - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1));
    [trials[i], trials[j]] = [trials[j], trials[i]];
  }
  return trials;
}

export function summarize(results: readonly TrialResult[]): Summary {
  const errors = results.map((r) => angleError(r.response, r.azimuth)).sort((a, b) => a - b);
  const mid = errors.length / 2;
  const medianError =
    errors.length === 0
      ? NaN
      : errors.length % 2
        ? errors[Math.floor(mid)]
        : (errors[mid - 1] + errors[mid]) / 2;
  const confusions = results.filter((r) => isFrontBackConfusion(r.response, r.azimuth)).length;
  return {
    trials: results.length,
    medianError,
    frontBackRate: results.length ? confusions / results.length : 0,
  };
}
