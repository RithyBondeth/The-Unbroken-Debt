import type { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { InputSource } from "../../player/InputSource";
import type { MoveIntent } from "../../player/movement";
import type { Waypoint } from "./course";

export interface BotTarget {
  readonly feet: Vector3;
  readonly yaw: number;
}

export interface BotReport {
  finished: boolean;
  seconds: number;
  stuckAt: number[];
}

/**
 * Walks the course automatically by steering towards each waypoint, so the
 * controller can be tested the same way every time (and without a person).
 */
export class WaypointBot implements InputSource {
  index = 0;
  elapsed = 0;
  private waypointTime = 0;
  /** Time allowed for the current waypoint, set from its distance when it starts. */
  private budget = -1;
  private readonly stuckAt: number[] = [];
  private target: BotTarget | null = null;
  private lastTime = performance.now();

  constructor(
    private readonly route: readonly Waypoint[],
    private readonly onDone: (report: BotReport) => void,
  ) {}

  attach(target: BotTarget): void {
    this.target = target;
  }

  get done(): boolean {
    return this.index >= this.route.length;
  }

  readMove(out: MoveIntent): MoveIntent {
    out.x = 0;
    out.z = 0;
    out.hurry = false;
    out.crouch = false;
    const wp = this.route[this.index];
    if (!wp || !this.target) return out;

    const now = performance.now();
    const dt = Math.min((now - this.lastTime) / 1000, 0.1);
    this.lastTime = now;
    this.elapsed += dt;
    this.waypointTime += dt;

    const feet = this.target.feet;
    const dx = wp.x - feet.x;
    const dz = wp.z - feet.z;
    const distance = Math.hypot(dx, dz);
    const heightOk = wp.y === undefined || Math.abs(feet.y - wp.y) < 0.3;

    if (distance < 0.35 && heightOk) {
      this.advance();
      return out;
    }
    // Give up on a waypoint after a generous time (from its starting distance) and record where.
    if (this.budget < 0) this.budget = 4 + distance * 2;
    if (this.waypointTime > this.budget) {
      this.stuckAt.push(this.index);
      this.advance();
      return out;
    }

    out.z = distance < 0.35 ? 0.6 : 1;
    out.hurry = wp.hurry ?? false;
    out.crouch = wp.crouch ?? false;
    return out;
  }

  consumeLook(out: { yaw: number; pitch: number }): void {
    out.yaw = 0;
    out.pitch = 0;
    const wp = this.route[this.index];
    if (!wp || !this.target) return;
    const feet = this.target.feet;
    const desired = Math.atan2(wp.x - feet.x, wp.z - feet.z);
    let delta = desired - this.target.yaw;
    delta = Math.atan2(Math.sin(delta), Math.cos(delta));
    // Turn smoothly, at most about 4 radians per second at 60 fps.
    out.yaw = Math.max(-0.07, Math.min(0.07, delta));
  }

  dispose(): void {}

  private advance(): void {
    this.index++;
    this.waypointTime = 0;
    this.budget = -1;
    if (this.done) {
      this.onDone({
        finished: this.stuckAt.length === 0,
        seconds: this.elapsed,
        stuckAt: [...this.stuckAt],
      });
    }
  }
}
