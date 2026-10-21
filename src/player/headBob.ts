/**
 * Head-bob and footstep timing. One stride is two footsteps; the head dips
 * at each footfall and sways once per stride. Pure functions so they can be tested.
 */

export interface StrideState {
  /** Progress through the current stride, 0 to 1. */
  phase: number;
  /** Bob amplitude currently applied, eased towards the target. */
  amplitude: number;
}

export interface StrideResult {
  /** True when a foot landed during this update. */
  stepped: boolean;
}

/**
 * Advances the stride by the distance travelled. Footsteps land at phase 0.5 and 1.0.
 */
export function advanceStride(
  state: StrideState,
  distance: number,
  strideLength: number,
  result: StrideResult,
): StrideResult {
  result.stepped = false;
  if (distance <= 0 || strideLength <= 0) return result;
  const before = state.phase;
  let after = before + distance / strideLength;
  if (before < 0.5 && after >= 0.5) result.stepped = true;
  if (after >= 1) {
    result.stepped = true;
    after %= 1;
  }
  state.phase = after;
  return result;
}

/** Vertical offset of the eye: lowest at each footfall. */
export function bobOffsetY(phase: number, amplitude: number): number {
  // Two dips per stride: cos(4πp) is 1 at footfalls, so the eye is lowest there.
  return -amplitude * 0.5 * Math.cos(4 * Math.PI * phase);
}

/** Sideways sway: one full cycle per stride, smaller than the vertical bob. */
export function bobOffsetX(phase: number, amplitude: number): number {
  return amplitude * 0.5 * Math.sin(2 * Math.PI * phase);
}
