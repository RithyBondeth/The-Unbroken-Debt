/**
 * Tuning values for Sora's first-person movement (Spike S1).
 * Distances in metres, speeds in metres per second, angles in radians.
 */
export interface PlayerConfig {
  /** Capsule while standing. Sora is about 1.62 m tall. */
  standHeight: number;
  standEyeHeight: number;
  /** Capsule while crouched; fits under 1.25 m clearance. */
  crouchHeight: number;
  crouchEyeHeight: number;
  radius: number;

  walkSpeed: number;
  hurrySpeed: number;
  crouchSpeed: number;
  climbSpeed: number;
  /** Ground acceleration towards the wished speed. */
  acceleration: number;
  /** How much steering is possible while airborne (0–1). */
  airControl: number;
  /** Largest hover gap (m) closed by snapping down while grounded. */
  groundSnap: number;

  /**
   * Havok step-up height. 0 relies on the rounded capsule riding over small edges
   * (up to about radius × (1 − cos maxSlope) ≈ 10 cm: thresholds, warped boards).
   * Stairs use a hidden ramp collider instead (Spike S1 finding): Babylon's step-up
   * moves only a few centimetres per frame, so at walking pace it wedges on stair edges.
   */
  maxStepHeight: number;
  /** Steepest walkable slope; the steep back stair is 48.6°. */
  maxSlopeDeg: number;

  /** Seconds the camera takes to follow a step-up, hiding the snap. */
  eyeSmoothing: number;
  /** Seconds to lower or raise the eye when crouching. */
  crouchTransition: number;

  strideWalk: number;
  strideHurry: number;
  strideCrouch: number;
  bobWalk: number;
  bobHurry: number;
  bobCrouch: number;

  /** Noise loudness per footstep (0–1), heard by spirits (TDD section 10.1). */
  noiseWalk: number;
  noiseHurry: number;
  noiseCrouch: number;

  mouseSensitivity: number;
  maxPitch: number;
}

export const DEFAULT_PLAYER_CONFIG: PlayerConfig = {
  standHeight: 1.7,
  standEyeHeight: 1.58,
  crouchHeight: 1.1,
  crouchEyeHeight: 0.98,
  radius: 0.25,

  walkSpeed: 1.6,
  hurrySpeed: 3.4,
  crouchSpeed: 0.9,
  climbSpeed: 1.1,
  acceleration: 14,
  airControl: 0.15,
  groundSnap: 0.2,

  maxStepHeight: 0,
  maxSlopeDeg: 55,

  eyeSmoothing: 0.08,
  crouchTransition: 0.18,

  strideWalk: 0.72,
  strideHurry: 1.1,
  strideCrouch: 0.5,
  bobWalk: 0.022,
  bobHurry: 0.04,
  bobCrouch: 0.012,

  noiseWalk: 0.35,
  noiseHurry: 1,
  noiseCrouch: 0.12,

  mouseSensitivity: 0.0022,
  maxPitch: (85 * Math.PI) / 180,
};
