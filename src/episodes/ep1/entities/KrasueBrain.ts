import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { KRASUE_WINDOWS, type KrasueWindow } from "../data/krasue";

export type KrasueState =
  "away" | "arriving" | "patrol" | "watching" | "charging" | "searching" | "cooldown" | "caught";

/** How far out over the paddies it waits, unseen, and how high. */
const FAR = 34,
  FAR_SIDE = 9,
  FAR_UP = 7;
/** Seconds from the dark to the window: fast, braking hard just outside it. */
export const KRASUE_ARRIVAL = 1.1;
/** Seconds it hangs outside, unseen by Sora, before it gives up and goes. */
const LINGER = 4.5;
/** Seconds after it leaves before it can come back to the windows. */
export const KRASUE_REST = 14;
/** How long Sora must stand at a window before it comes: never the same twice running. */
export const KRASUE_DELAYS = [2.4, 4.6, 3.2, 5.8, 2.9, 4.1] as const;

/**
 * Window ambush. The Krasue keeps far off over the fields, out of sight. When
 * Sora lingers at a kitchen window it swoops in from the dark and brakes just
 * outside, a readable warning; cover genuinely works, and when it loses her it
 * flies away again and is gone.
 */
export class KrasueBrain {
  state: KrasueState = "away";
  window: KrasueWindow = KRASUE_WINDOWS[0];
  readonly position = new Vector3();
  readonly direction = new Vector3(0, 0, 1);
  speed = 0;
  sightings = 0;
  /** How many times it has come to the windows (each one is a scare cue). */
  arrivals = 0;
  suspicion = 0;
  elapsed = 0;
  private lostFor = 0;
  private stateAge = 0;
  private strikeFor = 0;
  private lurk = 0;
  private rest = KRASUE_REST;
  private absentFor = 0;
  private readonly from = new Vector3();

  constructor() {
    this.position.copyFrom(this.farPosition());
  }

  get active(): boolean {
    return ["watching", "charging", "searching", "caught"].includes(this.state);
  }

  /** Out over the fields, beyond the lamp and the fog: not drawn, not heard. */
  get hidden(): boolean {
    return this.state === "away";
  }

  selectWindow(window: KrasueWindow): void {
    if (this.state !== "away" || this.window === window) return;
    this.window = window;
    this.position.copyFrom(this.farPosition());
  }

  /**
   * @param lurking Sora is in the kitchen, looking out of one of its windows.
   */
  update(dt: number, eye: Vector3, seen: boolean, lampOpen = false, lurking = false): void {
    dt = Math.max(0, Math.min(dt, 0.05));
    this.elapsed += dt;
    this.stateAge += dt;
    if (this.state === "caught") return;
    if (this.state === "away") {
      this.rest += dt;
      this.position.copyFrom(this.farPosition());
      // Only once it has rested does standing at the glass start to call it.
      const rested = this.rest >= KRASUE_REST;
      this.lurk = lurking && rested ? this.lurk + dt : Math.max(0, this.lurk - dt * 2);
      if (rested && this.lurk >= KRASUE_DELAYS[this.arrivals % KRASUE_DELAYS.length]) {
        this.arrivals++;
        this.lurk = 0;
        this.suspicion = 0;
        this.from.copyFrom(this.position);
        this.setState("arriving");
      }
      return;
    }
    if (this.state === "arriving") {
      const t = Math.min(1, this.stateAge / KRASUE_ARRIVAL);
      const ease = 1 - (1 - t) ** 3;
      const to = this.patrolPosition();
      // A swoop down out of the sky, not a straight slide.
      const control = to
        .add(this.window.normal.scale(9))
        .addInPlace(this.window.tangent.scale(-3))
        .addInPlaceFromFloats(0, 5, 0);
      const next = Vector3.Lerp(
        Vector3.Lerp(this.from, control, ease),
        Vector3.Lerp(control, to, ease),
        ease,
      );
      const movement = next.subtract(this.position);
      if (movement.lengthSquared() > 0.000001) this.direction.copyFrom(movement).normalize();
      this.position.copyFrom(next);
      if (t >= 1) {
        this.absentFor = 0;
        this.setState("patrol");
      }
      return;
    }
    if (this.state === "cooldown") {
      // It goes the way it came, faster and faster, until the dark has it.
      this.speed = Math.min(22, Math.max(2, this.speed) + dt * 16);
      this.flyTo(this.farPosition(), dt * this.speed);
      if (Vector3.Distance(this.position, this.farPosition()) < 0.5 || this.stateAge > 5)
        this.goAway();
      return;
    }
    if (this.state === "patrol") {
      this.patrol();
      this.suspicion = Math.max(0, this.suspicion + (seen ? dt : -dt * 2));
      this.absentFor = lurking || seen ? 0 : this.absentFor + dt;
      if (this.suspicion >= 0.28) {
        this.sightings++;
        this.setState("watching");
      } else if ((this.stateAge > LINGER && this.suspicion === 0) || this.absentFor > 2.5)
        this.retreat();
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
    this.goAway();
    // A retry or a cutscene never brings it straight back to the glass.
    this.rest = KRASUE_REST * 0.5;
  }

  private goAway(): void {
    this.speed = 0;
    this.rest = 0;
    this.lurk = 0;
    this.setState("away");
    this.position.copyFrom(this.farPosition());
  }

  private retreat(): void {
    this.suspicion = 0;
    this.strikeFor = 0;
    this.speed = 2;
    this.setState("cooldown");
  }

  private patrol(): void {
    const next = this.patrolPosition();
    const movement = next.subtract(this.position);
    if (movement.lengthSquared() > 0.000001) this.direction.copyFrom(movement).normalize();
    this.position.copyFrom(next);
  }

  private farPosition(): Vector3 {
    return this.window.center
      .add(this.window.normal.scale(FAR))
      .addInPlace(this.window.tangent.scale(-FAR_SIDE))
      .addInPlaceFromFloats(0, FAR_UP, 0);
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
