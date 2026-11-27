import type { Scene } from "@babylonjs/core/scene";
import type { AssetContainer } from "@babylonjs/core/assetContainer";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { StandardMaterial } from "@babylonjs/core/Materials/standardMaterial";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { MocapFigure } from "@/shared/entities/MocapFigure";
import { PREAY_CLIPS } from "../data/preayClips";

/** Her own walking pace (m/s): the walk clip at 1x, as the performer walked it. */
export const PREAY_WALK_SPEED = PREAY_CLIPS.walk.speed;
/** Her hurried, stumbling pace (m/s) at 1x: the hunt under the house. */
export const PREAY_HURRY_SPEED = PREAY_CLIPS.hurry.speed;
/** Height of her eyes behind the hair, above her feet (m), matching her 1.13x gaunt stature. */
export const PREAY_EYE_HEIGHT = 1.66;

const GAIT_EASE = 0.56;
const TURN_WALKING = 2.0;
const TURN_STANDING = 1.15;
const STEP_ROUND = 0.35;
const MAX_RATE = 1.65;
export const PREAY_TOP_SPEED = PREAY_HURRY_SPEED * MAX_RATE;

/** Range (m) within which Preay's cold aura chills & flickers Sora's kerosene lamp. */
export const PREAY_AURA_RANGE = 8.5;

const wrap = (a: number) => {
  while (a > Math.PI) a -= 2 * Math.PI;
  while (a < -Math.PI) a += 2 * Math.PI;
  return a;
};

export interface PreayHorrorState {
  /** Broken-neck sideways tilt in radians (e.g. 0.65 = ~37°, -0.8 = ~-46°). */
  neckTilt?: number;
  /** Unnatural extra yaw twist (e.g. 1.75 rad = 100° over-shoulder stare). */
  overShoulder?: number;
  /** 0–1 forward predatory crouch/hunch. */
  hunch?: number;
  /** 0–1 sudden convulsive head/shoulder twitch burst. */
  twitch?: number;
  /** 0–1 dead-eye pale glint intensity peeking behind wet hair. */
  eyeGlint?: number;
}

/**
 * The Preay of Episode 1 (ខ្មោចព្រាយ) — upgraded for high-end Asian psychological horror:
 *
 * - Drowned corpse-pale wet PBR finish with a cold moonlight rim light that catches soaked
 *   hair, bloodstained cloth, and clawed fingers in near-total darkness.
 * - Faint clouded pale-eye glints tucked behind parted wet hair (never bright cartoons).
 * - Procedural bone distortion on top of CMU mocap: broken-neck tilts, 110° over-shoulder
 *   head twists, predatory spine hunch, and sharp Jacob's-Ladder head/clavicle convulsions.
 * - Cold lamp-choking proximity aura that shrinks and chills Sora's kerosene flame nearby.
 */
export class Preay {
  readonly figure: MocapFigure;
  /** Called on each heel strike with the foot's place, for her bare steps. */
  onStep: ((at: Vector3) => void) | null = null;
  /** The ground she walks on, where the scene knows it. */
  ground: ((x: number, z: number) => number) | null = null;

  private yaw = 0;
  private wantYaw = 0;
  private gait = 0;
  private speed = 0;
  private walkTime = 0;
  private hurryTime = 0;
  private hurry = 0;
  private standTime = 0;
  private look = 0;
  private lookAt: Vector3 | null = null;
  private lastLook: Vector3 | null = null;
  private readonly last = new Vector3();
  private placed = false;
  private override: { clip: string; time: number; loop: boolean } | null = null;

  // Procedural horror posture state (lit strictly by real scene lights — zero fake self-glow)
  private neckTilt = 0;
  private neckTiltTarget = 0;
  private overShoulder = 0;
  private overShoulderTarget = 0;
  private hunch = 0;
  private hunchTarget = 0;
  private twitch = 0;
  private twitchTimer = 0;
  private isSilhouette = false;

  /** Loads her asset once for a scene; give it to `new Preay` for each figure. */
  static load(scene: Scene): Promise<AssetContainer> {
    return MocapFigure.load(scene, `${import.meta.env.BASE_URL}assets/ep1/preay.glb`);
  }

  constructor(asset: AssetContainer, name: string, standOffset = 0) {
    this.figure = new MocapFigure(asset, name);
    // Tall, gaunt horror stature (~1.78 m vs Sora's 1.58 m eye level) so she looms in doorways & rain
    this.figure.root.scaling.setAll(1.13);
    this.standTime = standOffset;
    this.figure.pose("stand", standOffset);
    this.setupHorrorLook(name);
  }

  private setupHorrorLook(name: string): void {
    // Match real monsoon village PBR lighting: zero emissive sticker glow, real specular AA,
    // and restrained night IBL so she naturally blends into shadows until lantern or lightning hits.
    for (const mesh of this.figure.meshes) {
      if (!(mesh.material instanceof PBRMaterial)) continue;
      const mat = mesh.material.clone(`${name}_${mesh.material.name}_photoreal`);
      mat.albedoColor = Color3.White();
      mat.emissiveColor = Color3.Black();
      mat.environmentIntensity = 0.58;
      mat.enableSpecularAntiAliasing = true;
      mat.maxSimultaneousLights = 8;
      if (mat.name.includes("hair_cards")) {
        mat.transparencyMode = PBRMaterial.PBRMATERIAL_ALPHATEST;
        mat.alphaCutOff = 0.34;
        mat.backFaceCulling = false;
      }
      mesh.material = mat;
    }
  }

  get root(): TransformNode {
    return this.figure.root;
  }

  get position(): Vector3 {
    return this.figure.root.position;
  }

  get heading(): number {
    return this.yaw;
  }

  /** Sets procedural horror distortion targets (broken-neck tilt, hunch, twitch). */
  setHorror(state: PreayHorrorState): void {
    if (state.neckTilt !== undefined) this.neckTiltTarget = state.neckTilt;
    if (state.overShoulder !== undefined) this.overShoulderTarget = state.overShoulder;
    if (state.hunch !== undefined) this.hunchTarget = state.hunch;
    if (state.twitch !== undefined) this.twitch = Math.max(0, Math.min(1, state.twitch));
  }

  /** Fires a brief violent head/shoulder convulsion shudder lasting `seconds`. */
  triggerTwitch(strength = 1, seconds = 0.34): void {
    this.twitch = Math.max(this.twitch, Math.min(1, strength));
    this.twitchTimer = Math.max(this.twitchTimer, seconds);
  }

  /**
   * Instantaneously places her in a twisted strobe posture (for lightning / bulb flicker jumps).
   */
  strobePose(at: Vector3, yaw: number, neckTilt: number, clip?: string, clipTime = 0): void {
    this.place(at, yaw);
    this.neckTilt = this.neckTiltTarget = neckTilt;
    this.overShoulder = this.overShoulderTarget = 0;
    if (clip) this.perform(clip, clipTime, false);
    this.setEnabled(true);
    this.standStill(0);
  }

  /**
   * 0–1 cold presence aura felt by Sora's lamp & atmosphere when Preay is enabled and nearby.
   */
  proximityChill(eye: Vector3): number {
    if (!this.isEnabled() || this.isSilhouette) return 0;
    const d = Vector3.Distance(this.position, eye);
    if (d >= PREAY_AURA_RANGE) return 0;
    const t = 1 - d / PREAY_AURA_RANGE;
    return t * t;
  }

  /** Shows her as a flat black shape (a shadow thrown on cloth/wall), not as herself. */
  silhouette(alpha: number): void {
    this.isSilhouette = true;
    const scene = this.figure.root.getScene();
    const ink = new StandardMaterial(`${this.figure.root.name}_silhouette`, scene);
    ink.disableLighting = true;
    ink.diffuseColor = Color3.Black();
    ink.emissiveColor = Color3.Black();
    ink.specularColor = Color3.Black();
    ink.alpha = alpha;
    ink.backFaceCulling = false;
    for (const mesh of this.figure.meshes) {
      mesh.material = ink;
      mesh.receiveShadows = false;
    }
  }

  /** Puts her somewhere, facing `yaw` (radians; 0 faces +Z), standing still. */
  place(at: Vector3, yaw: number): void {
    this.figure.root.position.copyFrom(at);
    this.last.copyFrom(at);
    this.yaw = this.wantYaw = yaw;
    this.gait = 0;
    this.speed = 0;
    this.placed = true;
    this.override = null;
  }

  /** Turns her (over time) to face a point. */
  face(point: Vector3): void {
    const p = this.figure.root.position;
    if (Math.hypot(point.x - p.x, point.z - p.z) > 0.05)
      this.wantYaw = Math.atan2(point.x - p.x, point.z - p.z);
  }

  /** Her head turns to a point (or back, with null). */
  watch(point: Vector3 | null): void {
    this.lookAt = point ? (this.lookAt ?? new Vector3()).copyFrom(point) : null;
  }

  /** Holds one clip instead of standing or walking, until `release`. */
  perform(clip: string, time: number, loop = false): void {
    this.override = { clip, time, loop };
  }

  release(): void {
    this.override = null;
  }

  /** Follows a point moved by a brain; automatically leans into predatory horror posture when hurrying. */
  follow(dt: number, at: Vector3, direction?: Vector3, move = true): void {
    const p = this.figure.root.position;
    if (!this.placed || Math.hypot(at.x - this.last.x, at.z - this.last.z) > 1.5) {
      const yaw = !this.placed && direction ? Math.atan2(direction.x, direction.z) : this.yaw;
      this.place(move ? at : Vector3.Zero(), yaw);
      this.last.copyFrom(at);
    }
    const dx = at.x - this.last.x;
    const dz = at.z - this.last.z;
    const moved = Math.hypot(dx, dz);
    const pace = dt > 0 ? Math.min(moved / dt, PREAY_TOP_SPEED) : 0;
    this.speed += (pace - this.speed) * (1 - Math.exp(-dt * 8));
    if (move) p.copyFrom(at);
    this.last.copyFrom(at);
    if (direction && Math.hypot(direction.x, direction.z) > 1e-4)
      this.wantYaw = Math.atan2(direction.x, direction.z);
    else if (moved > 1e-4) this.wantYaw = Math.atan2(dx, dz);

    // Predatory broken-neck & hunch automatically intensify during active chases
    if (this.speed > PREAY_WALK_SPEED * 1.15) {
      this.hunchTarget = Math.max(this.hunchTarget, 0.65);
      if (Math.abs(this.neckTiltTarget) < 0.1) this.neckTiltTarget = 0.42;
      if (this.twitchTimer <= 0 && Math.random() < dt * 0.45) this.triggerTwitch(0.75, 0.28);
    }
    this.step(dt);
  }

  /** Walks her towards `target` at her own pace. Returns true once she is there. */
  walkTowards(dt: number, target: Vector3, pace = 1): boolean {
    const p = this.figure.root.position;
    const dx = target.x - p.x;
    const dz = target.z - p.z;
    const left = Math.hypot(dx, dz);
    if (left < 0.05) {
      this.standStill(dt);
      return true;
    }
    this.wantYaw = Math.atan2(dx, dz);
    const facing = Math.cos(wrap(this.wantYaw - this.yaw));
    const goal = PREAY_WALK_SPEED * Math.min(MAX_RATE, pace) * Math.max(0, facing) * this.gait;
    this.speed += (goal - this.speed) * (1 - Math.exp(-dt * 5));
    const step = Math.min(left, this.speed * dt);
    p.x += Math.sin(this.yaw) * step;
    p.z += Math.cos(this.yaw) * step;
    const floor = this.ground ? this.ground(p.x, p.z) : target.y;
    p.y += (floor - p.y) * (1 - Math.exp(-dt * 6));
    this.last.copyFrom(p);
    this.step(dt, true);
    return false;
  }

  /** Stands in place breathing, applying procedural horror distortions. */
  standStill(dt: number): void {
    this.speed += (0 - this.speed) * (1 - Math.exp(-dt * 6));
    this.last.copyFrom(this.figure.root.position);
    this.step(dt);
  }

  setPresence(value: number): void {
    const v = Math.max(0, Math.min(1, value));
    for (const mesh of this.figure.meshes) mesh.visibility = v;
    this.setEnabled(v > 0.01);
  }

  setEnabled(on: boolean): void {
    this.figure.setEnabled(on);
  }

  isEnabled(): boolean {
    return this.figure.root.isEnabled();
  }

  dispose(): void {
    this.figure.dispose();
  }

  private step(dt: number, walking = false): void {
    const turn = wrap(this.wantYaw - this.yaw);
    const moving = this.speed > 0.08 || walking;
    const stepping = !moving && Math.abs(turn) > STEP_ROUND;
    const gaitGoal = moving ? 1 : stepping ? 0.55 : 0;
    this.gait +=
      Math.sign(gaitGoal - this.gait) * Math.min(Math.abs(gaitGoal - this.gait), dt / GAIT_EASE);
    const rate = moving ? TURN_WALKING : stepping ? TURN_STANDING * this.gait : 0.3;
    this.yaw = wrap(this.yaw + Math.sign(turn) * Math.min(Math.abs(turn), rate * dt));

    const low = PREAY_WALK_SPEED * 1.3;
    const high = PREAY_HURRY_SPEED * 1.25;
    const hurryGoal = Math.max(0, Math.min(1, (this.speed - low) / (high - low)));
    this.hurry +=
      Math.sign(hurryGoal - this.hurry) *
      Math.min(Math.abs(hurryGoal - this.hurry), dt / GAIT_EASE);

    const before = this.walkTime;
    const beforeHurry = this.hurryTime;
    const cadence = moving
      ? Math.min(MAX_RATE, this.speed / PREAY_WALK_SPEED)
      : stepping
        ? 0.5
        : this.gait * 0.4;
    this.walkTime += dt * Math.max(cadence, this.gait > 0.05 ? 0.25 : 0);
    this.hurryTime += dt * Math.max(0.5, Math.min(MAX_RATE, this.speed / PREAY_HURRY_SPEED));
    this.standTime += dt;

    // Ease horror bone targets cleanly
    const ease = dt > 0 ? 1 - Math.exp(-dt * 7) : 1;
    this.neckTilt += (this.neckTiltTarget - this.neckTilt) * ease;
    this.overShoulder += (this.overShoulderTarget - this.overShoulder) * ease;
    this.hunch += (this.hunchTarget - this.hunch) * ease;
    if (this.twitchTimer > 0) {
      this.twitchTimer -= dt;
      if (this.twitchTimer <= 0) this.twitch = 0;
    }

    const root = this.figure.root;
    root.rotationQuaternion = null;
    root.rotation.set(0, this.yaw, 0);
    // Smooth S-curve easing on gait & hurry transitions so start/stop steps flow naturally
    const smoothGait = this.gait * this.gait * (3 - 2 * this.gait);
    const smoothHurry = this.hurry * this.hurry * (3 - 2 * this.hurry);
    if (this.override) this.figure.pose(this.override.clip, this.override.time, this.override.loop);
    else if (smoothHurry > 0.002 && smoothGait > 0.998)
      this.figure.blend("walk", this.walkTime, "hurry", this.hurryTime, smoothHurry);
    else this.figure.blend("stand", this.standTime, "walk", this.walkTime, smoothGait);
    root.computeWorldMatrix(true);

    const target = this.lookAt;
    this.look += ((target ? 1 : 0) - this.look) * (dt > 0 ? 1 - Math.exp(-dt * 2.8) : 1);
    // Allow eerie 115° supernatural head twist when watching Sora
    if (target && this.look > 0.01) this.figure.lookAt(target, this.look * 0.95, 1.95);
    else if (!target && this.look > 0.01 && this.lastLook)
      this.figure.lookAt(this.lastLook, this.look * 0.95, 1.95);
    if (target) (this.lastLook ??= new Vector3()).copyFrom(target);

    this.figure.distortHorror({
      neckRoll: this.neckTilt,
      neckYaw: this.overShoulder,
      hunch: this.hunch,
      twitch: this.twitch,
      walkBlend: this.override ? 0 : smoothGait,
      time: this.standTime,
    });

    if (this.onStep && this.gait > 0.4) {
      if (this.hurry > 0.5) this.strikes("hurry", beforeHurry, this.hurryTime);
      else this.strikes("walk", before, this.walkTime);
    }
  }

  private strikes(clip: "walk" | "hurry", from: number, to: number): void {
    const cycle = PREAY_CLIPS[clip].seconds;
    const a = ((from % cycle) + cycle) % cycle;
    const span = to - from;
    for (const s of PREAY_CLIPS[clip].strikes) {
      let d = s - a;
      if (d < 0) d += cycle;
      if (d <= span) {
        const p = this.figure.root.position;
        this.onStep?.(new Vector3(p.x, p.y + 0.05, p.z));
      }
    }
  }
}
