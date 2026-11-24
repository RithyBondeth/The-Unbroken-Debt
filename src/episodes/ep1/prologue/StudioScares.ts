import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { Quaternion, Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
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
import { thunder } from "../audio/prologueSounds";
import { POWER_CUT, POWER_RETURN } from "../data/powerCut";
import {
  ALTAR,
  FALLEN_FLAG,
  PICTURE,
  SHADOW,
  altarDue,
  angleTo,
  decodePoses,
  encodePoses,
  inBackRoom,
  pictureDue,
  shadowShot,
  studioScareFlag,
  type ShadowShot,
  type StudioScareId,
} from "../data/studioScares";
import { Preay } from "../entities/Preay";
import type { StudioLights } from "./Studio";

/** Seen by no camera (cameras see 0x0FFFFFFF): the shadow's figure is in the light's eyes only. */
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
  | "powerDown"
  | "powerUp";

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

/**
 * The studio's three scares, in place of the dancer ghost (data/studioScares.ts has the
 * rules and the user's picks): the picture that comes off the wall, the woman's shadow in
 * the lightning, the altar that tears out of the wall, which sets the storm breaking and
 * the telephone ringing.
 *
 * What falls really falls (Havok): each piece of the studio under a `fall_` empty
 * (tools/areas/ep1_area_studio.py, scare_props) is moved onto a node of its own at its
 * middle, unturned, so its body works in the game's axes whatever the glTF root does.
 * Once still, the bodies go and where everything lies is kept with the checkpoint
 * (FALLEN_FLAG), so a restored studio shows the same wreck.
 */
export class StudioScares {
  private readonly scene: Scene;
  /** Seconds Sora has been free to move (the opening and cutscenes do not count). */
  private time = 0;
  private readonly pieces = new Map<string, Piece>();
  private readonly falls: Fall[] = [];
  private readonly hits: (() => void)[] = [];
  private readonly sfx = new Map<Kind, { voices: StaticSound[]; volume: number; next: number }>();
  private heart: StaticSound | null = null;
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

    // A restored checkpoint: what has fallen lies where it came to rest.
    const poses = decodePoses(flags.get(FALLEN_FLAG, ""));
    if (this.done("picture")) this.layPicture(poses);
    if (this.done("altar")) {
      this.layAltar(poses);
      this.altar = "fallen";
    } else if (
      flags.get("ep1.studio.dancerSeen", false) ||
      flags.get("ep1.phone.answered", false)
    ) {
      // A save from before the dancer was cut, past where she stood: the altar stays up.
      this.altar = "fallen";
    }
  }

  /** The scares' sounds: the CC0 recordings where they are, synthesised stand-ins if not. */
  async makeSounds(): Promise<void> {
    const audio = this.game.audio;
    if (!audio) return;
    const rate = audio.context.sampleRate;
    const recording = (name: string) => {
      const base = `${import.meta.env.BASE_URL}assets/ep1/audio/sfx_ep1_studio_${name}`;
      return audio.load([`${base}.ogg`, `${base}.m4a`]);
    };
    type Make = (rate: number, rand: () => number) => Float32Array;
    const list: [Kind, boolean, Make, BusName, number, SpatialOptions][] = [
      ["picture", true, (r, n) => sounds.smash(r, n, 1.7), "sfx", 1, { minDistance: 2.5 }],
      ["thunder", true, thunder, "threat", 1, { minDistance: 30 }],
      ["tear", true, sounds.tear, "sfx", 1, { minDistance: 2.5 }],
      ["vase", true, (r, n) => sounds.smash(r, n, 1), "sfx", 1, { minDistance: 2.5 }],
      ["glass", true, (r, n) => sounds.smash(r, n, 1.8), "sfx", 2, { minDistance: 2, volume: 0.8 }],
      ["brass", true, sounds.clang, "sfx", 3, { minDistance: 2, volume: 0.8 }],
      ["bowl", true, sounds.bowlSpin, "sfx", 1, { minDistance: 2, volume: 0.8 }],
      ["thud", false, sounds.thud, "sfx", 2, { minDistance: 2, volume: 0.7 }],
      ["breath", false, sounds.whisper, "threat", 1, { minDistance: 0.6, volume: 0.5 }],
      ["powerDown", false, sounds.powerDown, "threat", 1, { minDistance: 3 }],
      ["powerUp", false, sounds.powerUp, "threat", 1, { minDistance: 3, volume: 0.9 }],
    ];
    await Promise.all(
      list.map(async ([kind, recorded, make, bus, voices, options], i) => {
        const buffer =
          (recorded ? await recording(kind) : null) ??
          audio.buffer(make(rate, seededRandom(1940 + i)), rate);
        const made = await Promise.all(
          Array.from({ length: voices }, (_, v) =>
            audio.spatialSound(`studio_${kind}_${v}`, buffer, bus, Vector3.Zero(), options),
          ),
        );
        this.sfx.set(kind, { voices: made, volume: made[0].volume, next: 0 });
      }),
    );
    const heart = (this.heart = await audio.sound(
      "studio_heart",
      audio.buffer(sounds.heartbeat(rate), rate),
      "sfx",
      0.55,
    ));
    heart.loop = true;
  }

  /**
   * Puts what the scares show for the first time where the warm-up views can see it (the
   * vase's shards, the broken glass, the figure in the lightning's shadows), so no shader
   * is built mid-scare. Returns what puts them away again.
   */
  prepareWarm(): () => void {
    const shown: AbstractMesh[] = [];
    if (!this.done("altar"))
      for (const mesh of this.scene.meshes)
        if (/_shard_\d+$/.test(mesh.name) && !mesh.isVisible) {
          mesh.isVisible = true;
          shown.push(mesh);
        }
    const glass = this.altarAt
      ? this.brokenGlass("warm_glass", 1, this.altarAt.add(new Vector3(0, 0.3, 0.3)), 0)
      : [];
    let unwarm: () => void = () => undefined;
    if (this.preay && !this.done("shadow")) {
      this.preay.place(new Vector3(-2.3, FLOOR, -3.5), 0);
      this.preay.standStill(0);
      this.preay.setEnabled(true);
      unwarm = this.lights.warmFlash(this.figure);
    }
    return () => {
      for (const mesh of shown) mesh.isVisible = false;
      for (const mesh of glass) mesh.dispose();
      unwarm();
      this.preay?.setEnabled(false);
    };
  }

  // ---------------------------------------------------------------- what others ask

  /** Resolves once the altar has fallen and the lights are back (at once if it has). */
  altarFallen(): Promise<void> {
    if (this.altar === "fallen") return Promise.resolve();
    return new Promise((done) => this.altarWaiting.push(done));
  }

  /** The altar has fallen, or is falling. */
  get altarDone(): boolean {
    return this.altar !== "waiting";
  }

  /** Sora's pounding heart: on as the altar falls, off once she lifts the earpiece. */
  heartbeat(on: boolean): void {
    if (!this.heart) return;
    if (on) this.heart.play();
    else this.heart.stop();
  }

  // ---------------------------------------------------------------- each frame

  update(dt: number): void {
    const game = this.game;
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
    }
    if (game.cutscene) return;
    this.time += dt;
    const eye = game.camera.globalPosition;
    const forward = game.camera.getDirection(Vector3.Forward());
    if (
      this.pictureAt &&
      !this.done("picture") &&
      pictureDue(this.time, eye, forward, this.pictureAt)
    )
      this.pictureFalls();
    if (this.preay && !this.done("shadow") && !this.lights.flashing) {
      const shot = shadowShot(this.time, eye, forward, this.figureHead);
      if (shot) this.shadowFalls(shot);
    }
    if (this.altar === "waiting" && this.altarAt && game.inventory.has("satchel")) {
      this.holding += dt;
      const inside = inBackRoom(eye);
      if (inside) this.waited += dt;
      else this.outside += dt;
      const away = inside ? angleTo(eye, forward, this.altarAt) : 0;
      if (altarDue(this.holding, this.waited, away, this.outside)) this.altarFalls();
    }
  }

  // ---------------------------------------------------------------- the picture

  /** Off its nail, out from the wall, the top leaning away: it lands on its face. */
  private pictureFalls(): void {
    this.game.flags.set(studioScareFlag("picture"), true);
    const node = this.pictureNode();
    if (!node) return;
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
        // Should it never strike anything hard enough to be heard, it is heard anyway.
        { at: 1.2, play: () => this.strike(piece, node.position.clone(), 4) },
        {
          at: PICTURE.settle,
          play: () => this.layStill(["picture", ...this.named("picture_glass")]),
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

  /** The picture on a node of its own at its middle (once). */
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
      // No pose kept: face down on the floor below the nail.
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
    // The strike is on top of the house: no gap before the thunder.
    this.score().sting("shock", 0.85);
    this.game.atmosphere.scare();
    this.play("thunder", shot.light);
    const eye = this.game.camera.globalPosition;
    const behind = eye.subtract(this.game.camera.getDirection(Vector3.Forward()).scale(0.6));
    this.falls.push({ time: 0, cues: [{ at: 0.35, play: () => this.play("breath", behind) }] });
    this.hideFigureAt = this.time + 1.2;
  }

  // ---------------------------------------------------------------- the altar

  private altarFalls(): void {
    this.altar = "falling";
    this.game.flags.set(studioScareFlag("altar"), true);
    const parts = this.altarParts();
    const score = this.score();
    const lead = score.lead("shock");
    score.sting("shock", 1);
    const tearAt = this.group("fall_altar_bracket")?.getAbsolutePosition().clone() ?? this.altarAt;
    let angle = 0,
      spin = 0,
      swinging = true;
    const rest = ALTAR.tilt * (Math.PI / 180);
    const cut = lead + ALTAR.powerCut;
    const fall: Fall = {
      time: 0,
      cues: [
        {
          at: lead,
          play: () => {
            this.play("tear", tearAt ?? Vector3.Zero());
            this.game.atmosphere.scare();
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
        { at: cut + 0.55, play: () => this.lights.strike() },
        {
          at: cut + POWER_RETURN,
          play: () => this.play("powerUp", this.game.camera.globalPosition),
        },
        {
          at: cut + POWER_CUT.length + 0.2,
          play: () => {
            // Kept now, for the checkpoint that follows; kept again once all is still.
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
        // The west end drops as the bracket tears out, swings to its stop and bounces.
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
        // The print knocked crooked on its nail, swinging and settling.
        if (parts.print) {
          const tip = 0.15 * (1 - Math.exp(-s / 0.3) * Math.cos(s * 9));
          parts.print.rotationQuaternion = Quaternion.RotationAxis(new Vector3(0, 0, 1), tip);
        }
        if (!swinging && s > 2) fall.step = undefined;
      },
    };
    this.falls.push(fall);
  }

  /** The altar's parts, each on a node of its own (the same names when laid from a save). */
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

  /** The bracket tears out, the shelf starts to swing, everything on it is let go. */
  private letGo(): void {
    const shelfPiece = this.pieces.get("altar_shelf");
    if (shelfPiece) {
      const node = shelfPiece.node;
      const shape = this.box(node);
      shape.material = { friction: 0.25, restitution: 0.05 };
      const body = new PhysicsBody(node, PhysicsMotionType.ANIMATED, false, this.scene);
      body.shape = shape;
      shelfPiece.body = body;
      // It swings on its east bracket: the arm from the hinge to the shelf's middle goes down.
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
      // Lifted clear of the shelf, so nothing starts inside it.
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
    // A shove from the tearing wall: everything starts towards the room.
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

  /** The lamp tips: its flame and its light go out. */
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

  /** Splits the vase's shards off onto nodes of their own, where they are now. */
  private shards(vase: TransformNode): TransformNode[] {
    return vase
      .getChildMeshes(false, (n) => /_shard_\d+$/.test(n.name))
      .map((mesh) => {
        const node = this.detach(mesh, mesh.name, undefined, true);
        mesh.isVisible = true;
        return node;
      });
  }

  /** The bowl's incense sticks, on nodes of their own. */
  private incense(bowl: TransformNode): TransformNode[] {
    return bowl
      .getChildMeshes(false, (n) => /^altar_incense_\d$/.test(n.name))
      .map((mesh) => this.detach(mesh, mesh.name, undefined, true));
  }

  /**
   * Moves `group`'s children (or `group` itself, `alone`) onto a new unturned node named
   * `name` at `pivot` (or their middle), each staying where it is.
   */
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

  /** A box round everything under `node` (in its own axes, unturned when this is called). */
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

  /** An upright cylinder round something round (the vase, the bowl, the lamp): it rolls. */
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

  /** A thin capsule along an incense stick. */
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
        // Bodies are not made or dropped inside the physics step: next frame.
        this.hits.push(() => this.strike(piece, at, speed));
      });
    }
    this.pieces.set(name, piece);
    return piece;
  }

  /** Its first impact, once. */
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

  /** Lays the named pieces still where they are and keeps where (FALLEN_FLAG). */
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

  /**
   * Broken glass: `count` thin slivers round `at`, always the same shapes for the same
   * `seed` (a restored checkpoint lays the same pieces). Each is its own mesh at its middle.
   */
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

  /** The names of the pieces whose names start `prefix_`. */
  private named(prefix: string): string[] {
    return [...this.pieces.keys()].filter((name) => name.startsWith(`${prefix}_`));
  }

  /** Away from the wall a piece hangs on: from the room's middle line towards it, reversed. */
  private awayFromWall(node: TransformNode): Vector3 {
    const p = node.getAbsolutePosition();
    // The rooms run north-south between the party walls (runtime x 0 to -4.6).
    return new Vector3(p.x < -2.3 ? 1 : -1, 0, 0);
  }

  private group(name: string): TransformNode | null {
    return this.scene.getTransformNodeByName(name) ?? this.scene.getMeshByName(name);
  }

  private done(id: StudioScareId): boolean {
    return this.game.flags.get(studioScareFlag(id), false);
  }

  /** Plays one of the scares' sounds at `at`, `loudness` (0–1) of its full volume. */
  private play(kind: Kind, at: Vector3, loudness = 1): void {
    const sound = this.sfx.get(kind);
    if (!sound) return;
    const voice = sound.voices[sound.next];
    sound.next = (sound.next + 1) % sound.voices.length;
    voice.spatial.position = at.clone();
    voice.volume = sound.volume * Math.max(0.15, Math.min(1, loudness));
    voice.play();
  }
}
