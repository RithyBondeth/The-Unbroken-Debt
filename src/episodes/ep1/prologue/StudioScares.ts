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
import { orientedBox } from "@/core/levelBuilder";
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
  bathFrostedDue,
  bathMirrorDue,
  bathTankDue,
  bedBreathDue,
  decodePoses,
  encodePoses,
  hallFlashDue,
  inBackRoom,
  inBathroom,
  isDoorWalkablyOpen,
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

/** Seen by no camera (cameras see 0x0FFFFFFF): the figure exists ONLY to cast real 3D shadows. */
const UNSEEN = 0x10000000;
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
  | "neckBreath"
  | "soraGasp"
  | "glassScrape"
  | "windowSlam"
  | "elecFlicker"
  | "erhuDread"
  | "throatRattle"
  | "wetStepsClose"
  | "lockedRattle"
  | "deadAirDrop"
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

export type DoorToggleResult = "opened" | "closed" | "locked";

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
  /** Game time until a haunted lock releases (0 = unlocked). */
  lockedUntil: number;
  /** Leaf bounding box in `node` local space for solid Havok collision. */
  leafMin: Vector3;
  leafMax: Vector3;
  /** Closed-doorway world centre & half-width for player anti-pinch safety. */
  closedCenter: Vector3;
  closedHalfWidth: number;
  colliderNode: TransformNode | null;
  colliderBody: PhysicsBody | null;
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
 * The studio's Asian psychological horror director, solid Havok-backed hinged door
 * system, pure shadow-and-sound apparitions (no visible ghost model, no 2D mirror cracks),
 * sacred altar omen flames/smoke, and Havok scare physics.
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
  private bathDipperNode: TransformNode | null = null;
  private bathMirrorAt: Vector3 | null = null;
  private bathTankAt: Vector3 | null = null;
  private bathFaucetAt: Vector3 | null = null;
  private bathBulbAt: Vector3 | null = null;
  private stairDoorAt: Vector3 | null = null;
  private balconyOpenSec = 0;
  private phase4BathKilled = false;
  private phase4BedroomClosed = false;
  private phase4HallFlickered = false;
  private frostedGhostActive = false;
  private mirrorGhostActive = false;
  private hallStalkerActive = false;
  private nextAmbientAt = 32;

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

    this.bathDipperNode = this.group("haunt_bath_dipper");
    this.stairDoorAt = this.group("interact_door")?.getAbsolutePosition().clone() ?? null;

    // Register all 4 interactive hinged doors with solid Havok door-leaf collision
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
        lockedUntil: 0,
        leafMin: new Vector3(Infinity, Infinity, Infinity),
        leafMax: new Vector3(-Infinity, -Infinity, -Infinity),
        closedCenter: Vector3.Zero(),
        closedHalfWidth: 0.45,
        colliderNode: null,
        colliderBody: null,
      };
      this.setupDoorCollider(state);
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

    // Restored checkpoint state: preserve fallen objects, footprints, and door state
    const poses = decodePoses(flags.get(FALLEN_FLAG, ""));
    if (this.done("picture")) this.layPicture(poses);
    if (flags.get("ep1.clock.stopped", "")) {
      this.flames.extinguish("shelf", false);
    }
    if (flags.get("ep1.phone.answered", false)) {
      this.bathVisuals.showWetFootprints(true, false);
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

  /** Loads all mastered CC0 recordings + bespoke Asian horror SFX with non-repeating pools. */
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
        { minDistance: 0.7, volume: 0.78 },
      ],
      [
        "neckBreath",
        ["sfx_ep1_taxi_neck_breath", "sfx_ep1_studio_breath"],
        sounds.whisper,
        "threat",
        1,
        { minDistance: 0.65, volume: 0.95 },
      ],
      [
        "soraGasp",
        ["sfx_ep1_taxi_sora_gasp_1", "sfx_ep1_taxi_sora_gasp_2"],
        sounds.whisper,
        "voice",
        1,
        { minDistance: 1.5, volume: 0.78 },
      ],
      [
        "glassScrape",
        ["sfx_ep1_taxi_glass_scrape"],
        sounds.creak,
        "threat",
        1,
        { minDistance: 1.4, volume: 0.92 },
      ],
      [
        "windowSlam",
        ["sfx_ep1_taxi_window_slam", "sfx_ep1_studio_door_slam"],
        sounds.doorClose,
        "threat",
        1,
        { minDistance: 2.4, volume: 0.96 },
      ],
      [
        "elecFlicker",
        ["sfx_ep1_taxi_elec_flicker", "sfx_ep1_studio_bulb_flicker"],
        sounds.powerUp,
        "sfx",
        2,
        { minDistance: 2.0, volume: 0.84 },
      ],
      ["erhuDread", [], sounds.erhuDread, "threat", 1, { minDistance: 3.5, volume: 0.86 }],
      ["throatRattle", [], sounds.throatRattle, "threat", 1, { minDistance: 1.1, volume: 0.9 }],
      ["wetStepsClose", [], sounds.wetStepsClose, "threat", 1, { minDistance: 1.5, volume: 0.92 }],
      ["lockedRattle", [], sounds.lockedRattle, "sfx", 1, { minDistance: 1.6, volume: 0.88 }],
      ["deadAirDrop", [], sounds.deadAirDrop, "threat", 1, { minDistance: 5.0, volume: 0.92 }],
      ["powerDown", [], sounds.powerDown, "threat", 1, { minDistance: 3, volume: 0.92 }],
      ["powerUp", [], sounds.powerUp, "threat", 1, { minDistance: 3, volume: 0.84 }],
      [
        "doorCreak",
        ["sfx_ep1_studio_door_creak_1", "sfx_ep1_studio_door_creak_2"],
        sounds.creak,
        "sfx",
        2,
        { minDistance: 1.8, volume: 0.78 },
      ],
      [
        "doorOpen",
        ["sfx_ep1_studio_door_open"],
        sounds.creak,
        "sfx",
        2,
        { minDistance: 1.8, volume: 0.82 },
      ],
      [
        "doorClose",
        ["sfx_ep1_studio_door_close", "sfx_ep1_studio_door_close_2"],
        sounds.doorClose,
        "sfx",
        2,
        { minDistance: 2.0, volume: 0.86 },
      ],
      [
        "doorLatch",
        ["sfx_ep1_studio_door_latch"],
        sounds.doorLatch,
        "sfx",
        2,
        { minDistance: 1.5, volume: 0.78 },
      ],
      [
        "doorSlam",
        ["sfx_ep1_studio_door_slam"],
        sounds.doorClose,
        "threat",
        2,
        { minDistance: 2.8, volume: 0.98 },
      ],
      [
        "waterStir",
        ["sfx_ep1_studio_water_stir"],
        sounds.thud,
        "sfx",
        1,
        { minDistance: 1.4, volume: 0.78 },
      ],
      [
        "bulbFlicker",
        ["sfx_ep1_studio_bulb_flicker"],
        sounds.powerUp,
        "sfx",
        1,
        { minDistance: 1.8, volume: 0.74 },
      ],
      [
        "stepsSlow",
        ["sfx_ep1_studio_steps_slow"],
        sounds.creak,
        "threat",
        1,
        { minDistance: 1.8, volume: 0.7 },
      ],
      [
        "stepsFast",
        ["sfx_ep1_studio_steps_fast"],
        sounds.creak,
        "threat",
        1,
        { minDistance: 2.5, volume: 0.92 },
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
        { minDistance: 2.2, volume: 0.72 },
      ],
      [
        "whisper",
        [
          "sfx_ep1_studio_whisper_1",
          "sfx_ep1_studio_whisper_2",
          "sfx_ep1_taxi_whisper_1",
          "sfx_ep1_taxi_whisper_2",
          "sfx_ep1_taxi_whisper_3",
        ],
        sounds.whisper,
        "threat",
        1,
        { minDistance: 0.8, volume: 0.68 },
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
      0.52,
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
          minDistance: 1.0,
          maxDistance: 11.0,
          volume: 0.64,
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
      this.setFigureLayer(UNSEEN);
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

  /** True when the given interactive studio door is swung wide enough to walk through. */
  isDoorOpen(id: StudioDoorId): boolean {
    const d = this.doors.get(id);
    if (!d) return false;
    return isDoorWalkablyOpen(d.target, d.openRad, d.closedRad);
  }

  /** True while a door's latch is temporarily held shut by a haunted encounter. */
  isDoorLocked(id: StudioDoorId): boolean {
    const d = this.doors.get(id);
    return !!d && this.time < d.lockedUntil;
  }

  /** Opens or closes any hinged door smoothly with solid physics & latch/locked audio. */
  toggleDoor(id: StudioDoorId): DoorToggleResult {
    const d = this.doors.get(id);
    if (!d) return "closed";
    const at = d.node.getAbsolutePosition();
    if (this.time < d.lockedUntil) {
      this.play("lockedRattle", at, 0.92);
      return "locked";
    }
    // If Sora opens the bathroom door while the frosted-glass silhouette is still standing
    // behind the glass, blink the bulb and vanish the figure instantly so she never clips!
    if (id === "haunt_bath_door" && this.frostedGhostActive) {
      this.clearFrostedGhost(true);
    }
    const opening = !this.isDoorOpen(id);
    d.target = opening ? d.openRad : d.closedRad;
    d.speed = id === "haunt_balcony_door" ? 1.85 : 2.45;
    if (opening) {
      d.closingLatch = "none";
      this.play("doorLatch", at, id === "haunt_balcony_door" ? 0.82 : 0.7);
      this.play("doorOpen", at, 0.82);
    } else {
      d.closingLatch = "normal";
      this.play("doorCreak", at, 0.48);
    }
    if (id === "haunt_balcony_door" && opening) {
      this.flames?.pulseDraught(0.85, 0.25, -0.95);
    }
    return opening ? "opened" : "closed";
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
    const wasRunning = this.faucetRunning;
    this.setFaucetRunning(!this.faucetRunning);
    this.play("thud", this.bathFaucetAt ?? this.game.camera.globalPosition, 0.44);
    // Turning off the haunted running tap while standing at the sink springs the 3D mirror trap!
    if (wasRunning && !this.done("bathMirror") && inBathroom(this.game.camera.globalPosition)) {
      this.falls.push({
        time: 0,
        cues: [
          {
            at: 0.35,
            play: () => {
              if (!this.done("bathMirror") && inBathroom(this.game.camera.globalPosition)) {
                this.triggerBathMirrorHaunt();
              }
            },
          },
        ],
      });
    }
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
    this.bathVisuals?.setMirrorActive(false);
    this.game.audio?.duckAmbience(1, 0.2);
  }

  /** Called by Prologue at the climax scream of Yay Mey's call: layers an in-room breath behind Sora! */
  onPhoneCallClimax(): void {
    const eye = this.game.camera.globalPosition;
    const forward = this.game.camera.getDirection(Vector3.Forward());
    const behindNeck = eye.subtract(forward.scale(0.42));
    this.play("neckBreath", behindNeck, 0.94);
    this.play("windowSlam", runtime(0.65, 9.25, 1.1), 0.72);
    this.lights.setHallBulbLevel(0.35, 1.3);
    this.flames?.pulseDraught(0.95, 0.3, 0.95);
  }

  /** Called by Prologue once Yay Mey's terrifying phone call ends (begins Phase 4). */
  onPhoneAnswered(): void {
    this.bathVisuals?.showWetFootprints(true, true);
    this.flames?.pulseDraught(0.8, 0.5, 0.85);
    this.score().pressure(0.48);
  }

  /** Plays a non-repeating real thunder crack for natural storm lightning. */
  playStormThunder(at: Vector3): void {
    this.play("thunder", at, 0.85);
  }

  // ---------------------------------------------------------------- each frame

  update(dt: number, ringing = false): void {
    const game = this.game;
    const eye = game.camera.globalPosition;
    const inBath = inBathroom(eye);
    const bathGain = Math.min(1.15, this.lights.bathBulb.intensity / 4.2) * this.lights.power;
    this.bathVisuals?.setMirrorActive(inBath, this.mirrorGhostActive, eye, bathGain);
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

    // Subtle breathing motion on the unseen shadow caster so cast shadows feel alive.
    if (
      this.preay?.isEnabled() &&
      (this.mirrorGhostActive || this.hallStalkerActive || this.frostedGhostActive)
    ) {
      this.preay.standStill(dt);
    }

    if (this.hideFigureAt >= 0 && this.time >= this.hideFigureAt) {
      this.hideFigureAt = -1;
      this.frostedGhostActive = false;
      this.mirrorGhostActive = false;
      this.hallStalkerActive = false;
      this.lights.setBathShadowCasters(null);
      this.preay?.watch(null);
      this.preay?.setEnabled(false);
      this.setFigureLayer(UNSEEN);
    }
    if (game.cutscene) return;
    this.time += dt;
    const forward = game.camera.getDirection(Vector3.Forward());

    if (inBackRoom(eye) || inBath) this.visitedBackOrBath = true;

    const kitCount = KIT.filter((k) => game.inventory.has(k)).length;
    const phoneAnswered = game.flags.get("ep1.phone.answered", false);
    const phase = studioHauntPhase({
      kitCount,
      visitedBackOrBath: this.visitedBackOrBath,
      altarDone: this.altarDone,
      phoneAnswered,
    });

    // ---- Beat 1: Front Studio — Suffocating calm broken by Partition Shadow + Double-Tap Picture Crash
    if (
      this.preay &&
      !this.done("shadow") &&
      !this.lights.flashing &&
      !this.mirrorGhostActive &&
      !this.frostedGhostActive &&
      !this.hallStalkerActive
    ) {
      const shot = shadowShot(this.time, eye, forward, this.figureHead);
      if (shot) this.shadowFalls(shot);
    }
    if (
      this.pictureAt &&
      !this.done("picture") &&
      pictureDue(this.time, eye, forward, this.pictureAt)
    ) {
      this.pictureFalls();
    }

    // If the player unlatched the French balcony door, a sudden storm gust slams it shut!
    if (balconyOpenFrac > 0.5 && !this.done("balconySlam")) {
      this.balconyOpenSec += dt;
      if (this.balconyOpenSec >= 6.5) this.triggerBalconySlam();
    } else {
      this.balconyOpenSec = 0;
    }

    // ---- Beat 2 & 3: Back Bedroom & Closed Bathroom — Running Tap, Frosted-Glass Figure & Live 3D Mirror Trap
    if (inBackRoom(eye) && !this.done("bathFaucet") && !phoneAnswered) {
      this.game.flags.set(studioScareFlag("bathFaucet"), true);
      this.setFaucetRunning(true);
    }
    const bathDoor = this.doors.get("haunt_bath_door");
    if (
      bathDoor &&
      this.preay &&
      !this.done("bathFrosted") &&
      !phoneAnswered &&
      !this.mirrorGhostActive &&
      bathFrostedDue(eye, forward, bathDoor.closedCenter, !this.isDoorOpen("haunt_bath_door"))
    ) {
      this.triggerBathFrostedSilhouette();
    }
    if (
      this.bathMirrorAt &&
      !this.done("bathMirror") &&
      !this.frostedGhostActive &&
      bathMirrorDue(eye, forward, this.bathMirrorAt)
    ) {
      this.triggerBathMirrorHaunt();
    }
    if (
      this.bathTankAt &&
      this.done("bathMirror") &&
      !this.done("bathTank") &&
      bathTankDue(eye, forward, this.bathTankAt)
    ) {
      this.triggerBathTankHaunt();
    }

    // ---- Beat 4: Back Bedroom — Sacred Altar Omen (Sideways Incense + Sequential Candle Snuff + Under-Bed Breath)
    if (!this.done("bedBreath") && bedBreathDue(eye, runtime(3.75, 11.6, 0.35), this.altarDone)) {
      this.triggerBedAndAltarOmen();
    }
    if (this.altar === "waiting" && this.altarAt && game.inventory.has("satchel")) {
      this.holding += dt;
      const inside = inBackRoom(eye);
      if (inside) this.waited += dt;
      else this.outside += dt;
      const away = inside ? angleTo(eye, forward, this.altarAt) : 0;
      if (altarDue(this.holding, this.waited, away, this.outside)) this.altarFalls();
    }

    // ---- Beat 6: Post-Call Exit — Dying Lights, Motionless Hall Stalker & Stair-Gate Final Rush
    if (phase === 4) {
      this.stepPhase4(eye, forward, kitCount === KIT.length);
    }

    // ---- Sparse, oppressive directional house dread (silence dominates!)
    this.stepAmbientHouseSounds(phase, eye, forward, ringing);
  }

  // ---------------------------------------------------------------- Beat 2: Closed Frosted-Glass Bathroom Door (Shadow + Sound Only)

  private triggerBathFrostedSilhouette(): void {
    const preay = this.preay;
    if (!preay) return;
    this.game.flags.set(studioScareFlag("bathFrosted"), true);
    this.frostedGhostActive = true;
    const doorPos = this.doors.get("haunt_bath_door")?.closedCenter ?? runtime(2.42, 14.15, 1.1);
    const glassAt = new Vector3(doorPos.x, 1.48, doorPos.z);

    // Unseen caster stands inside the bathroom, casting a looming warm 3D shadow across
    // the north-east bathroom wall visible straight through the frosted glass door panes.
    this.setFigureLayer(UNSEEN);
    preay.place(runtime(1.78, 15.42, FLOOR), 0.25);
    preay.perform("reach", 0.72);
    preay.standStill(0);
    preay.setEnabled(true);
    for (const mesh of this.figure) mesh.computeWorldMatrix(true);

    this.lights.setBathShadowCasters(this.figure);
    this.lights.strikeFrom(
      runtime(1.1, 14.36, 1.35),
      runtime(2.55, 16.72, 1.64),
      this.figure,
      { pulses: [0, 0.42, 0.92], decay: 0.28 },
      0.72,
      new Color3(1, 0.84, 0.56),
    );

    this.vacuum(1.9, 0.18);
    this.play("deadAirDrop", glassAt, 0.78);
    this.play("wetStepsClose", runtime(2.2, 14.8, FLOOR), 0.74);
    this.play("glassScrape", glassAt, 0.86);
    this.lights.flickerBathBulb(1.85);
    this.score().pressure(0.42);

    this.falls.push({
      time: 0,
      cues: [
        {
          at: 0.42,
          play: () => {
            if (this.frostedGhostActive) this.play("throatRattle", glassAt, 0.82);
          },
        },
        {
          at: 1.55,
          play: () => {
            if (this.frostedGhostActive) this.clearFrostedGhost(true);
          },
        },
      ],
    });
  }

  private clearFrostedGhost(withBlink: boolean): void {
    if (!this.frostedGhostActive) return;
    this.frostedGhostActive = false;
    this.lights.setBathShadowCasters(null);
    this.preay?.watch(null);
    this.preay?.setEnabled(false);
    this.setFigureLayer(UNSEEN);
    if (withBlink) {
      const bulbAt = this.bathBulbAt ?? runtime(1.68, 15.45, 2.52);
      this.lights.setBathBulbLevel(0);
      this.play("elecFlicker", bulbAt, 0.85);
      this.falls.push({
        time: 0,
        cues: [{ at: 0.22, play: () => this.lights.setBathBulbLevel(1) }],
      });
    }
  }

  // ---------------------------------------------------------------- Beat 3: Bathroom Shadow & Sound Trap (No Visible Ghost, No Mirror Crack)

  private triggerBathMirrorHaunt(): void {
    this.game.flags.set(studioScareFlag("bathMirror"), true);
    const mirrorAt = this.bathMirrorAt ?? runtime(1.72, 16.712, 1.57);
    const bulbAt = this.bathBulbAt ?? runtime(1.68, 15.45, 2.52);
    const bathDoor = this.doors.get("haunt_bath_door");

    // 1. Slam the solid bathroom door shut behind Sora and jam the brass latch for 3.2 seconds.
    if (bathDoor) {
      bathDoor.lockedUntil = this.time + 3.2;
      if (Math.abs(bathDoor.angle - bathDoor.closedRad) > 0.08) {
        this.hauntDoorTo("haunt_bath_door", "closed", 6.2);
      } else {
        this.play("doorSlam", bathDoor.closedCenter, 0.96);
      }
    }
    this.play("windowSlam", bathDoor?.closedCenter ?? mirrorAt, 0.84);
    this.play("deadAirDrop", mirrorAt, 0.92);
    this.vacuum(2.8, 0.1);
    this.lights.flickerBathBulb(2.65);
    this.play("elecFlicker", bulbAt, 0.86);
    this.score().pressure(0.62);

    this.falls.push({
      time: 0,
      cues: [
        {
          at: 0.24,
          play: () => {
            // 2. Unseen caster throws a looming human shadow across the closed door & south wall
            //    reflected right inside the live tarnished mirror — no visible 3D ghost model.
            if (this.preay) {
              this.mirrorGhostActive = true;
              this.setFigureLayer(UNSEEN);
              this.preay.place(runtime(1.86, 15.32, FLOOR), Math.PI);
              this.preay.release();
              this.preay.standStill(0);
              this.preay.setEnabled(true);
              for (const mesh of this.figure) mesh.computeWorldMatrix(true);
              this.lights.setBathShadowCasters(this.figure);
              this.lights.strikeFrom(
                runtime(1.42, 16.38, 1.32),
                runtime(2.26, 14.12, 1.58),
                this.figure,
                { pulses: [0, 0.32, 0.68], decay: 0.24 },
                0.65,
                new Color3(1, 0.84, 0.56),
              );
            }
            this.play("erhuDread", mirrorAt, 0.9);
            this.play("throatRattle", runtime(1.8, 15.45, 1.52), 0.88);
          },
        },
        {
          at: 1.18,
          play: () => {
            // 3. Second arc: wet footsteps rush behind Sora as a towering reaching shadow snaps
            //    across the green bathroom tiles right beside the mirror + hot breath on her neck.
            if (this.preay && this.mirrorGhostActive) {
              this.setFigureLayer(UNSEEN);
              this.preay.place(runtime(1.74, 15.62, FLOOR), Math.PI);
              this.preay.perform("reach", 0.96);
              this.preay.standStill(0);
              for (const mesh of this.figure) mesh.computeWorldMatrix(true);
              this.lights.strikeFrom(
                runtime(1.08, 14.32, 1.32),
                runtime(2.28, 16.74, 1.65),
                this.figure,
                { pulses: [0, 0.2, 0.48], decay: 0.2 },
                0.78,
                new Color3(0.95, 0.82, 0.58),
              );
            }
            this.play("wetStepsClose", runtime(1.72, 15.65, FLOOR), 0.92);
            this.play("elecFlicker", bulbAt, 0.92);
            const eye = this.game.camera.globalPosition;
            const behind = eye.subtract(
              this.game.camera.getDirection(Vector3.Forward()).scale(0.35),
            );
            this.play("neckBreath", behind, 0.96);
            this.play("soraGasp", eye, 0.82);
            this.score().sting("shock", 0.86);
            this.game.atmosphere.scare();
          },
        },
        {
          at: 2.02,
          play: () => {
            // 4. Brief bulb blackout: shadow vanishes cleanly before the dim bulb buzzes back.
            this.mirrorGhostActive = false;
            this.lights.setBathShadowCasters(null);
            this.preay?.watch(null);
            this.preay?.setEnabled(false);
            this.setFigureLayer(UNSEEN);
            this.lights.setBathBulbLevel(0);
            this.play("elecFlicker", bulbAt, 0.8);
          },
        },
        {
          at: 2.28,
          play: () => {
            this.lights.setBathBulbLevel(0.85);
            if (!this.done("bathTank")) this.triggerBathTankHaunt();
          },
        },
        {
          at: 3.22,
          play: () => {
            // Soft click as the haunted latch finally lets go
            if (bathDoor) this.play("doorLatch", bathDoor.closedCenter, 0.72);
          },
        },
      ],
    });
  }

  private triggerBathTankHaunt(): void {
    this.game.flags.set(studioScareFlag("bathTank"), true);
    const tankAt = this.bathTankAt ?? runtime(0.5, 16.24, 0.72);
    this.bathVisuals?.triggerTankRipples();
    this.play("waterStir", tankAt, 0.8);

    const dipper = this.bathDipperNode;
    if (dipper) {
      const basePos = dipper.position.clone();
      const baseRot = dipper.rotationQuaternion?.clone() ?? Quaternion.Identity();
      const fall: Fall = {
        time: 0,
        cues: [{ at: 0.18, play: () => this.play("thud", dipper.getAbsolutePosition(), 0.34) }],
        step: (t) => {
          const rock = Math.sin(t * 14) * Math.exp(-t * 2.4) * 0.14;
          const nudge = Math.min(1, t / 0.45) * 0.012;
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

  // ---------------------------------------------------------------- Beat 4a: Sacred Altar Omen & Bed Breath

  /**
   * Asian folk omen as Sora nears the bed for her satchel:
   * altar incense smoke bends horizontally toward her, the 3 altar candles snuff out
   * one by one in cold silence, and low raspy breathing rises from beneath the iron bed.
   */
  private triggerBedAndAltarOmen(): void {
    this.game.flags.set(studioScareFlag("bedBreath"), true);
    const underBed = runtime(3.65, 11.4, 0.22);
    this.vacuum(2.2, 0.2);
    this.play("deadAirDrop", underBed, 0.7);
    this.play("neckBreath", underBed, 0.92);
    this.flames?.setAltarOmenSmoke(0.95, -0.78, 0.62);
    this.flames?.pulseDraught(0.65, -0.75, 0.55);
    this.score().pressure(0.46);

    // Sequential sacred omen: the 3 altar candles die 0 -> 1 -> 2 as if someone walked past!
    this.falls.push({
      time: 0,
      cues: [
        { at: 0.15, play: () => this.flames?.extinguishAltarCandle(0, true) },
        {
          at: 0.68,
          play: () => {
            this.flames?.extinguishAltarCandle(1, true);
            this.play("throatRattle", underBed, 0.72);
          },
        },
        { at: 1.25, play: () => this.flames?.extinguishAltarCandle(2, true) },
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
    this.score().sting("drop", 0.66);
    this.falls.push({
      time: 0,
      cues: [
        {
          at: 0.14,
          play: () => {
            this.play("thunder", runtime(1.2, -2.0, 2.2), 0.82);
            this.lights.strike();
          },
        },
      ],
    });
  }

  private setFaucetRunning(on: boolean): void {
    this.faucetRunning = on;
    this.bathVisuals?.setFaucetRunning(on);
    if (this.bathFaucet) {
      if (on) this.bathFaucet.play();
      else this.bathFaucet.stop();
    }
  }

  // ---------------------------------------------------------------- solid Havok door system

  private setupDoorCollider(state: DoorState): void {
    const node = state.node;
    node.rotationQuaternion = Quaternion.RotationAxis(Vector3.Up(), state.closedRad);
    node.computeWorldMatrix(true);
    const inv = node.getWorldMatrix().clone().invert();
    const children = node.getChildMeshes(false);
    const leafMeshes = children.filter(
      (m) =>
        m.getTotalVertices() > 0 &&
        !/(knob|handle|lockplate|lockcase|keyhole|bolt|hinge|plate_|kick|espagnolette|guide)/i.test(
          m.name,
        ),
    );
    const source = leafMeshes.length ? leafMeshes : children;
    const min = new Vector3(Infinity, Infinity, Infinity);
    const max = new Vector3(-Infinity, -Infinity, -Infinity);
    const pt = new Vector3();
    for (const mesh of source) {
      if (mesh.getTotalVertices() === 0) continue;
      mesh.computeWorldMatrix(true);
      for (const v of mesh.getBoundingInfo().boundingBox.vectorsWorld) {
        Vector3.TransformCoordinatesToRef(v, inv, pt);
        min.minimizeInPlace(pt);
        max.maximizeInPlace(pt);
      }
    }
    if (!Number.isFinite(min.x)) return;

    // Guarantee a solid 10 cm slab thickness on the leaf's thin axis and 2 cm jamb overlap
    // on the wide axis so Havok's player capsule can never squeeze or tunnel through any closed/ajar door.
    const dx = max.x - min.x;
    const dz = max.z - min.z;
    if (dx < dz) {
      const pad = Math.max(0, (0.1 - dx) / 2);
      min.x -= pad;
      max.x += pad;
      min.z -= 0.01;
      max.z += 0.01;
    } else {
      const pad = Math.max(0, (0.1 - dz) / 2);
      min.z -= pad;
      max.z += pad;
      min.x -= 0.01;
      max.x += 0.01;
    }
    state.leafMin.copyFrom(min);
    state.leafMax.copyFrom(max);
    const [closedCenter, , closedExtents] = orientedBox(min, max, node.getWorldMatrix());
    state.closedCenter.copyFrom(closedCenter);
    state.closedHalfWidth = Math.max(closedExtents.x, closedExtents.z) / 2;

    if (!this.scene.getPhysicsEngine()) return;
    node.rotationQuaternion = Quaternion.RotationAxis(Vector3.Up(), state.angle);
    node.computeWorldMatrix(true);
    const [center, rotation, extents] = orientedBox(min, max, node.getWorldMatrix());
    const colNode = new TransformNode(`col_${state.id}_body`, this.scene);
    colNode.metadata = { surface: "teak" };
    colNode.position.copyFrom(center);
    colNode.rotationQuaternion = rotation.clone();
    colNode.computeWorldMatrix(true);
    const shape = new PhysicsShapeBox(Vector3.Zero(), Quaternion.Identity(), extents, this.scene);
    shape.material = { friction: 0.4, restitution: 0 };
    // STATIC + disablePreStep=false (TELEPORT) gives immovable wall priority against
    // PhysicsCharacterController and updates cleanly on every swing with zero velocity drift.
    const body = new PhysicsBody(colNode, PhysicsMotionType.STATIC, false, this.scene);
    body.shape = shape;
    body.disablePreStep = false;
    state.colliderNode = colNode;
    state.colliderBody = body;
  }

  private hauntDoorTo(id: StudioDoorId, pose: "open" | "ajar" | "closed", speed: number): void {
    const d = this.doors.get(id);
    if (!d) return;
    d.target = pose === "open" ? d.openRad : pose === "ajar" ? d.ajarRad : d.closedRad;
    d.speed = speed;
    d.closingLatch = pose === "closed" ? (speed >= 3.5 ? "slam" : "normal") : "none";
    this.play("doorCreak", d.node.getAbsolutePosition(), 0.78);
  }

  private playerInDoorway(d: DoorState): boolean {
    if (d.id === "haunt_balcony_door") return false;
    const feet = this.game.player.feet;
    return (
      Math.abs(feet.z - d.closedCenter.z) < 0.32 &&
      Math.abs(feet.x - d.closedCenter.x) < d.closedHalfWidth + 0.14
    );
  }

  private stepDoors(dt: number): void {
    for (const d of this.doors.values()) {
      const diff = d.target - d.angle;
      if (Math.abs(diff) < 0.002) continue;
      // Never pinch or crush Sora if she is standing directly inside the doorway threshold.
      const closing = Math.abs(d.target - d.closedRad) < Math.abs(d.angle - d.closedRad);
      if (closing && Math.abs(d.angle - d.closedRad) < 0.72 && this.playerInDoorway(d)) {
        continue;
      }
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
    if (d.colliderNode && d.colliderBody && Number.isFinite(d.leafMin.x)) {
      d.node.computeWorldMatrix(true);
      const [center, rotation] = orientedBox(d.leafMin, d.leafMax, d.node.getWorldMatrix());
      d.colliderNode.position.copyFrom(center);
      d.colliderNode.rotationQuaternion = rotation.clone();
      d.colliderNode.computeWorldMatrix(true);
    }
  }

  // ---------------------------------------------------------------- Beat 6: Phase 4 Post-Call Stalker & Stair Rush

  private stepPhase4(eye: Vector3, forward: Vector3, kitComplete: boolean): void {
    const blenderY = -eye.z;
    // 1. Cascading lights dying & solid doors quietly shutting behind Sora
    if (!this.phase4BathKilled && blenderY < 12.8) {
      this.phase4BathKilled = true;
      this.lights.flickerBathBulb(0.85);
      this.play("elecFlicker", this.bathBulbAt ?? runtime(1.68, 15.45, 2.52), 0.78);
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
        this.hauntDoorTo("haunt_bedroom_door", "ajar", 0.75);
      }
    }
    if (!this.phase4HallFlickered && blenderY < 7.4) {
      this.phase4HallFlickered = true;
      this.lights.setHallBulbLevel(0.42, 2.8);
      this.play("elecFlicker", runtime(1.95, 8.0, 2.02), 0.74);
      this.flames?.pulseDraught(0.9, -0.4, 0.9);
    }

    // 2. Post-call corridor shadow & creeping door (pure shadow + sound, no visible ghost model)
    const hallAt = runtime(0.65, 9.18, 1.45);
    if (
      this.preay &&
      !this.done("hallFlash") &&
      !this.mirrorGhostActive &&
      !this.frostedGhostActive &&
      !this.hallStalkerActive &&
      hallFlashDue(eye, forward, hallAt, true)
    ) {
      this.triggerHallStalker();
    }

    // 3. Final Stair-Gate Rush: sprinting bare footsteps closing behind Sora + violent partition door slam!
    if (
      this.stairDoorAt &&
      !this.done("stairSteps") &&
      stairStepsDue(eye, this.stairDoorAt, true, kitComplete)
    ) {
      this.game.flags.set(studioScareFlag("stairSteps"), true);
      this.score().pressure(0.85);
      this.play("stepsFast", runtime(1.3, 4.6, 0.1), 0.96);
      this.falls.push({
        time: 0,
        cues: [
          {
            at: 0.52,
            play: () => {
              if (this.isDoorOpen("haunt_partition_door")) {
                this.hauntDoorTo("haunt_partition_door", "closed", 6.4);
              }
              this.play("windowSlam", runtime(0.65, 6.08, 1.2), 0.92);
              this.game.atmosphere.scare();
            },
          },
          {
            at: 0.78,
            play: () => {
              const cur = this.game.camera.globalPosition;
              const behind = cur.subtract(
                this.game.camera.getDirection(Vector3.Forward()).scale(0.4),
              );
              this.play("neckBreath", behind, 0.94);
              this.play("soraGasp", cur, 0.76);
            },
          },
        ],
      });
    }
  }

  private triggerHallStalker(): void {
    const preay = this.preay;
    if (!preay) return;
    this.game.flags.set(studioScareFlag("hallFlash"), true);
    this.hallStalkerActive = true;
    const bulbAt = runtime(1.95, 8.0, 2.02);
    const farFeet = runtime(0.65, 9.18, FLOOR);

    this.vacuum(2.1, 0.16);
    this.lights.setHallBulbLevel(0.32, 2.0);
    this.play("elecFlicker", bulbAt, 0.84);
    this.play("erhuDread", farFeet, 0.9);
    this.play("throatRattle", farFeet.add(new Vector3(0, 1.45, 0)), 0.84);
    this.play("whisper", farFeet.add(new Vector3(0, 1.4, 0)), 0.72);
    if (this.isDoorOpen("haunt_bedroom_door")) {
      this.hauntDoorTo("haunt_bedroom_door", "ajar", 0.65);
    }

    this.falls.push({
      time: 0,
      cues: [
        {
          at: 0.52,
          play: () => {
            // Brief warm surge throws a towering reaching shadow across the dark hall doorway & wall
            this.setFigureLayer(UNSEEN);
            preay.place(runtime(1.18, 7.95, FLOOR), Math.PI);
            preay.perform("reach", 0.96);
            preay.standStill(0);
            preay.setEnabled(true);
            for (const mesh of this.figure) mesh.computeWorldMatrix(true);
            this.lights.strikeFrom(
              runtime(2.1, 6.45, 1.38),
              runtime(0.35, 9.2, 1.65),
              this.figure,
              { pulses: [0, 0.16], decay: 0.13 },
              1.25,
              new Color3(1, 0.78, 0.5),
            );
            this.play("elecFlicker", bulbAt, 0.92);
          },
        },
        {
          at: 0.72,
          play: () => {
            const cur = this.game.camera.globalPosition;
            const behind = cur.subtract(
              this.game.camera.getDirection(Vector3.Forward()).scale(0.38),
            );
            this.play("wetStepsClose", behind, 0.9);
            this.play("neckBreath", behind, 0.96);
            this.play("soraGasp", cur, 0.84);
            this.score().sting("shock", 0.84);
            this.game.atmosphere.scare();
          },
        },
        {
          at: 1.35,
          play: () => {
            this.hallStalkerActive = false;
            preay.watch(null);
            preay.setEnabled(false);
            this.setFigureLayer(UNSEEN);
            this.lights.setHallBulbLevel(0.55, 0.4);
          },
        },
      ],
    });
  }

  // ---------------------------------------------------------------- sparse ambient house dread

  private stepAmbientHouseSounds(
    phase: 1 | 2 | 3 | 4,
    eye: Vector3,
    forward: Vector3,
    ringing: boolean,
  ): void {
    if (this.time < this.nextAmbientAt || !this.sfx.has("creak")) return;
    const roll = Math.random();
    if (phase === 1) {
      // Phase 1 stays mostly silent: only a rare distant structural settle
      this.play(
        "creak",
        eye.add(new Vector3((Math.random() - 0.5) * 3.2, 1.8, (Math.random() - 0.5) * 3.2)),
        0.42,
      );
    } else if (phase === 2) {
      if (roll < 0.5 && !inBathroom(eye)) {
        this.play("stepsSlow", runtime(1.6, 15.2, 0.1), 0.52);
      } else {
        this.play("knock", runtime(2.4, 14.1, 1.1), 0.55);
      }
    } else {
      if (!ringing && roll < 0.45) {
        const behind = eye.subtract(forward.scale(0.85)).add(new Vector3(0, 0.04, 0));
        this.play("whisper", behind, 0.6);
      } else {
        this.play("stepsSlow", runtime(1.3, 10.6, 0.1), 0.62);
      }
    }
    const baseGap = phase >= 3 ? 32 : phase === 2 ? 36 : 44;
    this.nextAmbientAt = this.time + baseGap + Math.random() * 18;
  }

  // ---------------------------------------------------------------- Beat 1b: the picture

  /** Off its nail, out from the wall, after a brief silence vacuum and wood creak. */
  private pictureFalls(): void {
    if (this.done("picture")) return;
    this.game.flags.set(studioScareFlag("picture"), true);
    const node = this.pictureNode();
    if (!node) return;
    this.vacuum(1.6, 0.18);
    this.play("creak", node.position, 0.48);
    this.flames?.pulseDraught(0.65, 0.7, -0.5);
    this.falls.push({
      time: 0,
      cues: [
        {
          at: 0.42,
          play: () => {
            const out = this.awayFromWall(node);
            const piece = this.dynamic("picture", node, this.box(node), 1.6, (at, speed) =>
              this.pictureHits(at, speed),
            );
            piece.body?.setLinearVelocity(out.scale(0.36));
            piece.body?.setAngularVelocity(Vector3.Cross(Vector3.Up(), out).scale(2.1));
            this.play("thud", node.position, 0.4);
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
    this.play("picture", at, Math.min(1, 0.55 + speed / 7));
    this.score().pressure(0.34);
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

  // ---------------------------------------------------------------- Beat 1a: Partition Shadow + Double-Tap

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

    this.vacuum(1.8, 0.14);
    this.lights.setHallBulbLevel(0.05, 0.45);
    this.lights.strikeFrom(
      shot.light,
      shot.wall,
      this.figure,
      { pulses: SHADOW.pulses, decay: SHADOW.decay },
      SHADOW.gain,
    );
    this.score().sting("shock", 0.85);
    this.game.atmosphere.scare();
    this.flames?.pulseDraught(0.95, 0.2, 0.95);
    this.play("deadAirDrop", shot.wall, 0.88);
    this.play("erhuDread", shot.wall, 0.84);
    this.play("thunder", shot.light, 0.92);

    const eye = this.game.camera.globalPosition;
    const behind = eye.subtract(this.game.camera.getDirection(Vector3.Forward()).scale(0.38));
    this.falls.push({
      time: 0,
      cues: [
        {
          at: 0.18,
          play: () => {
            this.play("neckBreath", behind, 0.96);
            this.play("soraGasp", this.game.camera.globalPosition, 0.78);
          },
        },
        {
          at: 0.65,
          play: () => this.lights.setHallBulbLevel(1, 0),
        },
        {
          // Double-tap surprise: just as Sora spins around to an empty room, the framed picture crashes!
          at: 1.35,
          play: () => {
            if (!this.done("picture") && this.pictureAt) this.pictureFalls();
          },
        },
      ],
    });
    this.hideFigureAt = this.time + 1.15;
  }

  // ---------------------------------------------------------------- Beat 4b: Altar Collapse + Double-Strobe Blackout Approach

  private altarFalls(): void {
    this.altar = "falling";
    this.game.flags.set(studioScareFlag("altar"), true);
    const parts = this.altarParts();
    const score = this.score();
    this.vacuum(ALTAR.powerCut + POWER_CUT.length + 0.3, 0.1);
    this.flames?.pulseDraught(1.0, 0.4, 0.9);
    const lead = score.lead("shock");
    score.sting("shock", 0.96);
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
            this.play("deadAirDrop", tearAt ?? Vector3.Zero(), 0.92);
            this.game.atmosphere.scare();
            this.flames?.extinguish("altar", true);
            this.letGo();
          },
        },
        { at: lead + 0.55, play: () => this.heartbeat(true) },
        {
          at: cut,
          play: () => {
            this.lights.powerCut();
            this.play("powerDown", this.game.camera.globalPosition);
          },
        },
        {
          // Blackout Flash 1: storm lightning throws a towering reaching shadow across the north
          // bedroom wall beside the smashed altar — unseen caster, zero visible ghost model.
          at: cut + 0.36,
          play: () => {
            if (this.preay) {
              this.setFigureLayer(UNSEEN);
              this.preay.place(runtime(1.62, 11.45, FLOOR), Math.PI);
              this.preay.perform("reach", 0.94);
              this.preay.standStill(0);
              this.preay.setEnabled(true);
              for (const mesh of this.figure) mesh.computeWorldMatrix(true);
              this.lights.strikeFrom(
                runtime(2.15, 9.55, 1.42),
                runtime(1.15, 13.98, 1.62),
                this.figure,
                { pulses: [0, 0.18], decay: 0.12 },
                2.8,
              );
            } else {
              this.lights.strike();
            }
            this.play("thunder", runtime(2.2, 1.0, 2.4), 0.94);
          },
        },
        {
          // Pitch dark between flashes: wet bare footsteps sprint across the tiles straight toward Sora.
          at: cut + 0.58,
          play: () => {
            const midRoom = runtime(1.65, 11.1, FLOOR);
            this.play("wetStepsClose", midRoom, 0.96);
            this.play("throatRattle", midRoom.add(new Vector3(0, 1.45, 0)), 0.88);
          },
        },
        {
          // 1.28 s electrical snap-back flash: no visible ghost — only the bedroom door swinging ajar & erhu dread.
          at: cut + 1.26,
          play: () => {
            this.preay?.watch(null);
            this.preay?.setEnabled(false);
            this.setFigureLayer(UNSEEN);
            if (this.isDoorOpen("haunt_bedroom_door")) {
              this.hauntDoorTo("haunt_bedroom_door", "ajar", 2.8);
            }
            this.play("erhuDread", this.game.camera.globalPosition, 0.94);
            this.play("soraGasp", this.game.camera.globalPosition, 0.86);
            this.game.atmosphere.scare();
          },
        },
        {
          // Lights die for 110 ms -> cold wet breath right behind Sora's ear before power stabilizes.
          at: cut + 1.38,
          play: () => {
            const eye = this.game.camera.globalPosition;
            const behind = eye.subtract(
              this.game.camera.getDirection(Vector3.Forward()).scale(0.35),
            );
            this.play("neckBreath", behind, 0.96);
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
