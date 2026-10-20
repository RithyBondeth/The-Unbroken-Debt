import {
  CharacterSupportedState,
  PhysicsCharacterController,
  type CharacterSurfaceInfo,
} from "@babylonjs/core/Physics/v2/characterController";
import { PhysicsRaycastResult } from "@babylonjs/core/Physics/physicsRaycastResult";
import type { PhysicsEngine } from "@babylonjs/core/Physics/v2/physicsEngine";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { UniversalCamera } from "@babylonjs/core/Cameras/universalCamera";
import type { Scene } from "@babylonjs/core/scene";
import type { Observer } from "@babylonjs/core/Misc/observable";
import type { EventBus } from "../core/EventBus";
import type { GameEvents } from "../core/events";
import { GRAVITY, surfaceOf } from "../core/Physics";
import { DEFAULT_PLAYER_CONFIG, type PlayerConfig } from "./PlayerConfig";
import type { InputSource } from "./InputSource";
import {
  approach,
  smoothingFactor,
  targetSpeed,
  wishVelocity,
  type MoveIntent,
  type Stance,
  type Vec2,
} from "./movement";
import { advanceStride, bobOffsetX, bobOffsetY, type StrideState } from "./headBob";

/**
 * A ladder the player can climb. In levels this will come from a `ladder_`
 * node in Blender; the spike defines them in code.
 */
export interface Ladder {
  min: Vector3;
  max: Vector3;
  /** Horizontal unit vector pointing from the ladder towards the climber. */
  normal: Vector3;
}

const UP = Vector3.Up();
const DOWN = Vector3.Down();

/**
 * Sora's first-person controller on the Havok character controller:
 * walk, hurry, crouch, stairs, ladders, head-bob and footstep noise.
 * Runs after the physics step each frame (TDD section 4, update order 1).
 */
export class PlayerController {
  readonly config: PlayerConfig;
  headBobEnabled = true;
  /** When false, input is ignored (scripted sequences, menus). */
  inputEnabled = true;

  yaw = 0;
  pitch = 0;

  private readonly controller: PhysicsCharacterController;
  private readonly physics: PhysicsEngine;
  private readonly intent: MoveIntent = { x: 0, z: 0, hurry: false, crouch: false };
  private readonly look = { yaw: 0, pitch: 0 };
  private readonly stride: StrideState = { phase: 0, amplitude: 0 };
  private readonly stepResult = { stepped: false };
  private readonly ladders: Ladder[] = [];
  private readonly observer: Observer<Scene>;

  private _stance: Stance = "stand";
  private _support: CharacterSurfaceInfo | null = null;
  private _climbing: Ladder | null = null;
  private eyeHeight: number;
  private eyeY: number;
  private horizontal: Vec2 = { x: 0, z: 0 };
  private _speed = 0;

  // Scratch objects: no allocation per frame (TDD section 14).
  private readonly wish: Vec2 = { x: 0, z: 0 };
  private readonly next: Vec2 = { x: 0, z: 0 };
  private readonly forward = new Vector3();
  private readonly desired = new Vector3();
  private readonly velocity = new Vector3();
  private readonly lastPosition = new Vector3();
  private readonly rayFrom = new Vector3();
  private readonly rayTo = new Vector3();
  private readonly ray = new PhysicsRaycastResult();

  constructor(
    private readonly scene: Scene,
    private readonly camera: UniversalCamera,
    public input: InputSource,
    spawnFeet: Vector3,
    private readonly bus?: EventBus<GameEvents>,
    config: Partial<PlayerConfig> = {},
  ) {
    this.config = { ...DEFAULT_PLAYER_CONFIG, ...config };
    const c = this.config;

    const physics = scene.getPhysicsEngine();
    if (!physics) throw new Error("PlayerController needs physics enabled on the scene");
    this.physics = physics as PhysicsEngine;

    const center = spawnFeet.add(new Vector3(0, c.standHeight / 2, 0));
    this.controller = new PhysicsCharacterController(
      center,
      { capsuleHeight: c.standHeight, capsuleRadius: c.radius },
      scene,
    );
    this.controller.maxStepHeight = c.maxStepHeight;
    this.controller.maxSlopeCosine = Math.cos((c.maxSlopeDeg * Math.PI) / 180);
    this.controller.acceleration = c.acceleration;
    this.lastPosition.copyFrom(center);

    this.eyeHeight = c.standEyeHeight;
    this.eyeY = spawnFeet.y + c.standEyeHeight;
    camera.minZ = 0.05;
    camera.inputs.clear();

    this.observer = scene.onAfterPhysicsObservable.add(() => this.update());
  }

  get stance(): Stance {
    return this._stance;
  }

  get climbing(): boolean {
    return this._climbing !== null;
  }

  get supported(): boolean {
    return this._support?.supportedState === CharacterSupportedState.SUPPORTED;
  }

  /** Horizontal speed in m/s. */
  get speed(): number {
    return this._speed;
  }

  /** Wished horizontal velocity for the current input, used by tests to detect snagging. */
  get wishVelocity(): Readonly<Vec2> {
    return this.wish;
  }

  get wishSpeed(): number {
    return Math.hypot(this.wish.x, this.wish.z);
  }

  get feet(): Vector3 {
    const p = this.controller.getPosition();
    return new Vector3(p.x, p.y - this.currentHeight() / 2, p.z);
  }

  addLadder(ladder: Ladder): void {
    this.ladders.push(ladder);
  }

  teleport(feet: Vector3, yaw = this.yaw): void {
    this.controller.setPosition(feet.add(new Vector3(0, this.currentHeight() / 2, 0)));
    this.controller.setVelocity(Vector3.Zero());
    this.lastPosition.copyFrom(this.controller.getPosition());
    this.horizontal = { x: 0, z: 0 };
    this.yaw = yaw;
    this.eyeY = feet.y + this.eyeHeight;
    this._climbing = null;
  }

  dispose(): void {
    this.observer.remove();
    this.controller.dispose();
  }

  private update(): void {
    // Clamp long frames (tab switches, hitches) so nothing tunnels through floors.
    const dt = Math.min(this.scene.getEngine().getDeltaTime() / 1000, 1 / 30);
    if (!(dt > 0)) return;
    const c = this.config;

    this.readInput();
    this.updateStance();

    const support = this.controller.checkSupport(dt, DOWN);
    this._support = support;

    const ladder = this.findLadder();
    if (this._climbing && ladder !== this._climbing) this._climbing = null;
    if (!this._climbing && ladder && this.intent.z > 0 && this.facing(ladder)) {
      this._climbing = ladder;
    }

    const speed = targetSpeed(this._stance, this.intent.hurry, c);
    wishVelocity(this.intent, this.yaw, speed, this.wish);

    if (this._climbing) this.climb(dt, support, this._climbing);
    else if (support.supportedState === CharacterSupportedState.SUPPORTED) this.walk(dt, support);
    else this.fall(dt, support);

    // Speed from actual movement: the solver's velocity is noisy even at rest.
    const p = this.controller.getPosition();
    const moved = this._climbing
      ? Math.abs(p.y - this.lastPosition.y)
      : Math.hypot(p.x - this.lastPosition.x, p.z - this.lastPosition.z);
    this._speed += (moved / dt - this._speed) * smoothingFactor(dt, 0.05);
    this.lastPosition.copyFrom(p);
    this.updateCamera(dt);
  }

  private readInput(): void {
    if (!this.inputEnabled) {
      this.intent.x = 0;
      this.intent.z = 0;
      this.intent.hurry = false;
      this.input.consumeLook(this.look);
      return;
    }
    this.input.readMove(this.intent);
    this.input.consumeLook(this.look);
    this.yaw += this.look.yaw;
    const max = this.config.maxPitch;
    this.pitch = Math.max(-max, Math.min(max, this.pitch + this.look.pitch));
  }

  private updateStance(): void {
    const c = this.config;
    if (this.intent.crouch && this._stance === "stand") {
      this.controller.setShapeOptions(
        { capsuleHeight: c.crouchHeight, capsuleRadius: c.radius },
        true,
      );
      this._stance = "crouch";
    } else if (!this.intent.crouch && this._stance === "crouch" && this.canStand()) {
      this.controller.setShapeOptions(
        { capsuleHeight: c.standHeight, capsuleRadius: c.radius },
        true,
      );
      this._stance = "stand";
    }
  }

  /** Checks for headroom above a crouched player before standing up. */
  private canStand(): boolean {
    const c = this.config;
    const feet = this.feet;
    const probe = c.radius * 0.8;
    const offsets = [
      [0, 0],
      [probe, 0],
      [-probe, 0],
      [0, probe],
      [0, -probe],
    ];
    for (const [ox, oz] of offsets) {
      this.rayFrom.set(feet.x + ox, feet.y + c.crouchHeight + 0.02, feet.z + oz);
      this.rayTo.set(feet.x + ox, feet.y + c.standHeight + 0.05, feet.z + oz);
      this.physics.raycastToRef(this.rayFrom, this.rayTo, this.ray);
      if (this.ray.hasHit) return false;
    }
    return true;
  }

  private walk(dt: number, support: CharacterSurfaceInfo): void {
    this.forward.set(Math.sin(this.yaw), 0, Math.cos(this.yaw));
    this.desired.set(this.wish.x, 0, this.wish.z);
    const current = this.controller.getVelocity();
    const out = this.controller.calculateMovement(
      dt,
      this.forward,
      support.averageSurfaceNormal,
      current,
      support.averageSurfaceVelocity,
      this.desired,
      UP,
    );

    // Keep ground speed constant on slopes and stairs: project onto the surface
    // without losing horizontal length (from the Babylon character controller sample).
    out.subtractInPlace(support.averageSurfaceVelocity);
    if (out.dot(UP) > 1e-3) {
      const length = out.length();
      out.normalizeFromLength(length);
      const horizontalLength = length / support.averageSurfaceNormal.dot(UP);
      const side = support.averageSurfaceNormal.cross(out);
      side.cross(UP).scaleToRef(horizontalLength, out);
    }
    out.addInPlace(support.averageSurfaceVelocity);

    this.controller.setVelocity(out);
    this.controller.integrate(dt, support, GRAVITY);
    this.horizontal.x = out.x;
    this.horizontal.z = out.z;
    this.snapToGround(support);
  }

  /**
   * Keeps the capsule on flat floors. Havok reports "supported" within a contact
   * tolerance, so after riding over a threshold or warped board the capsule can
   * hover several centimetres up indefinitely; this moves it back down.
   * Slopes and slope transitions are left alone: a centre-line ray can't tell
   * where a rounded capsule rests there, and snapping would push it into the ramp.
   */
  private snapToGround(support: CharacterSurfaceInfo): void {
    const c = this.config;
    if (support.averageSurfaceNormal.y < 0.98) return;
    const p = this.controller.getPosition();
    const feetY = p.y - this.currentHeight() / 2;
    this.rayFrom.set(p.x, feetY + c.radius, p.z);
    this.rayTo.set(p.x, feetY - c.groundSnap, p.z);
    this.physics.raycastToRef(this.rayFrom, this.rayTo, this.ray);
    if (!this.ray.hasHit || this.ray.hitNormalWorld.y < 0.98) return;

    const keep = this.controller.keepDistance;
    const gap = feetY - this.ray.hitPointWorld.y;
    if (gap > keep + 0.01 && gap < c.groundSnap) {
      p.y -= gap - keep;
      this.controller.setPosition(p);
    }
  }

  private fall(dt: number, support: CharacterSurfaceInfo): void {
    const current = this.controller.getVelocity();
    approach(
      this.horizontal,
      this.wish,
      this.config.acceleration * this.config.airControl * dt,
      this.next,
    );
    this.horizontal.x = this.next.x;
    this.horizontal.z = this.next.z;
    this.velocity.set(this.next.x, current.y + GRAVITY.y * dt, this.next.z);
    this.controller.setVelocity(this.velocity);
    this.controller.integrate(dt, support, GRAVITY);
  }

  /** W climbs, S descends; looking well down while pressing W also descends. */
  private climb(dt: number, support: CharacterSurfaceInfo, ladder: Ladder): void {
    const c = this.config;
    const lookingDown = this.pitch > 0.6;
    const vertical = this.intent.z * c.climbSpeed * (lookingDown ? -1 : 1);

    // Stepping back off the bottom of the ladder returns to walking.
    if (vertical < 0 && support.supportedState === CharacterSupportedState.SUPPORTED) {
      this._climbing = null;
      this.walk(dt, support);
      return;
    }

    // Lean into the ladder so the climber steps onto the floor at the top.
    const into = this.intent.z > 0 ? 0.6 : 0;
    this.velocity.set(-ladder.normal.x * into, vertical, -ladder.normal.z * into);
    this.controller.setVelocity(this.velocity);
    this.controller.integrate(dt, support, Vector3.ZeroReadOnly);
  }

  private findLadder(): Ladder | null {
    const p = this.controller.getPosition();
    const feetY = p.y - this.currentHeight() / 2;
    for (const ladder of this.ladders) {
      if (
        p.x >= ladder.min.x &&
        p.x <= ladder.max.x &&
        p.z >= ladder.min.z &&
        p.z <= ladder.max.z &&
        feetY >= ladder.min.y - 0.1 &&
        feetY <= ladder.max.y
      ) {
        return ladder;
      }
    }
    return null;
  }

  private facing(ladder: Ladder): boolean {
    // Facing the ladder means looking against its normal.
    const fx = Math.sin(this.yaw);
    const fz = Math.cos(this.yaw);
    return fx * -ladder.normal.x + fz * -ladder.normal.z > 0.5;
  }

  private currentHeight(): number {
    return this._stance === "crouch" ? this.config.crouchHeight : this.config.standHeight;
  }

  private updateCamera(dt: number): void {
    const c = this.config;
    const p = this.controller.getPosition();
    const feetY = p.y - this.currentHeight() / 2;

    const targetEye = this._stance === "crouch" ? c.crouchEyeHeight : c.standEyeHeight;
    this.eyeHeight += (targetEye - this.eyeHeight) * smoothingFactor(dt, c.crouchTransition);

    // Smooth vertical motion so step-ups don't snap the view; snap on big
    // changes (falls, teleports) so the camera never lags far behind.
    const eyeTarget = feetY + this.eyeHeight;
    if (Math.abs(eyeTarget - this.eyeY) > 0.5 || this._climbing) this.eyeY = eyeTarget;
    else this.eyeY += (eyeTarget - this.eyeY) * smoothingFactor(dt, c.eyeSmoothing);

    // Head-bob and footsteps while walking on the ground.
    const onGround = this.supported && !this._climbing;
    const moving = onGround && this._speed > 0.2;
    const stride =
      this._stance === "crouch" ? c.strideCrouch : this.intent.hurry ? c.strideHurry : c.strideWalk;
    const bobTarget = !moving
      ? 0
      : this._stance === "crouch"
        ? c.bobCrouch
        : this.intent.hurry
          ? c.bobHurry
          : c.bobWalk;
    this.stride.amplitude += (bobTarget - this.stride.amplitude) * smoothingFactor(dt, 0.15);
    if (moving) {
      advanceStride(this.stride, this._speed * dt, stride, this.stepResult);
      if (this.stepResult.stepped) this.footstep(feetY);
    }

    const bob = this.headBobEnabled ? this.stride.amplitude : 0;
    const sway = bobOffsetX(this.stride.phase, bob);
    const rightX = Math.cos(this.yaw);
    const rightZ = -Math.sin(this.yaw);

    this.camera.position.set(
      p.x + rightX * sway,
      this.eyeY + bobOffsetY(this.stride.phase, bob),
      p.z + rightZ * sway,
    );
    this.camera.rotation.set(this.pitch, this.yaw, 0);
  }

  private footstep(feetY: number): void {
    if (!this.bus) return;
    const c = this.config;
    const p = this.controller.getPosition();
    this.rayFrom.set(p.x, feetY + 0.05, p.z);
    this.rayTo.set(p.x, feetY - 0.3, p.z);
    this.physics.raycastToRef(this.rayFrom, this.rayTo, this.ray);
    const surface = surfaceOf(this.ray.body?.transformNode) ?? "dirt";
    const loudness =
      this._stance === "crouch" ? c.noiseCrouch : this.intent.hurry ? c.noiseHurry : c.noiseWalk;
    this.bus.emit("player:step", { surface, loudness });
    this.bus.emit("noise:made", {
      position: { x: p.x, y: feetY, z: p.z },
      loudness,
      source: "player",
    });
  }
}
