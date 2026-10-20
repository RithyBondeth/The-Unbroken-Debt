import type { PlayerConfig } from "./PlayerConfig";

/** Movement intent for one frame, from the keyboard, a gamepad or a test bot. */
export interface MoveIntent {
  /** Strafe, -1 (left) to 1 (right). */
  x: number;
  /** Forward, -1 (back) to 1 (forward). */
  z: number;
  hurry: boolean;
  crouch: boolean;
}

export type Stance = "stand" | "crouch";

export interface Vec2 {
  x: number;
  z: number;
}

/** Ground speed for the current stance. Hurrying is ignored while crouched. */
export function targetSpeed(stance: Stance, hurry: boolean, config: PlayerConfig): number {
  if (stance === "crouch") return config.crouchSpeed;
  return hurry ? config.hurrySpeed : config.walkSpeed;
}

/**
 * Converts input into a world-space horizontal velocity. Diagonals are not
 * faster than straight lines; partial stick input gives partial speed.
 * Babylon is left-handed: yaw 0 looks along +Z, positive yaw turns towards +X.
 */
export function wishVelocity(intent: MoveIntent, yaw: number, speed: number, out: Vec2): Vec2 {
  let x = intent.x;
  let z = intent.z;
  const length = Math.hypot(x, z);
  if (length > 1) {
    x /= length;
    z /= length;
  }
  const sin = Math.sin(yaw);
  const cos = Math.cos(yaw);
  out.x = (x * cos + z * sin) * speed;
  out.z = (z * cos - x * sin) * speed;
  return out;
}

/** Moves `current` towards `target` by at most `maxDelta` (per axis pair, as a vector). */
export function approach(current: Vec2, target: Vec2, maxDelta: number, out: Vec2): Vec2 {
  const dx = target.x - current.x;
  const dz = target.z - current.z;
  const distance = Math.hypot(dx, dz);
  if (distance <= maxDelta || distance === 0) {
    out.x = target.x;
    out.z = target.z;
  } else {
    const t = maxDelta / distance;
    out.x = current.x + dx * t;
    out.z = current.z + dz * t;
  }
  return out;
}

/** Frame-rate independent exponential smoothing factor for a time constant in seconds. */
export function smoothingFactor(dt: number, timeConstant: number): number {
  if (timeConstant <= 0) return 1;
  return 1 - Math.exp(-dt / timeConstant);
}
