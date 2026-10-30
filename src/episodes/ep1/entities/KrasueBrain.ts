import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { KRASUE_WINDOWS, type KrasueWindow } from "../data/krasue";

export type KrasueState = "patrol" | "watching" | "charging" | "searching" | "cooldown" | "caught";

/** Window ambush: a readable warning, physical flight, and cover that genuinely works. */
export class KrasueBrain {
  state: KrasueState = "patrol";
  window: KrasueWindow = KRASUE_WINDOWS[0];
  readonly position = new Vector3(8.5, 3.96, -13);
  readonly direction = new Vector3(0, 0, 1);
  speed = 0;
  sightings = 0;
  suspicion = 0;
  elapsed = 0;
  private lostFor = 0;
  private stateAge = 0;
  private strikeFor = 0;

  get active(): boolean {
    return ["watching", "charging", "searching", "caught"].includes(this.state);
  }

  selectWindow(window: KrasueWindow): void {
    if (this.active || this.window === window) return;
    this.window = window;
    this.patrol();
  }

  update(dt: number, eye: Vector3, seen: boolean, lampOpen = false): void {
    dt = Math.max(0, Math.min(dt, 0.05));
    this.elapsed += dt;
    this.stateAge += dt;
    if (this.state === "caught") return;
    if (this.state === "cooldown") {
      if (this.stateAge > 6) this.setState("patrol");
      this.flyTo(this.patrolPosition(), dt * 1.2);
      return;
    }
    if (this.state === "patrol") {
      this.patrol();
      this.suspicion = Math.max(0, this.suspicion + (seen ? dt : -dt * 2));
      if (this.suspicion >= 0.28) {
        this.sightings++;
        this.setState("watching");
      }
      return;
    }
    this.lostFor = seen ? 0 : this.lostFor + dt;
    if (this.state === "watching") {
      if (!seen) {
        this.suspicion = Math.max(0, this.suspicion - dt * 1.6);
        if (this.suspicion === 0) this.retreat();
      } else {
        this.suspicion += dt * (lampOpen ? 1.35 : 1);
        if (this.stateAge >= (lampOpen ? 0.26 : 0.38)) {
          this.speed = 0.8;
          this.setState("charging");
        }
      }
      return;
    }
    if (this.state === "charging") {
      // The entire creature remains outside. The final strike reaches an exposed
      // player through the aperture; the wall still blocks the lethal sight test.
      const strike = this.window.center.add(this.window.normal.scale(0.75));
      strike.y = Math.max(3.4, Math.min(4.08, eye.y));
      this.speed = Math.min(6.2, this.speed + dt * 13);
      if (seen) this.flyTo(strike, dt * this.speed);
      this.strikeFor =
        seen && Vector3.Distance(this.position, strike) < 0.07 ? this.strikeFor + dt : 0;
      if (this.strikeFor > 0.24) this.setState("caught");
      else if (this.lostFor > 0.22) this.setState("searching");
      return;
    }
    if (this.state === "searching") {
      if (seen) this.setState("charging");
      else if (this.stateAge > 2.6) this.retreat();
    }
  }

  reset(): void {
    this.suspicion = 0;
    this.lostFor = 0;
    this.strikeFor = 0;
    this.speed = 0;
    this.setState("patrol");
    this.patrol();
  }

  private retreat(): void {
    this.suspicion = 0;
    this.strikeFor = 0;
    this.setState("cooldown");
  }

  private patrol(): void {
    const next = this.patrolPosition();
    const movement = next.subtract(this.position);
    if (movement.lengthSquared() > 0.000001) this.direction.copyFrom(movement).normalize();
    this.position.copyFrom(next);
  }

  private patrolPosition(): Vector3 {
    const p = this.window.center
      .add(this.window.normal.scale(2.8 + Math.sin(this.elapsed * 0.45) * 0.85))
      .addInPlace(this.window.tangent.scale(Math.sin(this.elapsed * 0.58) * 1.05));
    p.y += 0.04 + Math.sin(this.elapsed * 1.17) * 0.22;
    return p;
  }

  private flyTo(target: Vector3, distance: number): void {
    const delta = target.subtract(this.position);
    if (delta.lengthSquared() > 0.000001) this.direction.copyFrom(delta).normalize();
    this.position.addInPlace(delta.scale(Math.min(1, distance / Math.max(0.001, delta.length()))));
  }

  private setState(state: KrasueState): void {
    this.state = state;
    this.stateAge = 0;
  }
}
