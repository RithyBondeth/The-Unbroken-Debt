import type { Scene } from "@babylonjs/core/scene";
import type { AssetContainer } from "@babylonjs/core/assetContainer";
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
/** Height of her eyes behind the hair, above her feet (m). */
export const PREAY_EYE_HEIGHT = 1.47;

/** Seconds to ease from standing into the walk and back. */
const GAIT_EASE = 0.45;
/** How fast she can turn (rad/s): walking, and stepping round where she stands. */
const TURN_WALKING = 1.9;
const TURN_STANDING = 1.15;
/** A turn bigger than this (rad), standing, is made in steps rather than on the spot. */
const STEP_ROUND = 0.35;
/** The fastest a clip is ever played: past this her feet would visibly hurry. */
const MAX_RATE = 1.6;
/** The fastest she ever goes (m/s): her stumbling hurry, played as fast as it can be. */
export const PREAY_TOP_SPEED = PREAY_HURRY_SPEED * MAX_RATE;

const wrap = (a: number) => {
  while (a > Math.PI) a -= 2 * Math.PI;
  while (a < -Math.PI) a += 2 * Math.PI;
  return a;
};

/**
 * The Preay of Episode 1 (ខ្មោចព្រាយ): a woman's ghost in a bloodied white dress, her long
 * hair over her face; the user's Sketchfab scan ("Horror Ghost Character - Blood Stained
 * Spirit" by adhamasalah, CC BY 4.0), rigged and moving on CMU motion capture
 * (tools/characters/build-preay.py).
 *
 * She moves as a person does: she stands breathing, eases into a walk at her own pace
 * (the clip plays at the speed she actually covers ground, so her feet never slide),
 * turns no faster than a person can, stepping round when she turns where she stands,
 * and her head comes round to whatever she is looking at. Drive her either from a brain
 * that moves a point (`follow`) or with `walkTowards` / `standStill`; call one of them
 * every frame she is shown.
 */
export class Preay {
  readonly figure: MocapFigure;
  /** Called on each heel strike with the foot's place, for her bare steps. */
  onStep: ((at: Vector3) => void) | null = null;
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
  /** Where she last looked, so her head eases back from it rather than snapping. */
  private lastLook: Vector3 | null = null;
  private readonly last = new Vector3();
  private placed = false;
  private override: { clip: string; time: number; loop: boolean } | null = null;

  /** Loads her asset once for a scene; give it to `new Preay` for each figure. */
  static load(scene: Scene): Promise<AssetContainer> {
    return MocapFigure.load(scene, `${import.meta.env.BASE_URL}assets/ep1/preay.glb`);
  }

  constructor(asset: AssetContainer, name: string, standOffset = 0) {
    this.figure = new MocapFigure(asset, name);
    this.standTime = standOffset;
    this.figure.pose("stand", standOffset);
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

  /** Shows her as a flat black shape (a shadow thrown on cloth), not as herself. */
  silhouette(alpha: number): void {
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

  /** Her head turns to a point (or back, with null), as far as a neck goes. */
  watch(point: Vector3 | null): void {
    this.lookAt = point ? (this.lookAt ?? new Vector3()).copyFrom(point) : null;
  }

  /** Holds one clip instead of standing or walking (the taxi's reach), until `release`. */
  perform(clip: string, time: number, loop = false): void {
    this.override = { clip, time, loop };
  }

  release(): void {
    this.override = null;
  }

  /**
   * Follows a point the game moves (a brain): she is put there, and her stride, pace
   * and turning follow from how it moves. `direction` is where she should face.
   */
  follow(dt: number, at: Vector3, direction?: Vector3, move = true): void {
    const p = this.figure.root.position;
    // First seen, or her point has jumped (a respawn): put her there, never walk her across.
    if (!this.placed || Math.hypot(at.x - this.last.x, at.z - this.last.z) > 1.5) {
      const yaw = !this.placed && direction ? Math.atan2(direction.x, direction.z) : this.yaw;
      this.place(move ? at : Vector3.Zero(), yaw);
      this.last.copyFrom(at);
    }
    const dx = at.x - this.last.x,
      dz = at.z - this.last.z,
      moved = Math.hypot(dx, dz);
    const pace = dt > 0 ? Math.min(moved / dt, PREAY_TOP_SPEED) : 0;
    this.speed += (pace - this.speed) * (1 - Math.exp(-dt * 8));
    if (move) p.copyFrom(at);
    this.last.copyFrom(at);
    if (direction && Math.hypot(direction.x, direction.z) > 1e-4)
      this.wantYaw = Math.atan2(direction.x, direction.z);
    else if (moved > 1e-4) this.wantYaw = Math.atan2(dx, dz);
    this.step(dt);
  }

  /**
   * Walks her towards `target` at her own pace (times `pace`, at most a brisk walk),
   * easing in from standing and turning on the way. Returns true once she is there.
   */
  walkTowards(dt: number, target: Vector3, pace = 1): boolean {
    const p = this.figure.root.position;
    const dx = target.x - p.x,
      dz = target.z - p.z,
      left = Math.hypot(dx, dz);
    if (left < 0.05) {
      this.standStill(dt);
      return true;
    }
    this.wantYaw = Math.atan2(dx, dz);
    // She sets off as she turns into the way, and only as fast as her gait allows.
    const facing = Math.cos(wrap(this.wantYaw - this.yaw));
    const goal = PREAY_WALK_SPEED * Math.min(MAX_RATE, pace) * Math.max(0, facing) * this.gait;
    this.speed += (goal - this.speed) * (1 - Math.exp(-dt * 5));
    const step = Math.min(left, this.speed * dt);
    p.x += Math.sin(this.yaw) * step;
    p.z += Math.cos(this.yaw) * step;
    p.y += (target.y - p.y) * (1 - Math.exp(-dt * 6));
    this.last.copyFrom(p);
    this.step(dt, true);
    return false;
  }

  /** She stands where she is, breathing; she turns to `wantYaw` in a few steps if she must. */
  standStill(dt: number): void {
    this.speed += (0 - this.speed) * (1 - Math.exp(-dt * 6));
    this.last.copyFrom(this.figure.root.position);
    this.step(dt);
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
    // A big turn where she stands is made by stepping round, not by spinning on her heels.
    const stepping = !moving && Math.abs(turn) > STEP_ROUND;
    const gaitGoal = moving ? 1 : stepping ? 0.55 : 0;
    this.gait +=
      Math.sign(gaitGoal - this.gait) * Math.min(Math.abs(gaitGoal - this.gait), dt / GAIT_EASE);
    const rate = moving ? TURN_WALKING : stepping ? TURN_STANDING * this.gait : 0.3;
    this.yaw = wrap(this.yaw + Math.sign(turn) * Math.min(Math.abs(turn), rate * dt));

    // Faster than an easy walk, she breaks into her stumbling hurry.
    const low = PREAY_WALK_SPEED * 1.3,
      high = PREAY_HURRY_SPEED * 1.25;
    const hurryGoal = Math.max(0, Math.min(1, (this.speed - low) / (high - low)));
    this.hurry +=
      Math.sign(hurryGoal - this.hurry) *
      Math.min(Math.abs(hurryGoal - this.hurry), dt / GAIT_EASE);

    // Each clip plays at the pace she covers ground; stepping round, at a slow step.
    const before = this.walkTime,
      beforeHurry = this.hurryTime;
    const cadence = moving
      ? Math.min(MAX_RATE, this.speed / PREAY_WALK_SPEED)
      : stepping
        ? 0.5
        : this.gait * 0.4;
    this.walkTime += dt * Math.max(cadence, this.gait > 0.05 ? 0.25 : 0);
    this.hurryTime += dt * Math.max(0.5, Math.min(MAX_RATE, this.speed / PREAY_HURRY_SPEED));
    this.standTime += dt;

    const root = this.figure.root;
    root.rotationQuaternion = null;
    root.rotation.set(0, this.yaw, 0);
    if (this.override) this.figure.pose(this.override.clip, this.override.time, this.override.loop);
    else if (this.hurry > 0.002 && this.gait > 0.998)
      this.figure.blend("walk", this.walkTime, "hurry", this.hurryTime, this.hurry);
    else this.figure.blend("stand", this.standTime, "walk", this.walkTime, this.gait);
    root.computeWorldMatrix(true);

    const target = this.lookAt;
    this.look += ((target ? 1 : 0) - this.look) * (1 - Math.exp(-dt * 1.6));
    if (target && this.look > 0.01) this.figure.lookAt(target, this.look * 0.9);
    else if (!target && this.look > 0.01 && this.lastLook)
      this.figure.lookAt(this.lastLook, this.look * 0.9);
    if (target) (this.lastLook ??= new Vector3()).copyFrom(target);

    if (this.onStep && this.gait > 0.4) {
      if (this.hurry > 0.5) this.strikes("hurry", beforeHurry, this.hurryTime);
      else this.strikes("walk", before, this.walkTime);
    }
  }

  /** Calls `onStep` for every heel strike between two times in the walk. */
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
