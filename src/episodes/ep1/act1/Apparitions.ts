import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { Axis, Space } from "@babylonjs/core/Maths/math.axis";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { Matrix, Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import type { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { CreatePlane } from "@babylonjs/core/Meshes/Builders/planeBuilder";
import { StandardMaterial } from "@babylonjs/core/Materials/standardMaterial";
import { Texture } from "@babylonjs/core/Materials/Textures/texture";
import type { Game } from "@/core/Game";
import type { Area } from "@/core/areaLoader";
import { extrasOf } from "@/core/levelBuilder";
import { seededRandom } from "@/audio/synth";
import type { DreadScore } from "@/audio/DreadScore";
import { branchSnap } from "@/audio/sounds/nightSounds";
import { ghostRush, mudSprint } from "../audio/taxiDreadSounds";
import type { VillageLights } from "./VillageLights";
import { ShadowRunner } from "../entities/ShadowRunner";

/** Blender (x east, y north, z up) to Babylon. */
const at = (x: number, y: number, z = 0) => new Vector3(-x, z, -y);

/** Height of Sora's eyes above her feet (m), to find the ground under her. */
const EYE = 1.58;

/** Where the runner's materials are compiled during loading: by the Neak Ta shrine. */
const WARMUP_SPOT = at(-5.0, -37.2);
/** How far ahead of Sora a runner crosses (m), how far out to each side it runs, and how fast. */
const DASH_AHEAD = 8.5;
const DASH_REACH = 6.5;
const DASH_SECONDS = 0.62;
/** ghostRush's nearest point is 0.6 s in: the form crosses her view then. */
const RUSH_CLOSEST = 0.6;

/** The village figures that turn to watch Sora while she isn't looking. */
const WATCHERS = /^(tingmong_\d+|neakta_stone_watch)$/;
/** Turns each watcher makes in the act at most, and seconds between them. */
const MAX_TURNS = 3;
const TURN_GAP = 15;

interface Watcher {
  node: TransformNode;
  meshes: AbstractMesh[];
  /** Its front in its own space, from the `front` extra written in Blender. */
  front: Vector3;
  /** Seen since it last moved: it moves only after the player has had a look at it. */
  seen: boolean;
  turns: number;
  next: number;
}

/** A shadow on its way somewhere: from, to, over `duration` seconds. */
interface Passing {
  mesh: Mesh;
  from: Vector3;
  to: Vector3;
  start: number;
  duration: number;
}

/**
 * The Neak Ta's shadows in Act I (story bible, rule 16: all shadows and moving
 * statues are its forms), kept to glimpses as the tension curve asks of Act I
 * (Beat Sheet, section 2): one each, and never a catch.
 *
 * - The runners: twice on the path, a black shadow sprints across it a few
 *   metres ahead of Sora, faster than a person can run, as on the taxi ride:
 *   once as she passes the Neak Ta shrine, once before the gate. A rush of air
 *   tears past her ears, bare feet slap the mud, and lightning catches it.
 * - Behind the cloth: once the incense has died down, lightning throws a figure's
 *   shadow along the tent's back cloth while Sora is inside.
 * - The follower: on the path, steps answer Sora's own a beat late, just behind her,
 *   and stop when she stops.
 * - The watchers: the Ting Mong and the primary ancestral shrine effigy, once seen,
 *   turn to face her while she isn't looking.
 */
export class Apparitions {
  /** Environmental false alarms must not compete with an authored presence. */
  get active(): boolean {
    return !!this.passing || this.runner.running || !!this.follower;
  }

  private time = 0;
  private readonly runner: ShadowRunner;
  /** 0–1: the fright after a runner, fading over a few seconds. */
  private fright = 0;
  private readonly cloth: Mesh;
  private readonly watchers: Watcher[] = [];
  private passing: Passing | null = null;
  private readonly done = new Set<string>();
  /** Things timed to a runner: the sting, the flash, the jolt. */
  private cues: { at: number; play: () => void }[] = [];
  /** The follower: steps answered until `until`, or until Sora stops. */
  private follower: { until: number; lastStep: number } | null = null;
  private sounds: Record<"rushLeft" | "rushRight" | "sprint" | "snap", StaticSound | null> = {
    rushLeft: null,
    rushRight: null,
    sprint: null,
    snap: null,
  };
  private steps: StaticSound[] = [];
  private suctions: StaticSound[] = [];
  private nextStep = 0;
  private nextWatcherCheck = 0;
  private readonly eye = new Vector3();
  private readonly forward = new Vector3();

  constructor(
    private readonly game: Game,
    area: Area,
    private readonly lights: VillageLights,
  ) {
    const scene = game.scene;
    const texture = new Texture(
      `${import.meta.env.BASE_URL}assets/ep1/T_ep1_shadow_figure.png`,
      scene,
    );
    texture.hasAlpha = true;
    this.runner = new ShadowRunner(scene, "neakta_runner");
    // On the cloth: a soft shadow, half seen through the light of the flash.
    const soft = new StandardMaterial("M_neakta_shadow_cloth", scene);
    soft.diffuseTexture = texture;
    soft.useAlphaFromDiffuseTexture = true;
    soft.alpha = 0.55;
    soft.disableLighting = true;
    soft.emissiveColor = Color3.Black();
    soft.diffuseColor = Color3.Black();
    soft.backFaceCulling = false;
    this.cloth = CreatePlane("neakta_shadow_cloth", { width: 1.3, height: 2.6 }, scene);
    this.cloth.material = soft;
    this.cloth.isPickable = false;
    this.cloth.setEnabled(false);

    const nodes = [...area.container.transformNodes, ...area.container.meshes];
    for (const node of nodes) {
      if (!WATCHERS.test(node.name)) continue;
      const angle = Number(extrasOf(node).front);
      if (!Number.isFinite(angle)) continue;
      node.computeWorldMatrix(true);
      // Blender (cos a, sin a, 0) in Babylon, then into the node's own space.
      const world = new Vector3(-Math.cos(angle), 0, -Math.sin(angle));
      const inverse = Matrix.Invert(node.getWorldMatrix());
      const front = Vector3.TransformNormal(world, inverse).normalize();
      const meshes =
        node instanceof Mesh ? [node, ...node.getChildMeshes()] : node.getChildMeshes();
      this.watchers.push({ node, meshes, front, seen: false, turns: 0, next: 0 });
    }

    game.bus.on("player:step", () => this.onStep());
  }

  /** Render the runner during loading; restore its hidden state afterwards. */
  prepareRenderWarmup(): () => void {
    return this.runner.prepareRenderWarmup(WARMUP_SPOT);
  }

  /** The act's stingers, once they are made (ActOne). */
  score: DreadScore | null = null;

  /** 0–1: how strongly the Neak Ta is showing itself right now. */
  get dread(): number {
    return this.fright;
  }

  async makeSounds(): Promise<void> {
    const audio = this.game.audio;
    if (!audio) return;
    const rate = audio.context.sampleRate;
    // The rush tears past from one ear to the other, the way the runner goes.
    const rush = (name: string, from: number, seed: number) =>
      audio.sound(
        name,
        audio.buffer(ghostRush(rate, seededRandom(seed), from, -from), rate),
        "threat",
        1,
      );
    this.sounds = {
      rushLeft: await rush("runner_rush_left", -1, 64),
      rushRight: await rush("runner_rush_right", 1, 65),
      sprint: await audio.spatialSound(
        "runner_sprint",
        audio.buffer(mudSprint(rate, seededRandom(66)), rate),
        "threat",
        Vector3.Zero(),
        { minDistance: 2, maxDistance: 40 },
      ),
      snap: await audio.spatialSound(
        "branch_snap",
        audio.buffer(branchSnap(rate, seededRandom(63)), rate),
        "threat",
        Vector3.Zero(),
        { minDistance: 4, maxDistance: 50 },
      ),
    };
    // Steps in the same mud as Sora's, but slower and heavier, with a suction
    // every time: someone bigger, walking where she has just walked.
    const steps = this.game.footsteps;
    if (steps) {
      const takes = steps.buffers.get("mud") ?? [];
      for (const [k, buffer] of takes.entries()) {
        const take = await audio.spatialSound(`follower_step_${k}`, buffer, "sfx", Vector3.Zero(), {
          minDistance: 1.5,
          maxDistance: 50,
          volume: 0.75,
        });
        take.playbackRate = 0.8;
        this.steps.push(take);
      }
      for (const [k, buffer] of steps.suctionBuffers.entries()) {
        const suction = await audio.spatialSound(
          `follower_suction_${k}`,
          buffer,
          "sfx",
          Vector3.Zero(),
          {
            minDistance: 1.5,
            maxDistance: 50,
            volume: 0.45,
          },
        );
        suction.playbackRate = 0.75;
        this.suctions.push(suction);
      }
    }
  }

  update(dt: number): void {
    if (this.game.flags.get("ep1.act2.started", false)) {
      this.cloth.setEnabled(false);
      this.follower = null;
      this.cues = [];
      this.runner.update(dt);
      return;
    }
    this.time += dt;
    const t = this.time;
    const camera = this.game.camera;
    this.eye.copyFrom(camera.globalPosition);
    camera.getDirectionToRef(Axis.Z, this.forward);
    const bx = -this.eye.x,
      by = -this.eye.z;

    // Coming up the path towards the village, looking where she is going.
    const ahead = this.forward.z < -0.55;
    if (by > -50 && by < -40 && Math.abs(bx) < 4 && ahead) this.once("shrine", () => this.dash(1));
    if (by > -24 && by < -14 && Math.abs(bx) < 4 && ahead) this.once("gate", () => this.dash(0.8));
    if (
      this.lights.tentLevel < 0.95 &&
      this.lights.flashing &&
      bx > -4 &&
      bx < 4 &&
      by > 1 &&
      by < 7
    )
      this.once("cloth", () => this.startCloth());
    if (by > -45 && by < -12 && this.game.player.speed > 0.6)
      this.once("follower", () => (this.follower = { until: t + 9, lastStep: t }));

    for (const cue of this.cues) if (cue.at <= t) cue.play();
    this.cues = this.cues.filter((cue) => cue.at > t);
    this.updatePassing(t);
    this.runner.update(dt);
    if (this.runner.running && this.sounds.sprint)
      this.sounds.sprint.spatial.position = this.runner.position.add(new Vector3(0, 0.4, 0));
    this.fright = Math.max(0, this.fright - dt / 5);
    if (this.follower && (t > this.follower.until || t - this.follower.lastStep > 0.7)) {
      // She has stopped: one more step behind her, then nothing.
      if (t - this.follower.lastStep > 0.7) this.playStep(0);
      this.follower = null;
    }
    if (t >= this.nextWatcherCheck) {
      this.nextWatcherCheck = t + 0.25;
      this.turnWatchers(t);
    }
  }

  /** Runs `start` the first time `id` comes up. */
  private once(id: string, start: () => void): void {
    if (this.done.has(id) || this.passing || this.runner.running) return;
    this.done.add(id);
    start();
  }

  private ground(): number {
    return this.eye.y - EYE;
  }

  /**
   * A runner across the path ahead of her, left to right or right to left: the
   * rush starts first, the form crosses her view on its loudest instant, and
   * lightning, the sting and a jolt land with it. `strength` scales the scare.
   */
  private dash(strength: number): void {
    const forward = new Vector3(this.forward.x, 0, this.forward.z).normalize();
    const right = new Vector3(forward.z, 0, -forward.x);
    const centre = this.eye.add(forward.scale(DASH_AHEAD));
    centre.y = this.ground();
    const side = Math.random() < 0.5 ? -1 : 1;
    const from = centre.add(right.scale(side * DASH_REACH)).add(forward.scale(-1.2));
    const to = centre.add(right.scale(-side * DASH_REACH)).add(forward.scale(1.6));
    const delay = RUSH_CLOSEST - DASH_SECONDS / 2;
    this.runner.dash(from, to, DASH_SECONDS, delay);
    const rush = side < 0 ? this.sounds.rushLeft : this.sounds.rushRight;
    if (rush) {
      rush.volume = strength;
      rush.play();
    }
    if (this.sounds.sprint) {
      this.sounds.sprint.spatial.position = from;
      this.sounds.sprint.volume = strength;
      this.sounds.sprint.play();
    }
    const beat = this.time + RUSH_CLOSEST;
    const lead = this.score?.lead("shock") ?? 0;
    this.cues.push(
      { at: beat - lead, play: () => this.score?.sting("shock", 0.95 * strength) },
      { at: beat - 0.05, play: () => this.lights.storm.strike() },
      {
        at: beat,
        play: () => {
          this.game.atmosphere.scare();
          this.fright = Math.max(this.fright, strength);
        },
      },
      { at: beat + 0.5, play: () => this.score?.ring() },
    );
  }

  private startCloth(): void {
    // Just inside the tent's back cloth (y = 7 m), walking its length while the flash lasts.
    const y = -6.92;
    this.cloth.rotation.y = 0;
    this.lights.storm.strike();
    this.score?.sting("shock", 0.8);
    this.pass(this.cloth, new Vector3(-3.4, 1.35, y), new Vector3(3.4, 1.35, y), 2.4);
    for (let k = 0; k < 4; k++)
      setTimeout(() => this.playStep(0, at(3.4 - k * 2, 7.6)), 400 + k * 550);
  }

  private pass(mesh: Mesh, from: Vector3, to: Vector3, duration: number): void {
    mesh.position.copyFrom(from);
    mesh.setEnabled(true);
    this.passing = { mesh, from, to, start: this.time, duration };
  }

  private updatePassing(t: number): void {
    const p = this.passing;
    if (!p) return;
    const k = (t - p.start) / p.duration;
    if (k >= 1) {
      p.mesh.setEnabled(false);
      this.passing = null;
      return;
    }
    Vector3.LerpToRef(p.from, p.to, k, p.mesh.position);
  }

  private onStep(): void {
    const f = this.follower;
    if (!f) return;
    f.lastStep = this.time;
    // Answered a beat late, a few steps behind her: late enough to be someone
    // else's step, not an echo of hers.
    setTimeout(() => this.playStep(1), 260);
  }

  private playStep(variant: number, where?: Vector3): void {
    if (this.game.flags.get("ep1.act2.started", false)) return;
    const behind = this.forward.clone();
    behind.y = 0;
    behind.normalize();
    const position = where ?? this.eye.subtract(behind.scale(3.2));
    position.y = this.ground();
    const k = this.nextStep++ + variant;
    this.play(this.steps[k % Math.max(1, this.steps.length)] ?? null, position);
    // The foot dragged free of the mud a moment later.
    const suction = this.suctions[k % Math.max(1, this.suctions.length)];
    if (suction) setTimeout(() => this.play(suction, position), 90);
  }

  private play(sound: StaticSound | null, position: Vector3): void {
    if (!sound) return;
    sound.spatial.position = position.clone();
    sound.play();
  }

  /** Turns a watcher that isn't in view to face Sora, once it has been seen. */
  private turnWatchers(t: number): void {
    const camera = this.game.camera;
    for (const w of this.watchers) {
      const position = w.node.getAbsolutePosition();
      const distance = Vector3.Distance(position, this.eye);
      const inView = w.meshes.some((m) => camera.isInFrustum(m));
      if (inView) {
        if (distance < 25) w.seen = true;
        continue;
      }
      if (!w.seen || w.turns >= MAX_TURNS || t < w.next || distance < 4 || distance > 30) continue;
      const error = this.facingError(w, position);
      if (Math.abs(error) < 0.3) continue;
      w.node.rotate(Axis.Y, error, Space.WORLD);
      // Mirrored parents (the glTF root) can turn the other way: check, and correct.
      if (Math.abs(this.facingError(w, position)) > Math.abs(error))
        w.node.rotate(Axis.Y, -2 * error, Space.WORLD);
      w.turns++;
      w.seen = false;
      w.next = t + TURN_GAP;
      // Something gave it away: a branch, off where it stands.
      if (w.turns === 1) this.play(this.sounds.snap, position);
    }
  }

  /** The angle (radians) the watcher must turn about the vertical to face Sora. */
  private facingError(w: Watcher, position: Vector3): number {
    w.node.computeWorldMatrix(true);
    const front = Vector3.TransformNormal(w.front, w.node.getWorldMatrix());
    const want = Math.atan2(this.eye.x - position.x, this.eye.z - position.z);
    const has = Math.atan2(front.x, front.z);
    let d = want - has;
    while (d > Math.PI) d -= 2 * Math.PI;
    while (d < -Math.PI) d += 2 * Math.PI;
    return d;
  }

  dispose(): void {
    this.runner.dispose();
    this.cloth.dispose(false, true);
  }
}
