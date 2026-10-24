import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import {
  doorwayPath,
  hearingRadius,
  throughDoorways,
  WALKER_CATCH_DISTANCE,
  WALKER_ROUTE,
  WALKER_SPEED,
} from "../data/walker";

export type WalkerState = "idle" | "walking" | "investigating" | "caught" | "complete";

/** Blind, deterministic threat. Sound can interrupt its route; no camera / lamp sight test. */
export class WalkerBrain {
  state: WalkerState = "idle";
  readonly position = WALKER_ROUTE[0].at.clone();
  direction = new Vector3(0, 0, -1);
  elapsed = 0;
  private routeIndex = 1;
  private pause = 0;
  private detour: Vector3[] = [];
  private resume: Vector3 | null = null;
  private returning = false;

  get active(): boolean {
    return this.state === "walking" || this.state === "investigating";
  }
  get waiting(): boolean {
    return this.pause > 0;
  }

  start(): void {
    this.position.copyFrom(WALKER_ROUTE[0].at);
    this.routeIndex = 1;
    this.pause = 0;
    this.detour = [];
    this.resume = null;
    this.returning = false;
    this.elapsed = 0;
    this.state = "walking";
  }

  reset(): void {
    this.state = "idle";
    this.detour = [];
    this.pause = 0;
  }

  hear(at: Vector3, loudness: number, concealed: boolean): boolean {
    if (
      !this.active ||
      concealed ||
      Math.abs(at.y - this.position.y) > 1.2 ||
      Vector3.Distance(at, this.position) > hearingRadius(loudness)
    )
      return false;
    if (at.y < 2 || at.z < -18 || at.z > -10.5) return false;
    if (this.state === "investigating") return false;
    this.resume = this.position.clone();
    this.returning = false;
    this.pause = 0;
    this.detour = doorwayPath(this.position, at);
    this.state = "investigating";
    return true;
  }

  update(dt: number, sora: Vector3, concealed: boolean): void {
    // Small substeps preserve contact and the four-second pause across test / frame sizes.
    let remaining = Math.max(0, dt);
    while (remaining > 0 && this.active) {
      const step = Math.min(remaining, 0.05);
      remaining -= step;
      this.elapsed += step;
      if (this.contact(sora, concealed)) {
        this.state = "caught";
        return;
      }
      if (this.pause > 0) {
        this.pause = Math.max(0, this.pause - step);
        continue;
      }
      const target =
        this.state === "investigating" ? this.detour[0] : WALKER_ROUTE[this.routeIndex]?.at;
      if (!target) {
        this.state = "complete";
        return;
      }
      const delta = target.subtract(this.position),
        distance = delta.length();
      if (distance > 0.0001) {
        this.direction.copyFrom(delta).normalize();
        this.position.addInPlace(delta.scale(Math.min(1, (step * WALKER_SPEED) / distance)));
      }
      if (distance <= step * WALKER_SPEED + 0.0001) this.arrive();
      if (this.contact(sora, concealed)) {
        this.state = "caught";
        return;
      }
    }
  }

  private contact(sora: Vector3, concealed: boolean): boolean {
    return (
      Math.abs(sora.y - this.position.y) < 1 &&
      throughDoorways(this.position, sora) &&
      Vector3.Distance(this.position, sora) < (concealed ? 0.43 : WALKER_CATCH_DISTANCE)
    );
  }

  private arrive(): void {
    if (this.state === "investigating") {
      this.detour.shift();
      if (this.detour.length) return;
      if (!this.returning && this.resume) {
        this.pause = 2;
        this.detour = doorwayPath(this.position, this.resume);
        this.returning = true;
      } else {
        this.state = "walking";
        this.resume = null;
      }
    } else {
      this.pause = WALKER_ROUTE[this.routeIndex].pause ?? 0;
      this.routeIndex++;
      if (this.routeIndex >= WALKER_ROUTE.length) this.state = "complete";
    }
  }
}
