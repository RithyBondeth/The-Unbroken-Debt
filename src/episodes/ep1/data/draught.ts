/**
 * The air Sora stirs as she moves (the user, Nov 24, 2026: "candle's light and incense's
 * smoke should have interaction"). A candle she brushes past leans away from her and
 * gutters, its light dipping; incense smoke near her is pushed aside and tears. Standing
 * still close by, her breath barely stirs them. Babylon space, metres, seconds.
 */

/** How far from her feet the air she moves reaches a flame (m, horizontally). */
export const DRAUGHT_RANGE = 1.7;
/** At this speed (m/s) the draught is full: a brisk walk. */
export const DRAUGHT_SPEED = 2.2;
/** How far above or below her middle a flame can be and still feel it (m). */
const REACH_UP = 1.5;

export interface DraughtState {
  /** Her feet. */
  x: number;
  y: number;
  z: number;
  /** Her horizontal velocity (m/s), smoothed. */
  vx: number;
  vz: number;
}

/** 0 (still air) to 1 (she has just swept past it) for a flame or smoke at (x, y, z). */
export function draughtAt(s: DraughtState, x: number, y: number, z: number): number {
  const dy = y - (s.y + 1.0);
  if (Math.abs(dy) > REACH_UP) return 0;
  const d = Math.hypot(x - s.x, z - s.z);
  const near = Math.max(0, 1 - d / DRAUGHT_RANGE);
  if (near <= 0) return 0;
  const speed = Math.min(1, Math.hypot(s.vx, s.vz) / DRAUGHT_SPEED);
  return near * near * (0.15 + 0.85 * speed);
}

/**
 * The way the air at (x, z) is pushed, a unit vector on the ground: away from her and
 * along her motion (she drags the air behind her as she passes).
 */
export function draughtPush(s: DraughtState, x: number, z: number): { x: number; z: number } {
  let ax = x - s.x,
    az = z - s.z;
  const a = Math.hypot(ax, az) || 1;
  ax /= a;
  az /= a;
  const sp = Math.hypot(s.vx, s.vz);
  const mx = sp > 1e-3 ? s.vx / sp : 0,
    mz = sp > 1e-3 ? s.vz / sp : 0;
  const w = Math.min(1, sp / DRAUGHT_SPEED);
  const px = ax * (1 - 0.6 * w) + mx * 0.6 * w,
    pz = az * (1 - 0.6 * w) + mz * 0.6 * w;
  const p = Math.hypot(px, pz) || 1;
  return { x: px / p, z: pz / p };
}

/** Follows her feet each frame, keeping a smoothed velocity. */
export class Draught implements DraughtState {
  x = 0;
  y = -1000;
  z = 0;
  vx = 0;
  vz = 0;
  private primed = false;

  update(dt: number, feet: { x: number; y: number; z: number }): void {
    if (!this.primed || dt <= 0) {
      this.x = feet.x;
      this.y = feet.y;
      this.z = feet.z;
      this.primed = true;
      return;
    }
    const k = Math.min(1, dt * 6);
    this.vx += ((feet.x - this.x) / dt - this.vx) * k;
    this.vz += ((feet.z - this.z) / dt - this.vz) * k;
    // A teleport (a cutscene, a dev jump) is not a gust.
    if (Math.hypot(this.vx, this.vz) > 12) this.vx = this.vz = 0;
    this.x = feet.x;
    this.y = feet.y;
    this.z = feet.z;
  }

  at(x: number, y: number, z: number): number {
    return draughtAt(this, x, y, z);
  }

  push(x: number, z: number): { x: number; z: number } {
    return draughtPush(this, x, z);
  }
}
