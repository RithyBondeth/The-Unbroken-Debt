import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { Quaternion, Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import { CreateBox } from "@babylonjs/core/Meshes/Builders/boxBuilder";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { VertexData } from "@babylonjs/core/Meshes/mesh.vertexData";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import {
  PhysicsEventType,
  PhysicsMotionType,
} from "@babylonjs/core/Physics/v2/IPhysicsEnginePlugin";
import { PhysicsBody } from "@babylonjs/core/Physics/v2/physicsBody";
import {
  PhysicsShapeBox,
  PhysicsShapeCapsule,
  PhysicsShapeCylinder,
  type PhysicsShape,
} from "@babylonjs/core/Physics/v2/physicsShape";
import type { Scene } from "@babylonjs/core/scene";
import type { BusName, SpatialOptions } from "@/audio/AudioSystem";
import type { DreadScore } from "@/audio/DreadScore";
import { seededRandom } from "@/audio/synth";
import type { Game } from "@/core/Game";
import * as sounds from "../audio/studioSounds";
import { phoneRing, thunder } from "../audio/prologueSounds";
import { KIT } from "../data/prologue";
import { POWER_CUT, POWER_RETURN } from "../data/powerCut";
import {
  ALTAR,
  FALLEN_FLAG,
  PICTURE,
  SHADOW,
  STUDIO_DOORS,
  altarDue,
  angleTo,
  balconyKnockDue,
  bathDoorDue,
  bathMirrorDue,
  bathTankDue,
  bedBreathDue,
  bookSlideDue,
  chairTurnDue,
  decodePoses,
  doorWatcherDue,
  dropBookDue,
  encodePoses,
  fanDriftDue,
  hallFlashDue,
  inBackRoom,
  inBathroom,
  phantomRingDue,
  pictureDue,
  runtime,
  shadowShot,
  stairStepsDue,
  studioHauntPhase,
  studioScareFlag,
  type ShadowShot,
  type StudioDoorId,
  type StudioScareId,
} from "../data/studioScares";
import { Preay } from "../entities/Preay";
import type { StudioLights } from "./Studio";
import { StudioBathVisuals } from "./StudioBathVisuals";
import { StudioFlamesAndSmoke } from "./StudioFlamesAndSmoke";

/** Seen by no camera (cameras see 0x0FFFFFFF): the shadow's figure is in the light's eyes only. */
const UNSEEN = 0x10000000;
/** Standard camera visibility mask for real silhouette apparitions. */
const VISIBLE = 0x0fffffff;
/** The floor of every room on Sora's floor (runtime y). */
const FLOOR = 0;
/** An impact this fast (m/s) or faster is heard. */
const HEARD = 1.1;

type Kind =
  | "picture"
  | "thunder"
  | "tear"
  | "vase"
  | "glass"
  | "brass"
  | "bowl"
  | "thud"
  | "breath"
  | "powerDown"
  | "powerUp"
  | "doorCreak"
  | "doorOpen"
  | "doorClose"
  | "doorLatch"
  | "doorSlam"
  | "waterStir"
  | "bulbFlicker"
  | "stepsSlow"
  | "stepsFast"
  | "creak"
  | "knock"
  | "whisper"
  | "phantomRing";

interface SoundPool {
  voices: StaticSound[];
  volume: number;
  lastIndex: number;
}

interface DoorState {
  id: StudioDoorId;
  node: TransformNode;
  openRad: number;
  closedRad: number;
  ajarRad: number;
  angle: number;
  target: number;
  speed: number;
  /** Sound to fire the instant the door leaf meets its jamb (closedRad). */
  closingLatch: "none" | "normal" | "slam";
}

interface Piece {
  node: TransformNode;
  body: PhysicsBody | null;
  /** Its speed this frame and the last (m/s): how hard it hit. */
  speed: number;
  prev: number;
  /** Called once, the first time it strikes something (not the shelf) hard enough. */
  impact?: (at: Vector3, speed: number) => void;
}

interface Cue {
  at: number;
  play: () => void;
}

interface Fall {
  time: number;
  cues: Cue[];
  step?: (t: number, dt: number) => void;
}

const DEG = Math.PI / 180;

/**
 * The studio's 4-phase psychological horror director, interactive hinged door
 * system, animated candle/incense flame & smoke engine, and Havok scare physics.
 */
export class StudioScares {
  private readonly scene: Scene;
  /** Seconds Sora has been free to move (the opening and cutscenes do not count). */
  private time = 0;
  private readonly pieces = new Map<string, Piece>();
  private readonly doors = new Map<StudioDoorId, DoorState>();
  private readonly falls: Fall[] = [];
  private readonly hits: (() => void)[] = [];
  private readonly sfx = new Map<Kind, SoundPool>();
  private heart: StaticSound | null = null;
  private bathDrip: StaticSound | null = null;
  private bathFaucet: StaticSound | null = null;
  private preay: Preay | null = null;
  private figure: AbstractMesh[] = [];
  private figureHead = 1.55;
  private hideFigureAt = -1;
  private glassMaterial: PBRMaterial | null = null;
  /** The altar's shelf: its node at the hinge, its body, the axis it swings on. */
  private shelf: { node: TransformNode; body: PhysicsBody; axis: Vector3 } | null = null;
  private altar: "waiting" | "falling" | "fallen" = "waiting";
  private readonly altarWaiting: (() => void)[] = [];
  /** How long Sora has had the satchel, and been in the back room with it (s). */
  private holding = 0;
  private waited = 0;
  private outside = 0;
  private pictureAt: Vector3 | null = null;
  private altarAt: Vector3 | null = null;

  // ---- Visual & interactive studio runtime systems
  private bathVisuals: StudioBathVisuals | null = null;
  private flames: StudioFlamesAndSmoke | null = null;
  private visitedBackOrBath = false;
  private faucetRunning = false;
  private fanNode: TransformNode | null = null;
  private fanDrifting = false;
  private fanDriftAngle = 0;
  private slideBookNode: TransformNode | null = null;
  private dropBookNode: TransformNode | null = null;
  private stoolNode: TransformNode | null = null;
  private bathDipperNode: TransformNode | null = null;
  private bathMirrorAt: Vector3 | null = null;
  private bathTankAt: Vector3 | null = null;
  private bathFaucetAt: Vector3 | null = null;
  private bathBulbAt: Vector3 | null = null;
  private stairDoorAt: Vector3 | null = null;
  private balconyOpenSec = 0;
  private phase4BathKilled = false;
  private phase4HallFlickered = false;
  private phase4BedroomClosed = false;
  private watcherActive = false;
  private watcherSlip = 0;
  private nextAmbientAt = 18;

  constructor(
    private readonly game: Game,
    private readonly lights: StudioLights,
    private readonly score: () => DreadScore,
  ) {
    this.scene = game.scene;
  }

  // ---------------------------------------------------------------- loading

  async load(): Promise<void> {
    const flags = this.game.flags;
    for (const mesh of this.scene.meshes) if (/_shard_\d+$/.test(mesh.name)) mesh.isVisible = false;
    this.pictureAt = this.group("fall_picture")?.getAbsolutePosition().clone() ?? null;
    const shelf = this.group("fall_altar_shelf");
    if (shelf) {
      const { min, max } = shelf.getHierarchyBoundingVectors(true);
      this.altarAt = Vector3.Center(min, max);
    }

    // Dynamic haunt & interactive nodes kept separate from static batching
    this.fanNode = this.group("haunt_fan_rotor");
    this.slideBookNode = this.group("haunt_slide_book");
    this.dropBookNode = this.group("haunt_drop_book");
    this.stoolNode = this.group("haunt_stool");
    this.bathDipperNode = this.group("haunt_bath_dipper");
    this.stairDoorAt = this.group("interact_door")?.getAbsolutePosition().clone() ?? null;

    // Register all 4 interactive hinged doors (studio partition, bedroom, bathroom, balcony)
    for (const id of Object.keys(STUDIO_DOORS) as StudioDoorId[]) {
      const node = this.group(id);
      if (!node) continue;
      const cfg = STUDIO_DOORS[id];
      const state: DoorState = {
        id,
        node,
        openRad: cfg.openDeg * DEG,
        closedRad: cfg.closedDeg * DEG,
        ajarRad: cfg.ajarDeg * DEG,
        angle: cfg.initialDeg * DEG,
        target: cfg.initialDeg * DEG,
        speed: 2.2,
        closingLatch: "none",
      };
      this.doors.set(id, state);
      this.applyDoorAngle(state);
    }

    const marker = (name: string, fallback: Vector3) =>
      this.scene.getTransformNodeByName(`marker_${name}`)?.getAbsolutePosition().clone() ??
      fallback;
    this.bathMirrorAt = marker("bath_mirror", runtime(1.72, 16.712, 1.57));
    this.bathTankAt = marker("bath_tank", runtime(0.5, 16.24, 0.72));
    this.bathFaucetAt = marker("bath_faucet_drip", runtime(1.605, 16.567, 0.839));
    this.bathBulbAt = marker("bath_bulb", runtime(1.68, 15.45, 2.52));

    // Give the empty faucet anchor a generous invisible pickup volume around both brass taps
    const faucetNode = this.group("interact_bath_faucet");
    if (faucetNode) {
      const hit = CreateBox(
        "bath_faucet_pickup_volume",
        { width: 0.44, height: 0.26, depth: 0.26 },
        this.scene,
      );
      hit.position.copyFrom(faucetNode.getAbsolutePosition());
      hit.visibility = 0;
      hit.setParent(faucetNode);
    }

    this.bathVisuals = new StudioBathVisuals(this.scene, {
      mirrorAt: this.bathMirrorAt,
      faucetAt: this.bathFaucetAt,
      tankAt: this.bathTankAt,
    });
    this.flames = new StudioFlamesAndSmoke(this.scene);

    try {
      const asset = await Preay.load(this.scene);
      const preay = (this.preay = new Preay(asset, "studio_shadow"));
      this.figure = preay.root.getChildMeshes(false);
      for (const mesh of this.figure) {
        mesh.layerMask = UNSEEN;
        mesh.isPickable = false;
        mesh.receiveShadows = false;
        mesh.alwaysSelectAsActiveMesh = true;
      }
      preay.perform("reach", SHADOW.reach);
      preay.standStill(0);
      preay.root.computeWorldMatrix(true);
      const { max } = preay.root.getHierarchyBoundingVectors(true);
      this.figureHead = Math.max(1.3, Math.min(1.7, max.y - preay.root.position.y - 0.08));
      preay.setEnabled(false);
    } catch (error) {
      console.warn("[StudioScares] the shadow's figure did not load", error);
    }

    // Restored checkpoint state: preserve fallen objects, slid/dropped books, handprint, footprints
    const poses = decodePoses(flags.get(FALLEN_FLAG, ""));
    if (this.done("picture")) this.layPicture(poses);
    if (this.done("book") && this.slideBookNode) {
      this.slideBookNode.setAbsolutePosition(
        this.slideBookNode.getAbsolutePosition().add(new Vector3(-0.11, 0, 0)),
      );
    }
    if (this.done("dropBook") && this.dropBookNode) {
      const pose = poses.drop_book;
      if (pose) this.pose(this.dropBookNode, pose);
      else this.dropBookNode.setAbsolutePosition(runtime(0.72, 4.9, 0.02));
    }
    if (this.done("chairTurn") && this.stoolNode) {
      this.stoolNode.rotationQuaternion = Quaternion.RotationAxis(Vector3.Up(), 1.0);
      this.stoolNode.setAbsolutePosition(
        this.stoolNode.getAbsolutePosition().add(new Vector3(0.14, 0, -0.1)),
      );
    }
    if (this.done("bathMirror")) this.bathVisuals.revealHandprint(true);
    if (this.done("bathDoor")) {
      const d = this.doors.get("haunt_bath_door");
      if (d) {
        d.angle = d.target = d.ajarRad;
        this.applyDoorAngle(d);
      }
    }
    if (flags.get("ep1.clock.stopped", "")) {
      this.flames.extinguish("shelf", false);
    }
    if (flags.get("ep1.phone.answered", false)) {
      this.bathVisuals.showWetFootprints(true);
    }
    if (this.done("altar")) {
      this.layAltar(poses);
      this.flames.extinguish("altar", false);
      this.altar = "fallen";
    } else if (
      flags.get("ep1.studio.dancerSeen", false) ||
      flags.get("ep1.phone.answered", false)
    ) {
      this.altar = "fallen";
    }
  }

  /** Loads all mastered CC0 Freesound clips with non-repeating pools and synth fallbacks. */
  async makeSounds(): Promise<void> {
    const audio = this.game.audio;
    if (!audio) return;
    const rate = audio.context.sampleRate;
    const base = `${import.meta.env.BASE_URL}assets/ep1/audio/`;
    const loadClip = (file: string) => audio.load([`${base}${file}.ogg`, `${base}${file}.m4a`]);

    type Make = (rate: number, rand: () => number) => Float32Array;
    const list: [Kind, string[], Make, BusName, number, SpatialOptions][] = [
      [
        "picture",
        ["sfx_ep1_studio_picture"],
        (r, n) => sounds.smash(r, n, 1.7),
        "sfx",
        1,
        { minDistance: 2.5 },
      ],
      [
        "thunder",
        ["sfx_ep1_studio_thunder", "sfx_ep1_studio_thunder_2", "sfx_ep1_studio_thunder_3"],
        thunder,
        "threat",
        1,
        { minDistance: 30, volume: 0.95 },
      ],
      ["tear", ["sfx_ep1_studio_tear"], sounds.tear, "sfx", 1, { minDistance: 2.5 }],
      [
        "vase",
        ["sfx_ep1_studio_vase"],
        (r, n) => sounds.smash(r, n, 1),
        "sfx",
        1,
        { minDistance: 2.5 },
      ],
      [
        "glass",
        ["sfx_ep1_studio_glass"],
        (r, n) => sounds.smash(r, n, 1.8),
        "sfx",
        2,
        { minDistance: 2, volume: 0.8 },
      ],
      [
        "brass",
        ["sfx_ep1_studio_brass", "sfx_ep1_studio_brass_2"],
        sounds.clang,
        "sfx",
        2,
        { minDistance: 2, volume: 0.8 },
      ],
      ["bowl", ["sfx_ep1_studio_bowl"], sounds.bowlSpin, "sfx", 1, { minDistance: 2, volume: 0.8 }],
      ["thud", [], sounds.thud, "sfx", 2, { minDistance: 2, volume: 0.72 }],
      [
        "breath",
        ["sfx_ep1_studio_breath"],
        sounds.whisper,
        "threat",
        1,
        { minDistance: 0.7, volume: 0.72 },
      ],
      ["powerDown", [], sounds.powerDown, "threat", 1, { minDistance: 3, volume: 0.9 }],
      ["powerUp", [], sounds.powerUp, "threat", 1, { minDistance: 3, volume: 0.8 }],
      [
        "doorCreak",
        ["sfx_ep1_studio_door_creak_1", "sfx_ep1_studio_door_creak_2"],
        sounds.creak,
        "sfx",
        2,
        { minDistance: 1.8, volume: 0.74 },
      ],
      [
        "doorOpen",
        ["sfx_ep1_studio_door_open"],
        sounds.creak,
        "sfx",
        2,
        { minDistance: 1.8, volume: 0.8 },
      ],
      [
        "doorClose",
        ["sfx_ep1_studio_door_close", "sfx_ep1_studio_door_close_2"],
        sounds.doorClose,
        "sfx",
        2,
        { minDistance: 2.0, volume: 0.84 },
      ],
      [
        "doorLatch",
        ["sfx_ep1_studio_door_latch"],
        sounds.doorLatch,
        "sfx",
        2,
        { minDistance: 1.5, volume: 0.72 },
      ],
      [
        "doorSlam",
        ["sfx_ep1_studio_door_slam"],
        sounds.doorClose,
        "threat",
        2,
        { minDistance: 2.6, volume: 0.96 },
      ],
      [
        "waterStir",
        ["sfx_ep1_studio_water_stir"],
        sounds.thud,
        "sfx",
        1,
        { minDistance: 1.4, volume: 0.7 },
      ],
      [
        "bulbFlicker",
        ["sfx_ep1_studio_bulb_flicker"],
        sounds.powerUp,
        "sfx",
        1,
        { minDistance: 1.8, volume: 0.65 },
      ],
      [
        "stepsSlow",
        ["sfx_ep1_studio_steps_slow"],
        sounds.creak,
        "threat",
        1,
        { minDistance: 1.8, volume: 0.64 },
      ],
      [
        "stepsFast",
        ["sfx_ep1_studio_steps_fast"],
        sounds.creak,
        "threat",
        1,
        { minDistance: 2.2, volume: 0.84 },
      ],
      [
        "creak",
        ["sfx_ep1_studio_creak_1", "sfx_ep1_studio_creak_2", "sfx_ep1_studio_creak_3"],
        sounds.creak,
        "sfx",
        1,
        { minDistance: 1.8, volume: 0.62 },
      ],
      [
        "knock",
        ["sfx_ep1_studio_knock_1", "sfx_ep1_studio_knock_2", "sfx_ep1_studio_knock_3"],
        sounds.knock,
        "sfx",
        1,
        { minDistance: 2.2, volume: 0.68 },
      ],
      [
        "whisper",
        ["sfx_ep1_studio_whisper_1", "sfx_ep1_studio_whisper_2"],
        sounds.whisper,
        "threat",
        1,
        { minDistance: 0.75, volume: 0.58 },
      ],
      [
        "phantomRing",
        ["sfx_ep1_studio_phone_ring"],
        phoneRing,
        "threat",
        1,
        { minDistance: 2.4, volume: 0.58 },
      ],
    ];

    await Promise.all(
      list.map(async ([kind, clips, make, bus, copies, options], i) => {
        const loaded = (await Promise.all(clips.map((c) => loadClip(c)))).filter(
          (b): b is AudioBuffer => b !== null,
        );
        const buffers = loaded.length
          ? loaded
          : [audio.buffer(make(rate, seededRandom(1940 + i)), rate)];
        const voices: StaticSound[] = [];
        for (let b = 0; b < buffers.length; b++) {
          for (let v = 0; v < copies; v++) {
            voices.push(
              await audio.spatialSound(
                `studio_${kind}_${b}_${v}`,
                buffers[b],
                bus,
                Vector3.Zero(),
                options,
              ),
            );
          }
        }
        this.sfx.set(kind, { voices, volume: voices[0].volume, lastIndex: -1 });
      }),
    );

    const heart = (this.heart = await audio.sound(
      "studio_heart",
      audio.buffer(sounds.heartbeat(rate), rate),
      "sfx",
      0.48,
    ));
    heart.loop = true;

    // Spatialized bathroom water loops: faint steady drip + interactive running faucet
    const faucetPos = this.bathFaucetAt ?? runtime(1.605, 16.567, 0.839);
    const dripBuf = await loadClip("amb_ep1_bath_drip");
    if (dripBuf) {
      this.bathDrip = await audio.spatialSound("studio_bath_drip", dripBuf, "sfx", faucetPos, {
        loop: true,
        minDistance: 0.7,
        maxDistance: 7.5,
        volume: 0.34,
      });
      this.bathDrip.play();
    }
    const faucetBuf = await loadClip("amb_ep1_bath_faucet");
    if (faucetBuf) {
      this.bathFaucet = await audio.spatialSound(
        "studio_bath_faucet",
        faucetBuf,
        "sfx",
        faucetPos,
        {
          loop: true,
          minDistance: 0.9,
          maxDistance: 10.5,
          volume: 0.58,
        },
      );
    }
  }

  /**
   * Puts what the scares show for the first time where the warm-up views can see it,
   * so no shader is built mid-scare.
   */
  prepareWarm(): () => void {
    const shown: AbstractMesh[] = [];
    if (!this.done("altar"))
      for (const mesh of this.scene.meshes)
        if (/_shard_\d+$/.test(mesh.name) && !mesh.isVisible) {
          mesh.isVisible = true;
          shown.push(mesh);
        }
    for (const mesh of [
      ...(this.bathVisuals?.warmupMeshes() ?? []),
      ...(this.flames?.warmupMeshes() ?? []),
    ]) {
      if (!mesh.isVisible) {
        mesh.isVisible = true;
        shown.push(mesh);
      }
    }
    const glass = this.altarAt
      ? this.brokenGlass("warm_glass", 1, this.altarAt.add(new Vector3(0, 0.3, 0.3)), 0)
      : [];
    let unwarm: () => void = () => undefined;
    if (this.preay) {
      this.setFigureLayer(VISIBLE);
      this.preay.place(new Vector3(-2.3, FLOOR, -3.5), 0);
      this.preay.standStill(0);
      this.preay.setEnabled(true);
      unwarm = this.lights.warmFlash(this.figure);
    }
    return () => {
      for (const mesh of shown) mesh.isVisible = false;
      for (const mesh of glass) mesh.dispose();
      unwarm();
      this.setFigureLayer(UNSEEN);
      this.preay?.setEnabled(false);
    };
  }

  // ---------------------------------------------------------------- public hooks

  /** Resolves once the altar has fallen and the lights are back (at once if it has). */
  altarFallen(): Promise<void> {
    if (this.altar === "fallen") return Promise.resolve();
    return new Promise((done) => this.altarWaiting.push(done));
  }

  /** The altar has fallen, or is falling. */
  get altarDone(): boolean {
    return this.altar !== "waiting";
  }

  /** Whether the cold bathroom tap is currently running. */
  get faucetIsRunning(): boolean {
    return this.faucetRunning;
  }

  /** True when the given interactive studio door is currently open (or opening). */
  isDoorOpen(id: StudioDoorId): boolean {
    const d = this.doors.get(id);
    if (!d) return false;
    return Math.abs(d.target - d.closedRad) > 0.2;
  }

  /** Opens or closes any hinged door smoothly with tactile latch, creak & jamb-shut audio. */
  toggleDoor(id: StudioDoorId): boolean {
    const d = this.doors.get(id);
    if (!d) return false;
    const opening = !this.isDoorOpen(id);
    const at = d.node.getAbsolutePosition();
    d.target = opening ? d.openRad : d.closedRad;
    d.speed = id === "haunt_balcony_door" ? 1.85 : 2.35;
    if (opening) {
      d.closingLatch = "none";
      this.play("doorLatch", at, id === "haunt_balcony_door" ? 0.82 : 0.65);
      this.play("doorOpen", at, 0.78);
    } else {
      d.closingLatch = "normal";
      this.play("doorCreak", at, 0.44);
    }
    if (id === "haunt_balcony_door" && opening) {
      this.flames?.pulseDraught(0.85, 0.25, -0.95);
    }
    return opening;
  }

  /** Plays a crisp brass latch click (e.g. rattling the locked stair gate). */
  playDoorLatch(at: Vector3): void {
    this.play("doorLatch", at, 0.76);
  }

  /** Plays a wooden door unlatch & swing open (e.g. opening the stair gate at P07). */
  playDoorOpen(at: Vector3): void {
    this.play("doorLatch", at, 0.7);
    this.play("doorOpen", at, 0.85);
  }

  /** Legacy alias for bathroom door toggle. */
  toggleBathDoor(): void {
    this.toggleDoor("haunt_bath_door");
  }

  /** Toggles the bathroom cold tap when Sora presses E at `interact_bath_faucet`. */
  toggleFaucet(): void {
    this.setFaucetRunning(!this.faucetRunning);
    this.play("thud", this.bathFaucetAt ?? this.game.camera.globalPosition, 0.42);
  }

  /** Called by Prologue when the shelf candle is snuffed in P05: bursts rising wick smoke. */
  onShelfCandleSnuffed(): void {
    this.flames?.extinguish("shelf", true);
  }

  /** Sora's pounding heart: on as the altar falls, off once she lifts the earpiece. */
  heartbeat(on: boolean): void {
    if (!this.heart) return;
    if (on) this.heart.play();
    else this.heart.stop();
  }

  /** Stops all looping bathroom/scare beds cleanly when leaving the studio. */
  stopLoops(): void {
    this.heart?.stop();
    this.bathDrip?.stop();
    this.bathFaucet?.stop();
    this.game.audio?.duckAmbience(1, 0.2);
  }

  /** Called by Prologue once Yay Mey's terrifying phone call ends (begins Phase 4). */
  onPhoneAnswered(): void {
    this.bathVisuals?.showWetFootprints(true);
    this.flames?.pulseDraught(0.75, 0.5, 0.85);
    this.score().pressure(0.42);
  }

  /** Plays a non-repeating real thunder crack for natural storm lightning. */
  playStormThunder(at: Vector3): void {
    this.play("thunder", at, 0.85);
  }

  // ---------------------------------------------------------------- each frame

  update(dt: number, ringing = false): void {
    const game = this.game;
    this.bathVisuals?.update(dt);
    this.stepDoors(dt);

    const balcony = this.doors.get("haunt_balcony_door");
    const balconyOpenFrac = balcony
      ? Math.min(
          1,
          Math.abs(balcony.angle - balcony.closedRad) / Math.max(0.1, Math.abs(balcony.openRad)),
        )
      : 0;
    this.flames?.setPower(this.lights.power);
    this.flames?.update(dt, balconyOpenFrac);

    for (const piece of this.pieces.values())
      if (piece.body) {
        piece.prev = piece.speed;
        piece.speed = piece.body.getLinearVelocity().length();
      }
    for (const hit of this.hits.splice(0)) hit();
    for (const fall of [...this.falls]) {
      fall.time += dt;
      for (const cue of fall.cues.filter((c) => c.at <= fall.time)) {
        fall.cues.splice(fall.cues.indexOf(cue), 1);
        cue.play();
      }
      fall.step?.(fall.time, dt);
      if (!fall.cues.length && !fall.step) this.falls.splice(this.falls.indexOf(fall), 1);
    }
    if (this.hideFigureAt >= 0 && this.time >= this.hideFigureAt) {
      this.hideFigureAt = -1;
      this.preay?.setEnabled(false);
      this.setFigureLayer(UNSEEN);
    }
    if (game.cutscene) return;
    this.time += dt;
    const eye = game.camera.globalPosition;
    const forward = game.camera.getDirection(Vector3.Forward());

    if (inBackRoom(eye) || inBathroom(eye)) this.visitedBackOrBath = true;

    const kitCount = KIT.filter((k) => game.inventory.has(k)).length;
    const phoneAnswered = game.flags.get("ep1.phone.answered", false);
    const phase = studioHauntPhase({
      kitCount,
      visitedBackOrBath: this.visitedBackOrBath,
      altarDone: this.altarDone,
      phoneAnswered,
    });

    // ---- Phase 1: Subtle psychological gaslighting
    this.stepFanDrift(dt, eye, forward);
    if (
      this.slideBookNode &&
      !this.done("book") &&
      bookSlideDue(this.time, eye, forward, this.slideBookNode.getAbsolutePosition())
    ) {
      this.slideBookOut();
    }
    if (
      !this.done("balconyKnock") &&
      balconyKnockDue(this.time, eye, forward, runtime(1.2, 0.0, 1.55))
    ) {
      this.triggerBalconyKnock();
    }
    if (
      this.pictureAt &&
      !this.done("picture") &&
      pictureDue(this.time, eye, forward, this.pictureAt)
    ) {
      this.pictureFalls();
    }

    // ---- Phase 2: The Intrusion (Bathroom, Partition/Bedroom Doors, Phone Echo, Poltergeist)
    if (inBackRoom(eye) && !this.done("bathFaucet") && !phoneAnswered) {
      this.game.flags.set(studioScareFlag("bathFaucet"), true);
      this.setFaucetRunning(true);
    }
    if (inBackRoom(eye) && !this.done("partitionDoor") && !phoneAnswered) {
      this.game.flags.set(studioScareFlag("partitionDoor"), true);
      this.hauntDoorTo("haunt_partition_door", "ajar", 0.55);
    }
    if (!this.done("bedBreath") && bedBreathDue(eye, runtime(3.75, 11.4, 0.35), this.altarDone)) {
      this.triggerBedBreath();
    }
    if (
      !this.done("phantomRing") &&
      !ringing &&
      phantomRingDue(this.time, eye, this.visitedBackOrBath, this.altarDone)
    ) {
      this.triggerPhantomRing();
    }
    if (
      this.bathMirrorAt &&
      !this.done("bathMirror") &&
      bathMirrorDue(eye, forward, this.bathMirrorAt)
    ) {
      this.triggerBathMirrorHaunt();
    }
    if (this.bathTankAt && !this.done("bathTank") && bathTankDue(eye, forward, this.bathTankAt)) {
      this.triggerBathTankHaunt();
    }
    if (
      this.doors.has("haunt_bath_door") &&
      !this.done("bathDoor") &&
      bathDoorDue(
        eye,
        forward,
        this.doors.get("haunt_bath_door")!.node.getAbsolutePosition(),
        this.done("bathMirror"),
      )
    ) {
      this.game.flags.set(studioScareFlag("bathDoor"), true);
      this.hauntDoorTo("haunt_bath_door", "ajar", 0.72);
    }
    if (
      this.stoolNode &&
      !this.done("chairTurn") &&
      chairTurnDue(
        this.time,
        eye,
        forward,
        this.stoolNode.getAbsolutePosition(),
        this.visitedBackOrBath,
      )
    ) {
      this.triggerChairTurn();
    }
    if (
      this.dropBookNode &&
      !this.done("dropBook") &&
      dropBookDue(
        this.time,
        eye,
        forward,
        this.dropBookNode.getAbsolutePosition(),
        this.visitedBackOrBath,
      )
    ) {
      this.triggerBookDrop();
    }
    if (this.preay && !this.done("shadow") && !this.lights.flashing && !this.watcherActive) {
      const shot = shadowShot(this.time, eye, forward, this.figureHead);
      if (shot) this.shadowFalls(shot);
    }

    // If the player unlatched the French balcony door, a sudden storm gust eventually slams it shut!
    if (balconyOpenFrac > 0.5 && !this.done("balconySlam")) {
      this.balconyOpenSec += dt;
      if (this.balconyOpenSec >= 7.5) this.triggerBalconySlam();
    } else {
      this.balconyOpenSec = 0;
    }

    // ---- Phase 3: The Rupture (Altar collapse & Blackout doorway figure)
    if (this.altar === "waiting" && this.altarAt && game.inventory.has("satchel")) {
      this.holding += dt;
      const inside = inBackRoom(eye);
      if (inside) this.waited += dt;
      else this.outside += dt;
      const away = inside ? angleTo(eye, forward, this.altarAt) : 0;
      if (altarDue(this.holding, this.waited, away, this.outside)) this.altarFalls();
    }

    // ---- Phase 4: The Stalked Exit (Closing doors cascade, hall flash, doorframe watcher, stair footsteps)
    if (phase === 4) {
      this.stepPhase4(dt, eye, forward, kitCount === KIT.length);
    }

    // ---- Organic phase-aware directional house sounds (non-repeating pools)
    this.stepAmbientHouseSounds(phase, eye, forward, ringing);
  }

  // ---------------------------------------------------------------- Phase 1 & 2 surprising haunts

  private stepFanDrift(dt: number, eye: Vector3, forward: Vector3): void {
    const fan = this.fanNode;
    if (!fan) return;
    if (!this.done("fan") && fanDriftDue(this.time, eye, forward, fan.getAbsolutePosition())) {
      this.game.flags.set(studioScareFlag("fan"), true);
      this.fanDrifting = true;
      this.play("creak", fan.getAbsolutePosition(), 0.32);
    }
    if (!this.fanDrifting) return;
    // Freezes dead the instant Sora looks up toward the ceiling fan!
    if (angleTo(eye, forward, fan.getAbsolutePosition()) < 50) {
      this.fanDrifting = false;
      return;
    }
    const step = dt * 0.42;
    this.fanDriftAngle += step;
    fan.rotationQuaternion = Quaternion.RotationAxis(Vector3.Up(), this.fanDriftAngle);
    if (this.fanDriftAngle >= 1.95) this.fanDrifting = false;
  }

  private slideBookOut(): void {
    const book = this.slideBookNode;
    if (!book) return;
    this.game.flags.set(studioScareFlag("book"), true);
    const start = book.getAbsolutePosition().clone();
    this.play("thud", start, 0.34);
    const duration = 1.25;
    const fall: Fall = {
      time: 0,
      cues: [],
      step: (t) => {
        const k = Math.min(1, t / duration);
        const ease = 1 - (1 - k) ** 3;
        book.setAbsolutePosition(start.add(new Vector3(-0.11 * ease, 0, 0)));
        if (k >= 1) fall.step = undefined;
      },
    };
    this.falls.push(fall);
  }

  /** Three sharp urgent knocks tap directly on the exterior wet balcony glass + cold draught! */
  private triggerBalconyKnock(): void {
    this.game.flags.set(studioScareFlag("balconyKnock"), true);
    const glassAt = runtime(1.2, -0.1, 1.55);
    this.vacuum(1.4, 0.28);
    this.play("knock", glassAt, 0.82);
    this.flames?.pulseDraught(0.92, 0.15, -0.95);
    this.score().pressure(0.24);
  }

  /** Impossible solitary half-ring from the hallway phone before the altar even falls! */
  private triggerPhantomRing(): void {
    this.game.flags.set(studioScareFlag("phantomRing"), true);
    const phoneAt = runtime(2.95, 6.12, 1.47);
    const pool = this.sfx.get("phantomRing");
    if (!pool || !pool.voices.length) return;
    const voice = pool.voices[0];
    voice.spatial.position = phoneAt.clone();
    voice.volume = 0.56;
    voice.play();
    this.falls.push({
      time: 0,
      cues: [{ at: 0.58, play: () => voice.stop() }],
    });
  }

  /** Close-mic breathing directly from underneath the wooden bed + bedroom door creeps inward. */
  private triggerBedBreath(): void {
    this.game.flags.set(studioScareFlag("bedBreath"), true);
    const underBed = runtime(3.65, 11.4, 0.22);
    this.play("breath", underBed, 0.88);
    this.flames?.pulseDraught(0.7, -0.8, 0.4);
    this.hauntDoorTo("haunt_bedroom_door", "ajar", 0.48);
  }

  /** Uncanny silent repositioning: wooden stool turns toward the doorway off-camera! */
  private triggerChairTurn(): void {
    const stool = this.stoolNode;
    if (!stool) return;
    this.game.flags.set(studioScareFlag("chairTurn"), true);
    const start = stool.getAbsolutePosition().clone();
    this.play("creak", start, 0.3);
    const fall: Fall = {
      time: 0,
      cues: [],
      step: (t) => {
        const k = Math.min(1, t / 0.85);
        const ease = 1 - (1 - k) ** 2;
        stool.rotationQuaternion = Quaternion.RotationAxis(Vector3.Up(), 1.0 * ease);
        stool.setAbsolutePosition(start.add(new Vector3(0.14 * ease, 0, -0.1 * ease)));
        if (k >= 1) fall.step = undefined;
      },
    };
    this.falls.push(fall);
  }

  /** Sudden poltergeist drop: upper bookcase hardcover tumbles heavily onto the tiles behind Sora! */
  private triggerBookDrop(): void {
    const book = this.dropBookNode;
    if (!book) return;
    this.game.flags.set(studioScareFlag("dropBook"), true);
    const start = book.getAbsolutePosition().clone();
    this.vacuum(1.3, 0.24);
    const piece = this.dynamic("drop_book", book, this.box(book), 0.9, (at, speed) => {
      this.play("thud", at, Math.min(1, 0.65 + speed / 6));
      this.score().pressure(0.32);
    });
    piece.body?.setLinearVelocity(new Vector3(-1.15, 0.35, 0.15));
    piece.body?.setAngularVelocity(new Vector3(2.8, 1.4, -3.5));
    this.play("creak", start, 0.42);
    this.falls.push({
      time: 0,
      cues: [
        { at: 0.95, play: () => this.strike(piece, book.getAbsolutePosition().clone(), 3.8) },
        { at: 2.6, play: () => this.layStill(["drop_book"]) },
      ],
    });
  }

  /** Violent monsoon gust slams the unlatched French balcony door shut with thunder & candle whip! */
  private triggerBalconySlam(): void {
    this.game.flags.set(studioScareFlag("balconySlam"), true);
    const d = this.doors.get("haunt_balcony_door");
    if (!d) return;
    d.target = d.closedRad;
    d.speed = 6.2;
    d.closingLatch = "slam";
    this.flames?.pulseDraught(1.0, 0.1, -1.0);
    this.score().sting("drop", 0.62);
    this.falls.push({
      time: 0,
      cues: [
        {
          at: 0.14,
          play: () => {
            this.play("thunder", runtime(1.2, -2.0, 2.2), 0.78);
            this.lights.strike();
          },
        },
      ],
    });
  }

  // ---------------------------------------------------------------- Phase 2 bathroom haunts

  private setFaucetRunning(on: boolean): void {
    this.faucetRunning = on;
    this.bathVisuals?.setFaucetRunning(on);
    if (this.bathFaucet) {
      if (on) this.bathFaucet.play();
      else this.bathFaucet.stop();
    }
  }

  private triggerBathMirrorHaunt(): void {
    this.game.flags.set(studioScareFlag("bathMirror"), true);
    const mirrorAt = this.bathMirrorAt ?? runtime(1.72, 16.712, 1.57);
    const bulbAt = this.bathBulbAt ?? runtime(1.68, 15.45, 2.52);
    this.vacuum(1.8, 0.18);
    this.lights.flickerBathBulb(1.85);
    this.play("bulbFlicker", bulbAt, 0.82);
    this.score().pressure(0.4);

    this.falls.push({
      time: 0,
      cues: [
        {
          at: 0.34,
          play: () => {
            // Realistic human arm & slender fingers shadow creeps across the tarnished mirror glass!
            this.bathVisuals?.startMirrorArmCreep();
            this.score().sting("drop", 0.74);
            this.game.atmosphere.scare();
            const eye = this.game.camera.globalPosition;
            const behind = eye.subtract(
              this.game.camera.getDirection(Vector3.Forward()).scale(0.5),
            );
            this.play("breath", behind, 0.9);
          },
        },
        {
          at: 0.96,
          play: () => {
            // As the arm shadow drags downward and vanishes, the damp handprint emerges on the glass
            this.bathVisuals?.revealHandprint(false);
          },
        },
        {
          at: 1.55,
          play: () => {
            this.play("knock", mirrorAt.add(new Vector3(0, 0, 2.4)), 0.45);
          },
        },
      ],
    });
  }

  private triggerBathTankHaunt(): void {
    this.game.flags.set(studioScareFlag("bathTank"), true);
    const tankAt = this.bathTankAt ?? runtime(0.5, 16.24, 0.72);
    this.bathVisuals?.triggerTankRipples();
    this.play("waterStir", tankAt, 0.75);

    const dipper = this.bathDipperNode;
    if (dipper) {
      const basePos = dipper.position.clone();
      const baseRot = dipper.rotationQuaternion?.clone() ?? Quaternion.Identity();
      const fall: Fall = {
        time: 0,
        cues: [{ at: 0.18, play: () => this.play("thud", dipper.getAbsolutePosition(), 0.32) }],
        step: (t) => {
          const rock = Math.sin(t * 14) * Math.exp(-t * 2.4) * 0.16;
          const nudge = Math.min(1, t / 0.45) * 0.014;
          dipper.position.set(basePos.x + nudge, basePos.y, basePos.z);
          dipper.rotationQuaternion = baseRot.multiply(
            Quaternion.RotationAxis(new Vector3(0, 0, 1), rock),
          );
          if (t >= 1.8) fall.step = undefined;
        },
      };
      this.falls.push(fall);
    }
  }

  // ---------------------------------------------------------------- unified door animation

  private hauntDoorTo(id: StudioDoorId, pose: "open" | "ajar" | "closed", speed: number): void {
    const d = this.doors.get(id);
    if (!d) return;
    d.target = pose === "open" ? d.openRad : pose === "ajar" ? d.ajarRad : d.closedRad;
    d.speed = speed;
    d.closingLatch = pose === "closed" ? (speed >= 3.5 ? "slam" : "normal") : "none";
    this.play("doorCreak", d.node.getAbsolutePosition(), 0.74);
  }

  private stepDoors(dt: number): void {
    for (const d of this.doors.values()) {
      const diff = d.target - d.angle;
      if (Math.abs(diff) < 0.002) continue;
      const step = Math.sign(diff) * Math.min(Math.abs(diff), dt * d.speed);
      d.angle += step;
      this.applyDoorAngle(d);
      if (Math.abs(d.target - d.angle) < 0.002) {
        d.angle = d.target;
        this.applyDoorAngle(d);
        if (Math.abs(d.angle - d.closedRad) < 0.005 && d.closingLatch !== "none") {
          const at = d.node.getAbsolutePosition();
          if (d.closingLatch === "slam") this.play("doorSlam", at, 1.0);
          else this.play("doorClose", at, 0.85);
          d.closingLatch = "none";
        }
        this.lights.refreshShadows();
      }
    }
  }

  private applyDoorAngle(d: DoorState): void {
    d.node.rotationQuaternion = Quaternion.RotationAxis(Vector3.Up(), d.angle);
  }

  // ---------------------------------------------------------------- Phase 4 haunts

  private stepPhase4(dt: number, eye: Vector3, forward: Vector3, kitComplete: boolean): void {
    const blenderY = -eye.z;
    // 1. Cascading lights dying & doors quietly closing room-by-room behind Sora!
    if (!this.phase4BathKilled && blenderY < 12.8) {
      this.phase4BathKilled = true;
      this.lights.flickerBathBulb(0.85);
      this.play("bulbFlicker", this.bathBulbAt ?? runtime(1.68, 15.45, 2.52), 0.72);
      if (this.isDoorOpen("haunt_bath_door")) {
        this.hauntDoorTo("haunt_bath_door", "closed", 0.95);
      }
      this.falls.push({
        time: 0,
        cues: [
          {
            at: 0.85,
            play: () => {
              this.lights.setBathBulbLevel(0);
              if (!this.faucetRunning) this.setFaucetRunning(true);
            },
          },
        ],
      });
    }
    if (!this.phase4BedroomClosed && blenderY < 8.6) {
      this.phase4BedroomClosed = true;
      if (this.isDoorOpen("haunt_bedroom_door")) {
        this.hauntDoorTo("haunt_bedroom_door", "ajar", 0.82);
      }
    }
    if (!this.phase4HallFlickered && blenderY < 7.2) {
      this.phase4HallFlickered = true;
      this.lights.setHallBulbLevel(0.45, 2.4);
      this.play("bulbFlicker", runtime(1.95, 8.0, 2.02), 0.58);
      this.flames?.pulseDraught(0.85, -0.4, 0.9);
    }

    // 2. Brief far-hall apparition flash under the sputtering airwell bulb
    const hallAt = runtime(0.65, 9.18, 1.45);
    if (
      this.preay &&
      !this.done("hallFlash") &&
      !this.watcherActive &&
      hallFlashDue(eye, forward, hallAt, true)
    ) {
      this.game.flags.set(studioScareFlag("hallFlash"), true);
      this.lights.setHallBulbLevel(0.4, 1.1);
      this.play("bulbFlicker", runtime(1.95, 8.0, 2.02), 0.65);
      this.setFigureLayer(VISIBLE);
      const feet = runtime(0.65, 9.18, FLOOR);
      this.preay.place(feet, Math.atan2(eye.x - feet.x, eye.z - feet.z));
      this.preay.release();
      this.preay.standStill(0);
      this.preay.setEnabled(true);
      this.score().sting("drop", 0.65);
      this.hideFigureAt = this.time + 0.48;
    }

    // 3. Peripheral Doorframe Watcher: Preay peeks around the back-room doorframe when Sora looks north
    const watcherAt = runtime(1.06, 9.42, 1.45);
    if (
      this.preay &&
      this.done("hallFlash") &&
      !this.done("doorWatcher") &&
      !this.watcherActive &&
      this.hideFigureAt < 0 &&
      doorWatcherDue(eye, forward, watcherAt, true)
    ) {
      this.game.flags.set(studioScareFlag("doorWatcher"), true);
      this.watcherActive = true;
      this.watcherSlip = 0;
      this.setFigureLayer(VISIBLE);
      const startFeet = runtime(1.06, 9.46, FLOOR);
      this.preay.place(startFeet, Math.atan2(eye.x - startFeet.x, eye.z - startFeet.z));
      this.preay.release();
      this.preay.standStill(0);
      this.preay.setEnabled(true);
      this.play("creak", startFeet, 0.58);
      this.score().sting("drop", 0.55);
    }
    if (this.watcherActive && this.preay) {
      this.watcherSlip += dt;
      const slip = Math.max(0, Math.min(1, (this.watcherSlip - 0.14) / 0.42));
      const x = 1.06 + slip * 0.58;
      this.preay.position.set(-x, FLOOR, -9.46 - slip * 0.25);
      this.preay.standStill(dt);
      if (slip >= 1) {
        this.watcherActive = false;
        this.preay.setEnabled(false);
        this.setFigureLayer(UNSEEN);
      }
    }

    // 4. Final Stair-Gate Push: hurried footsteps rushing from the front studio behind Sora
    if (
      this.stairDoorAt &&
      !this.done("stairSteps") &&
      stairStepsDue(eye, this.stairDoorAt, true, kitComplete)
    ) {
      this.game.flags.set(studioScareFlag("stairSteps"), true);
      this.score().pressure(0.75);
      this.play("stepsFast", runtime(1.4, 4.4, 0.1), 0.9);
      this.falls.push({
        time: 0,
        cues: [{ at: 0.95, play: () => this.play("breath", runtime(0.95, 5.7, 1.45), 0.62) }],
      });
    }
  }

  // ---------------------------------------------------------------- ambient house director

  private stepAmbientHouseSounds(
    phase: 1 | 2 | 3 | 4,
    eye: Vector3,
    forward: Vector3,
    ringing: boolean,
  ): void {
    if (this.time < this.nextAmbientAt || !this.sfx.has("creak")) return;
    const roll = Math.random();
    if (phase === 1) {
      if (roll < 0.42) {
        this.play("knock", runtime(2.5, 13.7, 1.0), 0.55);
      } else {
        this.play(
          "creak",
          eye.add(new Vector3((Math.random() - 0.5) * 3, 1.7, (Math.random() - 0.5) * 3)),
          0.55,
        );
      }
    } else if (phase === 2) {
      if (roll < 0.35 && !inBathroom(eye)) {
        this.play("stepsSlow", runtime(1.6, 15.2, 0.1), 0.52);
      } else if (roll < 0.7) {
        this.play("knock", runtime(2.4, 14.1, 1.1), 0.62);
      } else {
        this.play("creak", eye.add(new Vector3((Math.random() - 0.5) * 2.4, 1.6, -1.8)), 0.65);
      }
    } else {
      if (!ringing && roll < 0.42) {
        const behind = eye.subtract(forward.scale(0.85)).add(new Vector3(0, 0.04, 0));
        this.play("whisper", behind, 0.62);
      } else if (roll < 0.75) {
        this.play("stepsSlow", runtime(1.3, 10.6, 0.1), 0.64);
      } else {
        this.play(
          "creak",
          eye.add(new Vector3((Math.random() - 0.5) * 2.5, 1.6, (Math.random() - 0.5) * 2.5)),
          0.68,
        );
      }
    }
    const baseGap = phase >= 3 ? 21 : phase === 2 ? 17 : 18;
    this.nextAmbientAt = this.time + baseGap + Math.random() * 13;
  }

  // ---------------------------------------------------------------- the picture

  /** Off its nail, out from the wall, after a brief silence vacuum and wood creak. */
  private pictureFalls(): void {
    this.game.flags.set(studioScareFlag("picture"), true);
    const node = this.pictureNode();
    if (!node) return;
    this.vacuum(1.6, 0.2);
    this.play("creak", node.position, 0.45);
    this.flames?.pulseDraught(0.6, 0.7, -0.5);
    this.falls.push({
      time: 0,
      cues: [
        {
          at: 0.52,
          play: () => {
            const out = this.awayFromWall(node);
            const piece = this.dynamic("picture", node, this.box(node), 1.6, (at, speed) =>
              this.pictureHits(at, speed),
            );
            piece.body?.setLinearVelocity(out.scale(0.3));
            piece.body?.setAngularVelocity(Vector3.Cross(Vector3.Up(), out).scale(1.8));
            this.play("thud", node.position, 0.35);
            this.falls.push({
              time: 0,
              cues: [
                { at: 1.2, play: () => this.strike(piece, node.position.clone(), 4) },
                {
                  at: PICTURE.settle,
                  play: () => this.layStill(["picture", ...this.named("picture_glass")]),
                },
              ],
            });
          },
        },
      ],
    });
  }

  private pictureHits(at: Vector3, speed: number): void {
    this.play("picture", at, Math.min(1, 0.45 + speed / 8));
    this.score().pressure(0.3);
    const glass = this.scene.getMeshByName("fall_picture_glass");
    if (glass) glass.isVisible = false;
    const pieces = this.brokenGlass("picture_glass", 7, at.add(new Vector3(0, 0.04, 0)), 11);
    pieces.forEach((mesh, k) => {
      const piece = this.dynamic(mesh.name, mesh, this.box(mesh), 0.02);
      const a = (k / pieces.length) * Math.PI * 2 + Math.random();
      piece.body?.setLinearVelocity(new Vector3(Math.cos(a) * 1.4, 0.4, Math.sin(a) * 1.4));
      piece.body?.setAngularVelocity(new Vector3(Math.random() * 8, Math.random() * 8, 0));
    });
  }

  private pictureNode(): TransformNode | null {
    const known = this.pieces.get("picture")?.node;
    if (known) return known;
    const group = this.group("fall_picture");
    return group ? this.detach(group, "picture") : null;
  }

  private layPicture(poses: Record<string, number[]>): void {
    const node = this.pictureNode();
    if (!node) return;
    this.pieces.set("picture", { node, body: null, speed: 0, prev: 0 });
    const glass = this.scene.getMeshByName("fall_picture_glass");
    if (glass) glass.isVisible = false;
    const pose = poses.picture;
    if (pose) this.pose(node, pose);
    else {
      const out = this.awayFromWall(node);
      node.position.set(
        node.position.x + out.x * 0.25,
        FLOOR + 0.015,
        node.position.z + out.z * 0.25,
      );
      node.rotationQuaternion = Quaternion.RotationAxis(
        Vector3.Cross(Vector3.Up(), out),
        Math.PI / 2,
      );
    }
    for (const mesh of this.brokenGlass("picture_glass", 7, node.position, 11)) {
      const kept = poses[mesh.name];
      if (kept) this.pose(mesh, kept);
      else mesh.dispose();
    }
  }

  // ---------------------------------------------------------------- the shadow

  private shadowFalls(shot: ShadowShot): void {
    const preay = this.preay;
    if (!preay) return;
    this.game.flags.set(studioScareFlag("shadow"), true);
    this.setFigureLayer(UNSEEN);
    preay.place(shot.feet, shot.yaw);
    preay.perform("reach", SHADOW.reach);
    preay.standStill(0);
    preay.setEnabled(true);
    for (const mesh of this.figure) mesh.computeWorldMatrix(true);
    this.lights.strikeFrom(
      shot.light,
      shot.wall,
      this.figure,
      { pulses: SHADOW.pulses, decay: SHADOW.decay },
      SHADOW.gain,
    );
    this.score().sting("shock", 0.82);
    this.game.atmosphere.scare();
    this.flames?.pulseDraught(0.9, 0.2, 0.95);
    this.play("thunder", shot.light);
    const eye = this.game.camera.globalPosition;
    const behind = eye.subtract(this.game.camera.getDirection(Vector3.Forward()).scale(0.6));
    this.falls.push({
      time: 0,
      cues: [{ at: 0.35, play: () => this.play("breath", behind, 0.85) }],
    });
    this.hideFigureAt = this.time + 1.2;
  }

  // ---------------------------------------------------------------- the altar

  private altarFalls(): void {
    this.altar = "falling";
    this.game.flags.set(studioScareFlag("altar"), true);
    const parts = this.altarParts();
    const score = this.score();
    this.vacuum(ALTAR.powerCut + POWER_CUT.length, 0.14);
    this.flames?.pulseDraught(1.0, 0.4, 0.9);
    const lead = score.lead("shock");
    score.sting("shock", 0.95);
    const tearAt = this.group("fall_altar_bracket")?.getAbsolutePosition().clone() ?? this.altarAt;
    let angle = 0,
      spin = 0,
      swinging = true;
    const rest = ALTAR.tilt * DEG;
    const cut = lead + ALTAR.powerCut;
    const fall: Fall = {
      time: 0,
      cues: [
        {
          at: lead,
          play: () => {
            this.play("tear", tearAt ?? Vector3.Zero());
            this.game.atmosphere.scare();
            this.flames?.extinguish("altar", true);
            this.letGo();
          },
        },
        { at: lead + 0.6, play: () => this.heartbeat(true) },
        {
          at: cut,
          play: () => {
            this.lights.powerCut();
            this.play("powerDown", this.game.camera.globalPosition);
          },
        },
        {
          at: cut + 0.52,
          play: () => {
            if (this.preay) {
              const eye = this.game.camera.globalPosition;
              const doorFeet = runtime(0.62, 9.28, FLOOR);
              this.setFigureLayer(VISIBLE);
              this.preay.place(doorFeet, Math.atan2(eye.x - doorFeet.x, eye.z - doorFeet.z));
              this.preay.release();
              this.preay.standStill(0);
              this.preay.setEnabled(true);
            }
            this.lights.strike();
            this.play("thunder", runtime(2.2, 1.0, 2.4), 0.9);
          },
        },
        {
          at: cut + Math.min(POWER_RETURN - 0.08, 1.05),
          play: () => {
            this.preay?.setEnabled(false);
            this.setFigureLayer(UNSEEN);
          },
        },
        {
          at: cut + POWER_RETURN,
          play: () => this.play("powerUp", this.game.camera.globalPosition),
        },
        {
          at: cut + POWER_CUT.length + 0.2,
          play: () => {
            this.record(this.altarNames());
            this.altar = "fallen";
            for (const done of this.altarWaiting.splice(0)) done();
          },
        },
        { at: lead + ALTAR.rest, play: () => this.layStill(this.altarNames()) },
      ],
      step: (t, dt) => {
        if (t < lead) return;
        const s = t - lead;
        const shelf = this.shelf;
        if (shelf && swinging) {
          spin += 13 * Math.cos(angle) * dt;
          angle += spin * dt;
          if (angle >= rest) {
            angle = rest;
            spin = Math.abs(spin) > 0.6 ? -spin * 0.28 : 0;
            swinging = spin !== 0;
          }
          if (!parts.lampOut && angle > 0.12) {
            parts.lampOut = true;
            this.lampOut();
          }
          shelf.body.setTargetTransform(
            shelf.node.position,
            Quaternion.RotationAxis(shelf.axis, angle),
          );
        }
        if (parts.print) {
          const tip = 0.15 * (1 - Math.exp(-s / 0.3) * Math.cos(s * 9));
          parts.print.rotationQuaternion = Quaternion.RotationAxis(new Vector3(0, 0, 1), tip);
        }
        if (!swinging && s > 2) fall.step = undefined;
      },
    };
    this.falls.push(fall);
  }

  private altarParts(): { print: TransformNode | null; lampOut: boolean } {
    const shelf = this.group("fall_altar_shelf");
    if (shelf && !this.pieces.has("altar_shelf")) {
      const node = this.detach(shelf, "altar_shelf", shelf.getAbsolutePosition().clone());
      this.pieces.set("altar_shelf", { node, body: null, speed: 0, prev: 0 });
    }
    for (const [group, name] of [
      ["fall_altar_bracket", "altar_bracket"],
      ["fall_altar_vase", "altar_vase"],
      ["fall_altar_candle_0", "altar_candle_0"],
      ["fall_altar_candle_1", "altar_candle_1"],
      ["fall_altar_candle_2", "altar_candle_2"],
      ["fall_altar_bowl", "altar_bowl"],
      ["fall_altar_lamp", "altar_lamp"],
    ] as const) {
      const node = this.group(group);
      if (node && !this.pieces.has(name))
        this.pieces.set(name, { node: this.detach(node, name), body: null, speed: 0, prev: 0 });
    }
    const print = this.group("fall_altar_print");
    let printNode = this.pieces.get("altar_print")?.node ?? null;
    if (print && !printNode) {
      printNode = this.detach(print, "altar_print", print.getAbsolutePosition().clone());
      this.pieces.set("altar_print", { node: printNode, body: null, speed: 0, prev: 0 });
    }
    return { print: printNode, lampOut: false };
  }

  private letGo(): void {
    const shelfPiece = this.pieces.get("altar_shelf");
    if (shelfPiece) {
      const node = shelfPiece.node;
      const shape = this.box(node);
      shape.material = { friction: 0.25, restitution: 0.05 };
      const body = new PhysicsBody(node, PhysicsMotionType.ANIMATED, false, this.scene);
      body.shape = shape;
      shelfPiece.body = body;
      const { min, max } = node.getHierarchyBoundingVectors(true);
      const arm = Vector3.Center(min, max).subtract(node.position);
      arm.y = 0;
      let axis = Vector3.Cross(arm, Vector3.Down()).normalize();
      const test = arm.applyRotationQuaternion(Quaternion.RotationAxis(axis, 0.3));
      if (test.y > 0) axis = axis.negate();
      this.shelf = { node, body, axis };
    }
    const awayFromWall = new Vector3(0, 0, 1);
    const kick = (name: string, v: Vector3, w: Vector3) => {
      const piece = this.pieces.get(name);
      piece?.body?.setLinearVelocity(v);
      piece?.body?.setAngularVelocity(w);
    };
    const make = (
      name: string,
      shape: (node: TransformNode) => PhysicsShape,
      mass: number,
      impact?: (at: Vector3, speed: number) => void,
    ) => {
      const piece = this.pieces.get(name);
      if (!piece) return;
      piece.node.position.y += 0.004;
      this.dynamic(name, piece.node, shape(piece.node), mass, impact);
    };
    make(
      "altar_bracket",
      (n) => this.box(n),
      0.25,
      (at, s) => this.play("thud", at, s / 5),
    );
    kick("altar_bracket", new Vector3(0, -0.4, 0.7), new Vector3(3, 1, 5));
    make(
      "altar_vase",
      (n) => this.upright(n),
      0.8,
      (at, s) => this.vaseBreaks(at, s),
    );
    for (const k of [0, 1, 2])
      make(
        `altar_candle_${k}`,
        (n) => this.box(n),
        0.35,
        (at, s) => this.play("brass", at, s / 4),
      );
    make(
      "altar_bowl",
      (n) => this.upright(n),
      0.3,
      (at, s) => this.bowlLands(at, s),
    );
    make(
      "altar_lamp",
      (n) => this.upright(n),
      0.6,
      (at, s) => this.lampBreaks(at, s),
    );
    for (const name of [
      "altar_vase",
      "altar_candle_0",
      "altar_candle_1",
      "altar_candle_2",
      "altar_bowl",
      "altar_lamp",
    ])
      kick(name, awayFromWall.scale(0.15 + Math.random() * 0.15), Vector3.Zero());
  }

  private vaseBreaks(at: Vector3, speed: number): void {
    this.play("vase", at, Math.min(1, 0.5 + speed / 8));
    const vase = this.pieces.get("altar_vase");
    if (!vase) return;
    const velocity = vase.body?.getLinearVelocity().clone() ?? Vector3.Zero();
    const centre = vase.node.getAbsolutePosition().clone();
    this.dropBody(vase);
    for (const mesh of vase.node.getChildMeshes(false)) mesh.isVisible = false;
    this.shards(vase.node).forEach((shard, k) => {
      const out = shard.position.subtract(centre);
      out.y = 0;
      const dir =
        out.lengthSquared() > 1e-6 ? out.normalize() : new Vector3(Math.cos(k), 0, Math.sin(k));
      const piece = this.dynamic(shard.name, shard, this.box(shard), 0.03);
      piece.body?.setLinearVelocity(
        velocity
          .scale(0.25)
          .add(dir.scale(1 + Math.random() * 1.4))
          .add(new Vector3(0, 0.6 + Math.random(), 0)),
      );
      piece.body?.setAngularVelocity(
        new Vector3(Math.random() - 0.5, Math.random() - 0.5, Math.random() - 0.5).scale(30),
      );
    });
  }

  private bowlLands(at: Vector3, speed: number): void {
    this.play("bowl", at, Math.min(1, 0.5 + speed / 6));
    const bowl = this.pieces.get("altar_bowl");
    if (!bowl) return;
    const velocity = bowl.body?.getLinearVelocity().clone() ?? Vector3.Zero();
    this.incense(bowl.node).forEach((stick) => {
      const piece = this.dynamic(stick.name, stick, this.stick(stick), 0.004);
      piece.body?.setLinearVelocity(
        velocity.scale(0.5).add(new Vector3(Math.random() - 0.5, 0.5, Math.random() - 0.5)),
      );
    });
  }

  private lampBreaks(at: Vector3, speed: number): void {
    this.play("glass", at, Math.min(1, 0.5 + speed / 6));
    const lamp = this.pieces.get("altar_lamp");
    if (!lamp) return;
    for (const mesh of lamp.node.getChildMeshes(false))
      if (/glass/.test(mesh.name)) mesh.isVisible = false;
    this.brokenGlass("altar_glass", 6, at.add(new Vector3(0, 0.05, 0)), 23).forEach((mesh, k) => {
      const piece = this.dynamic(mesh.name, mesh, this.box(mesh), 0.01);
      const a = k * 1.1 + Math.random();
      piece.body?.setLinearVelocity(new Vector3(Math.cos(a), 0.5, Math.sin(a)).scale(1.2));
    });
  }

  private lampOut(): void {
    this.lights.altarLampOut();
    const lamp = this.pieces.get("altar_lamp");
    for (const mesh of lamp?.node.getChildMeshes(false) ?? [])
      if (/flame/.test(mesh.name)) mesh.isVisible = false;
  }

  private altarNames(): string[] {
    return [...this.pieces.keys()].filter((name) => /^(altar_|fall_altar_vase_shard_)/.test(name));
  }

  private layAltar(poses: Record<string, number[]>): void {
    this.altarParts();
    this.lampOut();
    const vase = this.pieces.get("altar_vase");
    if (vase) {
      for (const mesh of vase.node.getChildMeshes(false)) mesh.isVisible = false;
      for (const shard of this.shards(vase.node)) this.pieces.set(shard.name, this.still(shard));
    }
    const lamp = this.pieces.get("altar_lamp");
    for (const mesh of lamp?.node.getChildMeshes(false) ?? [])
      if (/glass/.test(mesh.name)) mesh.isVisible = false;
    const bowl = this.pieces.get("altar_bowl");
    if (bowl)
      for (const stick of this.incense(bowl.node)) this.pieces.set(stick.name, this.still(stick));
    for (const mesh of this.brokenGlass("altar_glass", 6, Vector3.Zero(), 23))
      if (poses[mesh.name]) this.pieces.set(mesh.name, this.still(mesh));
      else mesh.dispose();
    for (const [name, piece] of this.pieces)
      if (/^(altar_|fall_altar_vase_shard_)/.test(name)) {
        const pose = poses[name];
        if (pose) this.pose(piece.node, pose);
        else if (name === "altar_print")
          piece.node.rotationQuaternion = Quaternion.RotationAxis(new Vector3(0, 0, 1), 0.15);
      }
  }

  // ---------------------------------------------------------------- pieces and bodies

  private shards(vase: TransformNode): TransformNode[] {
    return vase
      .getChildMeshes(false, (n) => /_shard_\d+$/.test(n.name))
      .map((mesh) => {
        const node = this.detach(mesh, mesh.name, undefined, true);
        mesh.isVisible = true;
        return node;
      });
  }

  private incense(bowl: TransformNode): TransformNode[] {
    return bowl
      .getChildMeshes(false, (n) => /^altar_incense_\d$/.test(n.name))
      .map((mesh) => this.detach(mesh, mesh.name, undefined, true));
  }

  private detach(
    group: TransformNode,
    name: string,
    pivot?: Vector3,
    alone = false,
  ): TransformNode {
    group.computeWorldMatrix(true);
    const { min, max } = group.getHierarchyBoundingVectors(true);
    const node = new TransformNode(name, this.scene);
    node.position.copyFrom(pivot ?? Vector3.Center(min, max));
    node.rotationQuaternion = Quaternion.Identity();
    node.computeWorldMatrix(true);
    if (alone) group.setParent(node);
    else for (const child of [...group.getChildren()]) (child as TransformNode).setParent(node);
    return node;
  }

  private box(node: TransformNode): PhysicsShapeBox {
    const { min, max } = node.getHierarchyBoundingVectors(true);
    const size = max.subtract(min);
    size.x = Math.max(size.x, 0.006);
    size.y = Math.max(size.y, 0.006);
    size.z = Math.max(size.z, 0.006);
    return new PhysicsShapeBox(
      Vector3.Center(min, max).subtract(node.position),
      Quaternion.Identity(),
      size,
      this.scene,
    );
  }

  private upright(node: TransformNode): PhysicsShapeCylinder {
    const { min, max } = node.getHierarchyBoundingVectors(true);
    const c = Vector3.Center(min, max).subtract(node.position);
    const radius = Math.max(max.x - min.x, max.z - min.z) / 2;
    return new PhysicsShapeCylinder(
      new Vector3(c.x, min.y - node.position.y, c.z),
      new Vector3(c.x, max.y - node.position.y, c.z),
      radius,
      this.scene,
    );
  }

  private stick(node: TransformNode): PhysicsShapeCapsule {
    const { min, max } = node.getHierarchyBoundingVectors(true);
    const half = (max.y - min.y) / 2 - 0.003;
    return new PhysicsShapeCapsule(
      new Vector3(0, -half, 0),
      new Vector3(0, half, 0),
      0.003,
      this.scene,
    );
  }

  private dynamic(
    name: string,
    node: TransformNode,
    shape: PhysicsShape,
    mass: number,
    impact?: (at: Vector3, speed: number) => void,
  ): Piece {
    shape.material = shape.material ?? { friction: 0.6, restitution: 0.15 };
    const body = new PhysicsBody(node, PhysicsMotionType.DYNAMIC, false, this.scene);
    body.shape = shape;
    body.setMassProperties({ mass });
    const piece: Piece = { node, body, speed: 0, prev: 0, impact };
    if (impact) {
      body.setCollisionCallbackEnabled(true);
      body.getCollisionObservable().add((event) => {
        if (event.type !== PhysicsEventType.COLLISION_STARTED || !piece.impact) return;
        const other = event.collider === body ? event.collidedAgainst : event.collider;
        if (this.shelf && other === this.shelf.body) return;
        const speed = Math.max(piece.speed, piece.prev);
        if (speed < HEARD) return;
        const at = event.point?.clone() ?? node.getAbsolutePosition().clone();
        this.hits.push(() => this.strike(piece, at, speed));
      });
    }
    this.pieces.set(name, piece);
    return piece;
  }

  private strike(piece: Piece, at: Vector3, speed: number): void {
    const hit = piece.impact;
    piece.impact = undefined;
    hit?.(at, speed);
  }

  private still(node: TransformNode): Piece {
    return { node, body: null, speed: 0, prev: 0 };
  }

  private dropBody(piece: Piece): void {
    piece.body?.shape?.dispose();
    piece.body?.dispose();
    piece.body = null;
  }

  private layStill(names: string[]): void {
    for (const name of names) {
      const piece = this.pieces.get(name);
      if (piece) this.dropBody(piece);
      if (name === "altar_shelf") this.shelf = null;
    }
    this.record(names);
  }

  private record(names: string[]): void {
    const flags = this.game.flags;
    const poses = decodePoses(flags.get(FALLEN_FLAG, ""));
    for (const name of names) {
      const node = this.pieces.get(name)?.node;
      if (!node || node.isDisposed()) continue;
      const q = node.rotationQuaternion ?? Quaternion.FromEulerVector(node.rotation);
      poses[name] = [node.position.x, node.position.y, node.position.z, q.x, q.y, q.z, q.w];
    }
    flags.set(FALLEN_FLAG, encodePoses(poses));
  }

  private pose(node: TransformNode, pose: number[]): void {
    node.position.set(pose[0], pose[1], pose[2]);
    node.rotationQuaternion = new Quaternion(pose[3], pose[4], pose[5], pose[6]);
  }

  private brokenGlass(name: string, count: number, at: Vector3, seed: number): Mesh[] {
    const rand = seededRandom(seed);
    const material = (this.glassMaterial ??= (() => {
      const m = new PBRMaterial("M_studio_broken_glass", this.scene);
      m.albedoColor = new Color3(0.86, 0.9, 0.9);
      m.alpha = 0.32;
      m.metallic = 0;
      m.roughness = 0.06;
      m.backFaceCulling = false;
      m.transparencyMode = PBRMaterial.PBRMATERIAL_ALPHABLEND;
      return m;
    })());
    return Array.from({ length: count }, (_, k) => {
      const corners = 3 + (rand() < 0.4 ? 1 : 0);
      const size = 0.015 + rand() * 0.03;
      const angles = Array.from({ length: corners }, () => rand() * Math.PI * 2).sort(
        (a, b) => a - b,
      );
      const ring = angles.map((a) => [
        Math.cos(a) * size * (0.4 + rand() * 0.6),
        Math.sin(a) * size * (0.4 + rand() * 0.6),
      ]);
      const t = 0.0015;
      const positions: number[] = [];
      for (const y of [t / 2, -t / 2]) for (const [x, z] of ring) positions.push(x, y, z);
      const indices: number[] = [];
      for (let i = 1; i < corners - 1; i++)
        indices.push(0, i, i + 1, corners, corners + i + 1, corners + i);
      for (let i = 0; i < corners; i++) {
        const j = (i + 1) % corners;
        indices.push(i, corners + i, j, j, corners + i, corners + j);
      }
      const data = new VertexData();
      data.positions = positions;
      data.indices = indices;
      const normals: number[] = [];
      VertexData.ComputeNormals(positions, indices, normals);
      data.normals = normals;
      const mesh = new Mesh(`${name}_${k}`, this.scene);
      data.applyToMesh(mesh);
      mesh.material = material;
      mesh.isPickable = false;
      mesh.position.set(at.x + (rand() - 0.5) * 0.12, at.y, at.z + (rand() - 0.5) * 0.12);
      mesh.rotationQuaternion = Quaternion.Identity();
      return mesh;
    });
  }

  private named(prefix: string): string[] {
    return [...this.pieces.keys()].filter((name) => name.startsWith(`${prefix}_`));
  }

  private awayFromWall(node: TransformNode): Vector3 {
    const p = node.getAbsolutePosition();
    return new Vector3(p.x < -2.3 ? 1 : -1, 0, 0);
  }

  private setFigureLayer(mask: number): void {
    for (const mesh of this.figure) mesh.layerMask = mask;
  }

  private vacuum(holdSeconds: number, factor = 0.18): void {
    const audio = this.game.audio;
    if (!audio) return;
    audio.duckAmbience(factor, 0.45);
    this.falls.push({
      time: 0,
      cues: [{ at: holdSeconds, play: () => audio.duckAmbience(1, 1.8) }],
    });
  }

  private group(name: string): TransformNode | null {
    return this.scene.getTransformNodeByName(name) ?? this.scene.getMeshByName(name);
  }

  private done(id: StudioScareId): boolean {
    return this.game.flags.get(studioScareFlag(id), false);
  }

  private play(kind: Kind, at: Vector3, loudness = 1): void {
    const pool = this.sfx.get(kind);
    if (!pool || !pool.voices.length) return;
    let index = 0;
    if (pool.voices.length > 1) {
      do {
        index = Math.floor(Math.random() * pool.voices.length);
      } while (index === pool.lastIndex);
    }
    pool.lastIndex = index;
    const voice = pool.voices[index];
    voice.spatial.position = at.clone();
    voice.volume = pool.volume * Math.max(0.15, Math.min(1, loudness));
    voice.play();
  }
}
