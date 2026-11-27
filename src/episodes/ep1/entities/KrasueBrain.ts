import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { KRASUE_PADDY_PATHS, type PaddyFlightPath } from "../data/krasue";

export type KrasueState = "dormant" | "drifting" | "alert" | "approaching" | "pass" | "retreating";

/** Seconds between autonomous rice-field appearances (calm dread, never constant spam). */
export const KRASUE_DORMANT_MIN = 28;
export const KRASUE_DORMANT_MAX = 58;
/** Seconds of first sighting delay once Sora enters the village road/fields. */
export const KRASUE_FIRST_WAIT = 14;
/** Range (m) within which an open kerosene lamp or staring disturbs the Krasue. */
export const KRASUE_DISTURB_RANGE = 34;
/** Distance (m) at which an unchecked approaching Krasue sweeps past and snuffs Sora's lamp. */
export const KRASUE_PASS_RANGE = 4.4;

/**
 * Pure state machine for the redesigned Rice-Field Krasue (អាប).
 *
 * At periodic night moments it glides slowly over the flooded rice paddies pulsing with
 * a bioluminescent emerald-green or blood-red organ light. Watching it from afar is pure
 * atmospheric dread; keeping an open kerosene lamp exposed nearby agitates it (glow turns
 * blood-red and it banks steadily closer). Extinguishing the lamp (`F`) or taking cover
 * calms it so it retreats into the palms. Ignoring the red warning leads to a terrifying
 * close-range fly-by shriek that blows out Sora's lamp.
 */
export class KrasueBrain {
  state: KrasueState = "dormant";
  path: PaddyFlightPath = KRASUE_PADDY_PATHS[0];
  readonly position = new Vector3(38, 4.5, 36);
  readonly direction = new Vector3(-1, 0, -0.3);
  elapsed = 0;
  /** 0 = emerald-green calm drift, 1 = deep blood-red alerted/hunting. */
  redness = 0;
  /** 0–1 agitation driven by Sora's open lamp and direct gaze while exposed. */
  agitation = 0;
  /** Incremented each time it shifts into blood-red alert (triggers audio cue). */
  alerts = 0;
  /** Incremented each time a close pass hits Sora (snuffs lamp + jolt). */
  passes = 0;
  /** Incremented each time a new rice-field appearance starts. */
  sightings = 0;

  private stateAge = 0;
  private waitRemaining = KRASUE_FIRST_WAIT;
  private pathIndex = 0;
  private waypoint = 0;
  private speed = 2.4;
  private readonly passTarget = new Vector3();

  get hidden(): boolean {
    return this.state === "dormant";
  }

  get active(): boolean {
    return this.state === "alert" || this.state === "approaching" || this.state === "pass";
  }

  /** Forces an immediate rice-field appearance along `index` (e.g. story beat or QA). */
  summon(pathIndex?: number): void {
    const idx =
      pathIndex !== undefined
        ? ((pathIndex % KRASUE_PADDY_PATHS.length) + KRASUE_PADDY_PATHS.length) %
          KRASUE_PADDY_PATHS.length
        : this.pathIndex++ % KRASUE_PADDY_PATHS.length;
    this.path = KRASUE_PADDY_PATHS[idx];
    this.waypoint = 1;
    this.position.copyFrom(this.path.waypoints[0]);
    this.redness = this.path.baseRedness;
    this.agitation = 0;
    this.speed = 2.3;
    this.sightings++;
    this.setState("drifting");
  }

  update(
    dt: number,
    playerEye: Vector3,
    playerLookingAtKrasue: boolean,
    lampOpen: boolean,
    playerExposed: boolean,
  ): void {
    dt = Math.max(0, Math.min(dt, 0.05));
    this.elapsed += dt;
    this.stateAge += dt;

    if (this.state === "dormant") {
      // Only tick down the sighting wait while Sora is near the south/yard area or outdoors
      if (playerExposed || playerEye.z > -20) this.waitRemaining -= dt;
      if (this.waitRemaining <= 0) this.summon();
      return;
    }

    const dist = Vector3.Distance(this.position, playerEye);
    const disturbed =
      playerExposed &&
      dist < KRASUE_DISTURB_RANGE &&
      ((lampOpen && (playerLookingAtKrasue || dist < 21)) || (playerLookingAtKrasue && dist < 17));

    if (this.state === "drifting") {
      const target = this.path.waypoints[this.waypoint];
      this.flyTo(target, dt * 2.45);
      // Dip slightly over rice plots like feeding above water
      this.position.y += Math.sin(this.elapsed * 0.9) * 0.14 * dt;

      if (disturbed) {
        this.agitation = Math.min(1, this.agitation + dt * (lampOpen ? 0.38 : 0.2));
      } else {
        this.agitation = Math.max(0, this.agitation - dt * 0.28);
      }

      const wantRed = Math.max(this.path.baseRedness, this.agitation);
      this.redness += (wantRed - this.redness) * Math.min(1, dt * 2.2);

      if (this.agitation >= 0.65) {
        this.alerts++;
        this.setState("alert");
        return;
      }

      if (Vector3.Distance(this.position, target) < 1.1) {
        this.waypoint++;
        if (this.waypoint >= this.path.waypoints.length) {
          this.beginRetreat();
        }
      }
      return;
    }

    if (this.state === "alert") {
      // Hovers and turns its glowing red viscera toward Sora as a clear readable warning
      this.redness += (1 - this.redness) * Math.min(1, dt * 4.5);
      const toSora = playerEye.subtract(this.position);
      if (toSora.lengthSquared() > 1e-4) this.direction.copyFrom(toSora).normalize();
      if (!disturbed && !lampOpen) {
        this.agitation = Math.max(0, this.agitation - dt * 0.65);
        if (this.agitation <= 0.15) {
          this.beginRetreat();
          return;
        }
      }
      if (this.stateAge >= 1.9) {
        this.speed = 3.2;
        this.setState("approaching");
      }
      return;
    }

    if (this.state === "approaching") {
      this.redness += (1 - this.redness) * Math.min(1, dt * 5);
      if (!playerExposed || (!lampOpen && !playerLookingAtKrasue)) {
        this.agitation = Math.max(0, this.agitation - dt * 0.55);
        if (this.agitation <= 0.12 || !playerExposed) {
          this.beginRetreat();
          return;
        }
      } else {
        this.agitation = Math.min(1, this.agitation + dt * 0.3);
      }

      this.speed = Math.min(6.4, this.speed + dt * 1.4);
      const goal = playerEye.add(new Vector3(0, 0.35, 0));
      this.flyTo(goal, dt * this.speed);
      if (Vector3.Distance(this.position, playerEye) <= KRASUE_PASS_RANGE) {
        this.passes++;
        const away = this.direction.clone();
        away.y = 0.25;
        away.normalize();
        this.passTarget.copyFrom(playerEye).addInPlace(away.scale(22));
        this.passTarget.y = playerEye.y + 4.5;
        this.setState("pass");
      }
      return;
    }

    if (this.state === "pass") {
      // Sweeps swiftly past Sora's face and banks up into the storm clouds
      this.redness = 1;
      this.flyTo(this.passTarget, dt * 11.5);
      if (this.stateAge >= 2.2) {
        this.beginRetreat();
      }
      return;
    }

    if (this.state === "retreating") {
      const exit = this.path.waypoints[this.path.waypoints.length - 1].add(new Vector3(0, 4.5, 0));
      this.redness += (this.path.baseRedness * 0.5 - this.redness) * Math.min(1, dt * 1.5);
      this.speed = Math.min(9.5, Math.max(3.5, this.speed + dt * 3));
      this.flyTo(exit, dt * this.speed);
      if (Vector3.Distance(this.position, exit) < 1.8 || this.stateAge >= 6.5) {
        this.goDormant();
      }
    }
  }

  reset(): void {
    this.agitation = 0;
    this.redness = 0;
    this.goDormant(KRASUE_DORMANT_MIN * 0.8);
  }

  private beginRetreat(): void {
    this.agitation = 0;
    this.speed = 4.0;
    this.setState("retreating");
  }

  private goDormant(customWait?: number): void {
    this.setState("dormant");
    const span = KRASUE_DORMANT_MAX - KRASUE_DORMANT_MIN;
    const pseudo = Math.abs(Math.sin(this.elapsed * 1.37 + this.sightings * 2.13));
    this.waitRemaining = customWait ?? KRASUE_DORMANT_MIN + pseudo * span;
  }

  private flyTo(target: Vector3, distance: number): void {
    const delta = target.subtract(this.position);
    const len = delta.length();
    if (len > 1e-4) this.direction.copyFrom(delta).scaleInPlace(1 / len);
    this.position.addInPlace(delta.scale(Math.min(1, distance / Math.max(0.001, len))));
  }

  private setState(next: KrasueState): void {
    this.state = next;
    this.stateAge = 0;
  }
}
