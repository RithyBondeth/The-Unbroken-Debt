import type { Vec2 } from "./movement";

/**
 * Keeps the first-person camera exactly still while Sora stands still.
 *
 * Babylon decides whether the camera moved by comparing its position and
 * rotation with the last frame's for exact equality, and TAA only blends its
 * history on frames where the camera has not moved. At rest the camera was never
 * exactly still: the Havok capsule settles by fractions of a millimetre every
 * frame, and the eye-height, crouch and head-bob smoothing only ever approach
 * their targets. TAA then switched between its blended image and the raw,
 * sub-pixel jittered frame every few frames, and the whole picture shimmered and
 * shook while the player touched nothing (November 2026). Pure functions, for tests.
 */

/** Horizontal drift (m) ignored while standing still: below what the eye can see at 1.6 m. */
export const REST_DEADBAND = 0.004;

/**
 * Moves `anchor` towards (x, z) only as far as needed to keep it within `band`.
 * Jitter inside the band leaves the anchor (and so the camera) untouched; a real
 * push or a slide is followed smoothly, `band` behind.
 */
export function followWithin(anchor: Vec2, x: number, z: number, band: number): Vec2 {
  const dx = x - anchor.x;
  const dz = z - anchor.z;
  const distance = Math.hypot(dx, dz);
  if (distance <= band) return anchor;
  const t = 1 - band / distance;
  anchor.x += dx * t;
  anchor.z += dz * t;
  return anchor;
}

/**
 * Exponential approach that lands exactly on the target once within `epsilon`,
 * so a smoothed value stops changing instead of creeping forever.
 */
export function approachExactly(
  current: number,
  target: number,
  factor: number,
  epsilon: number,
): number {
  const next = current + (target - current) * factor;
  return Math.abs(target - next) < epsilon ? target : next;
}

/**
 * Vertical counterpart of `followWithin` for the eye height: while at rest,
 * a change smaller than `band` is ignored; anything larger is smoothed as usual.
 */
export function settleEye(
  current: number,
  target: number,
  factor: number,
  band: number,
  atRest: boolean,
): number {
  if (atRest && Math.abs(target - current) < band) return current;
  return current + (target - current) * factor;
}
