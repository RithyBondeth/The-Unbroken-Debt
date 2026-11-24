import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import type { AssetContainer } from "@babylonjs/core/assetContainer";
import { Axis, Space } from "@babylonjs/core/Maths/math.axis";
import { Matrix, Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import type { Game } from "@/core/Game";
import type { Area } from "@/core/areaLoader";
import { extrasOf } from "@/core/levelBuilder";
import { seededRandom } from "@/audio/synth";
import type { DreadScore } from "@/audio/DreadScore";
import { branchSnap } from "@/audio/sounds/nightSounds";
import type { VillageLights } from "./VillageLights";
import { Preay, PREAY_WALK_SPEED } from "../entities/Preay";
import { HALL, inFuneralRoom, COFFIN } from "../data/funeral";

/** Blender (x east, y north, z up) to Babylon. */
const at = (x: number, y: number, z = 0) => new Vector3(-x, z, -y);

/** Height of Sora's eyes above her feet (m), to find the ground under her. */
const EYE = 1.58;

/** Just in front of the banner hung behind the coffin (funeral_under: y1 - 0.15 = 20.85). */
const BEHIND_COFFIN_BANNER = -20.8;

/** Where her materials are compiled during loading: by the Neak Ta shrine. */
const WARMUP_SPOT = at(-5.0, -37.2);
/** How far ahead of Sora she crosses the path (m), and how far out to each side she walks. */
const CROSS_AHEAD = 8.5;
const CROSS_REACH = 4.6;
/** How long after she is seen she stays, and how close Sora may come, before she is gone. */
const CROSS_LINGER = 2.4;
const CROSS_NEAREST = 2.6;
/** How far behind Sora she walks when she follows her (m), and how long she follows. */
const FOLLOW_BEHIND = 6.5;
const FOLLOW_FOR = 14;
/** Once Sora turns and sees her behind: how long she stands there. */
const FOLLOW_SEEN = 1.4;

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

/**
 * The Preay in Act I (a woman's ghost in a bloodied white dress, ខ្មោចព្រាយ; she replaced
 * the Neak Ta's running shadows at the user's request, November 2026), kept to glimpses as
 * the tension curve asks of Act I (Beat Sheet, section 2): one each, and never a catch.
 * She moves only as a person moves: she walks, she turns her head, she stops.
 *
 * - The crossings: twice on the path, she walks across it a few metres ahead of Sora,
 *   once as Sora passes the Neak Ta shrine, once before the gate. Lightning finds her
 *   halfway across; her head comes round to Sora; she walks on into the dark.
 * - On the wall: once the incense has died down, lightning throws her shadow along the
 *   hall's back wall, behind the family altar, while Sora keeps the vigil by the coffin
 *   (the funeral moved indoors, Nov 19), and her bare steps go with it.
 * - The follower: on the path she walks behind Sora, keeping her distance, her bare
 *   steps a little out of time with Sora's, stopping when Sora stops. If Sora turns
 *   round, she is standing there, looking at her; then the lightning, and she is gone.
 * - The watchers: the Ting Mong and the primary ancestral shrine effigy, once seen,
 *   turn to face her while she isn't looking.
 */
export class Apparitions {
  /** The ground the Preay walks on in her crossings and following (the paddies' banks). */
  walksOn(ground: (x: number, z: number) => number): void {
    this.preay.ground = ground;
  }

  /** Environmental false alarms must not compete with an authored presence. */
  get active(): boolean {
    return !!this.crossing || !!this.shadow || !!this.follower;
  }

  private time = 0;
  /** The Preay herself, for the crossings and the follower (never both at once). */
  private readonly preay: Preay;
  /** Her shadow on the tent's back cloth: the same figure, pressed flat and black. */
  private readonly shade: Preay;
  private readonly shadeLayer: TransformNode;
  /** 0–1: the fright after she is seen, fading over a few seconds. */
  private fright = 0;
  private readonly watchers: Watcher[] = [];
  private crossing: { to: Vector3; beat: number; strength: number } | null = null;
  private shadow: { to: Vector3; until: number } | null = null;
  private readonly done = new Set<string>();
  /** Things timed to a crossing: the sting, the flash, the jolt. */
  private cues: { at: number; play: () => void }[] = [];
  /** The follower: where Sora has walked (for her to walk after), until when, and when seen. */
  private follower: { until: number; seenAt: number; away: number } | null = null;
  private readonly trail: Vector3[] = [];
  private sounds: Record<"snap", StaticSound | null> = { snap: null };
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
    asset: AssetContainer,
  ) {
    const scene = game.scene;
    this.preay = new Preay(asset, "preay_act1", 0.7);
    this.preay.onStep = (foot) => this.playStep(foot, 1);
    this.preay.setEnabled(false);
    // On the cloth: her shape, flat and soft, half seen through the light of the flash.
    this.shadeLayer = new TransformNode("preay_cloth_shadow", scene);
    this.shadeLayer.scaling.set(1, 1, 0.02);
    this.shade = new Preay(asset, "preay_cloth", 2.1);
    this.shade.root.parent = this.shadeLayer;
    this.shade.silhouette(0.55);
    // Her steps are outside the cloth, behind it.
    this.shade.onStep = (foot) =>
      this.playStep(new Vector3(foot.x, foot.y, this.shadeLayer.position.z - 0.65), 0.8);
    this.shadeLayer.setEnabled(false);

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
  }

  /** Render her during loading, so her shaders are ready; restore her hidden state afterwards. */
  prepareRenderWarmup(): () => void {
    this.preay.place(WARMUP_SPOT, 0);
    this.preay.standStill(0);
    this.preay.setEnabled(true);
    this.shadeLayer.position.copyFrom(WARMUP_SPOT);
    this.shade.place(Vector3.Zero(), 0);
    this.shade.standStill(0);
    this.shadeLayer.setEnabled(true);
    return () => {
      this.preay.setEnabled(false);
      this.shadeLayer.setEnabled(false);
    };
  }

  /** The act's stingers, once they are made (ActOne). */
  score: DreadScore | null = null;

  /** 0–1: how strongly she is showing herself right now. */
  get dread(): number {
    return this.fright;
  }

  async makeSounds(): Promise<void> {
    const audio = this.game.audio;
    if (!audio) return;
    const rate = audio.context.sampleRate;
    this.sounds = {
      snap: await audio.spatialSound(
        "branch_snap",
        audio.buffer(branchSnap(rate, seededRandom(63)), rate),
        "threat",
        Vector3.Zero(),
        { minDistance: 4, maxDistance: 50 },
      ),
    };
    // Bare feet in the same mud as Sora's: lighter than hers, unhurried, and the mud
    // letting go of each heel a moment later.
    const steps = this.game.footsteps;
    if (steps) {
      const takes = steps.buffers.get("mud") ?? [];
      for (const [k, buffer] of takes.entries()) {
        const take = await audio.spatialSound(`preay_step_${k}`, buffer, "sfx", Vector3.Zero(), {
          minDistance: 1.5,
          maxDistance: 45,
          volume: 0.6,
        });
        take.playbackRate = 0.92;
        this.steps.push(take);
      }
      for (const [k, buffer] of steps.suctionBuffers.entries()) {
        const suction = await audio.spatialSound(
          `preay_suction_${k}`,
          buffer,
          "sfx",
          Vector3.Zero(),
          { minDistance: 1.5, maxDistance: 45, volume: 0.35 },
        );
        suction.playbackRate = 0.9;
        this.suctions.push(suction);
      }
    }
  }

  update(dt: number): void {
    if (this.game.flags.get("ep1.act2.started", false)) {
      if (this.crossing || this.follower) this.vanish();
      this.shadeLayer.setEnabled(false);
      this.shadow = null;
      this.cues = [];
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
    if (by > -50 && by < -40 && Math.abs(bx) < 4 && ahead) this.once("shrine", () => this.cross(1));
    if (by > -24 && by < -14 && Math.abs(bx) < 4 && ahead) this.once("gate", () => this.cross(0.8));
    if (
      this.lights.tentLevel < 0.95 &&
      this.lights.flashing &&
      inFuneralRoom(this.game.player.feet)
    )
      this.once("cloth", () => this.startCloth());
    if (by > -45 && by < -12 && this.game.player.speed > 0.6)
      this.once("follower", () => this.startFollowing());

    for (const cue of this.cues) if (cue.at <= t) cue.play();
    this.cues = this.cues.filter((cue) => cue.at > t);
    this.updateCrossing(dt, t);
    this.updateShadow(dt, t);
    this.updateFollower(dt, t);
    this.fright = Math.max(0, this.fright - dt / 5);
    if (t >= this.nextWatcherCheck) {
      this.nextWatcherCheck = t + 0.25;
      this.turnWatchers(t);
    }
  }

  /** Runs `start` the first time `id` comes up. */
  private once(id: string, start: () => void): void {
    if (this.done.has(id) || this.active) return;
    this.done.add(id);
    start();
  }

  private ground(): number {
    return this.eye.y - EYE;
  }

  private flatForward(): Vector3 {
    const f = new Vector3(this.forward.x, 0, this.forward.z);
    return f.lengthSquared() > 1e-6 ? f.normalize() : new Vector3(0, 0, -1);
  }

  /** Is she somewhere Sora is looking, near enough to make out? */
  private seen(near = 22): boolean {
    const camera = this.game.camera;
    const p = this.preay.position;
    return (
      Vector3.Distance(p, this.eye) < near &&
      this.preay.figure.meshes.some((m) => camera.isInFrustum(m))
    );
  }

  /**
   * She walks across the path ahead of Sora, at her own unhurried pace, from the dark on
   * one side into the dark on the other. Lightning, the sting and a jolt land as she
   * reaches the middle; her head comes round to Sora as she passes. `strength` scales it.
   */
  private cross(strength: number): void {
    const forward = this.flatForward();
    const right = new Vector3(forward.z, 0, -forward.x);
    const centre = this.eye.add(forward.scale(CROSS_AHEAD));
    centre.y = this.ground();
    const side = Math.random() < 0.5 ? -1 : 1;
    const from = centre.add(right.scale(side * CROSS_REACH));
    const to = centre.add(right.scale(-side * CROSS_REACH)).add(forward.scale(0.8));
    this.preay.place(from, Math.atan2(to.x - from.x, to.z - from.z));
    this.preay.watch(null);
    this.preay.setEnabled(true);
    // She sets off, then walks at her pace: the middle comes after about this long.
    const beat = this.time + 0.6 + CROSS_REACH / PREAY_WALK_SPEED;
    this.crossing = { to, beat, strength };
    const lead = this.score?.lead("shock") ?? 0;
    this.cues.push(
      { at: beat - 1.1, play: () => this.preay.watch(this.eye) },
      { at: beat - lead, play: () => this.score?.sting("shock", 0.9 * strength) },
      { at: beat - 0.05, play: () => this.lights.storm.strike() },
      {
        at: beat,
        play: () => {
          this.game.atmosphere.scare();
          this.fright = Math.max(this.fright, strength);
        },
      },
      { at: beat + 0.5, play: () => this.score?.ring() },
      { at: beat + 1.6, play: () => this.preay.watch(null) },
    );
  }

  private updateCrossing(dt: number, t: number): void {
    const c = this.crossing;
    if (!c) return;
    const there = this.preay.walkTowards(dt, c.to);
    const near = Vector3.Distance(this.preay.position, this.eye) < CROSS_NEAREST;
    // Gone into the trees once she is across, or once Sora has had her look and looked
    // away; if Sora runs at her, the lightning takes her.
    if (near) this.lights.storm.strike();
    if (there || near || (t > c.beat + CROSS_LINGER && !this.seen())) this.vanish();
  }

  private startCloth(): void {
    // Pressed flat against the parinirvana banner behind the coffin (Blender y 20.85, the
    // funeral under the house), walking along it while the flash lasts.
    const side = Math.random() < 0.5 ? -1 : 1;
    this.shadeLayer.position.set(COFFIN.x, HALL.floor, BEHIND_COFFIN_BANNER);
    const from = new Vector3(side * 1.3, 0, 0),
      to = new Vector3(-side * 1.3, 0, 0);
    this.shade.place(from, Math.atan2(to.x - from.x, 0));
    this.shadeLayer.setEnabled(true);
    this.shadow = { to, until: this.time + 4.2 };
    this.lights.storm.strike();
    this.score?.sting("shock", 0.8);
  }

  private updateShadow(dt: number, t: number): void {
    const s = this.shadow;
    if (!s) return;
    const there = this.shade.walkTowards(dt, s.to);
    if (there || t > s.until) {
      this.shadeLayer.setEnabled(false);
      this.shadow = null;
    }
  }

  /** She falls in behind Sora on the path, out of sight. */
  private startFollowing(): void {
    this.trail.length = 0;
    this.follower = { until: this.time + FOLLOW_FOR, seenAt: -1, away: 0 };
  }

  private updateFollower(dt: number, t: number): void {
    const f = this.follower;
    if (!f) return;
    const feet = new Vector3(this.eye.x, this.ground(), this.eye.z);
    const last = this.trail.at(-1);
    if (!last || Vector3.Distance(last, feet) > 0.5) this.trail.push(feet);
    // Her place on Sora's trail: the last point a little way back along it.
    const spot = [...this.trail].reverse().find((p) => Vector3.Distance(p, feet) >= FOLLOW_BEHIND);
    if (!this.preay.isEnabled()) {
      // She appears only where Sora isn't looking.
      if (!spot) return;
      this.preay.place(spot, Math.atan2(feet.x - spot.x, feet.z - spot.z));
      if (this.seen(40)) return;
      this.preay.setEnabled(true);
    }
    if (f.seenAt < 0) {
      if (spot) this.preay.walkTowards(dt, spot);
      else this.preay.standStill(dt);
      this.preay.face(feet);
      if (this.seen(14)) {
        // Sora has turned round: she stops, and looks at her.
        f.seenAt = t;
        this.preay.watch(this.eye);
        this.score?.sting("drop", 0.85);
        this.fright = Math.max(this.fright, 0.7);
      } else if (t > f.until) this.vanish();
      return;
    }
    this.preay.standStill(dt);
    f.away = this.seen(30) ? 0 : f.away + dt;
    if (f.away > 0.4 || t - f.seenAt > FOLLOW_SEEN) {
      if (f.away <= 0.4) this.lights.storm.strike();
      this.vanish();
    }
  }

  /** She is gone: the crossing or the following ends. */
  private vanish(): void {
    this.preay.setEnabled(false);
    this.preay.watch(null);
    this.crossing = null;
    this.follower = null;
  }

  /** One of her bare steps in the mud, at `where`. */
  private playStep(where: Vector3, volume: number): void {
    if (this.game.flags.get("ep1.act2.started", false)) return;
    const k = this.nextStep++;
    const step = this.steps[k % Math.max(1, this.steps.length)] ?? null;
    if (step) step.volume = 0.6 * volume;
    this.play(step, where);
    // The foot drawn out of the mud a moment later.
    const suction = this.suctions[k % Math.max(1, this.suctions.length)];
    if (suction) setTimeout(() => this.play(suction, where), 90);
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
    this.preay.dispose();
    this.shade.dispose();
    this.shadeLayer.dispose();
  }
}
