import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { Axis, Space } from "@babylonjs/core/Maths/math.axis";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { Matrix, Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { PointLight } from "@babylonjs/core/Lights/pointLight";
import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import type { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { CreatePlane } from "@babylonjs/core/Meshes/Builders/planeBuilder";
import { StandardMaterial } from "@babylonjs/core/Materials/standardMaterial";
import { Texture } from "@babylonjs/core/Materials/Textures/texture";
import type { Game } from "../../../core/Game";
import type { Area } from "../../../core/AreaLoader";
import { extrasOf } from "../../../core/LevelBuilder";
import { seededRandom } from "../../../audio/synth";
import { breathOut, branchSnap, shadowVanish } from "../audio/nightSounds";
import { limitLightToRange } from "../../../render/RenderSetup";
import type { VillageLights } from "./VillageLights";
import type { Vigil } from "./Vigil";
import { ShadowFigure } from "../entities/ShadowFigure";
import { SpiritPresence } from "../entities/SpiritPresence";

/** Blender (x east, y north, z up) to Babylon. */
const at = (x: number, y: number, z = 0) => new Vector3(-x, z, -y);

/** Height of Sora's eyes above her feet (m), to find the ground under her. */
const EYE = 1.58;

/**
 * Where the figure stands at the Neak Ta shrine (the shrine at (-3.9, -34.9) faces
 * the path): at its south shoulder, where from the path the banyan's trunk is
 * straight behind it.
 */
const SHRINE_SPOT = at(-5.0, -37.2);
/** A faint cold glow on the banyan's trunk behind it, so it stands out black. */
const SHRINE_GLOW = at(-6.1, -36.5, 1.5);
/** Within this angle of the middle of her view, Sora is looking at it. */
const LOOKING = Math.cos((22 * Math.PI) / 180);

/** How a standing figure goes: what it waits for, and what it leaves behind. */
interface Standing {
  start: number;
  /** Seconds it has been looked at. */
  seenFor: number;
  /** Gone after being looked at straight on this long (or in view this long, if `inView`). */
  lookFor: number;
  inView: boolean;
  /** Gone when she comes this close (m). */
  near: number;
  /** Gone unseen after this long (s). */
  wait: number;
  sound: StaticSound | null;
  /** The jolt of a scare as it goes. */
  scare: boolean;
  /** A branch snaps beside it once she is this close and hasn't looked yet (m), or 0. */
  lure: number;
}

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
 * - At the shrine: passing the Neak Ta shrine on the path, a tall figure stands
 *   beside it; the moment Sora looks at it straight, it is gone, with a sound.
 * - The watcher: a figure stands by the gate, black against the glowing tent; it
 *   is gone when Sora raises the lamp, comes close, or looks at it too long.
 * - Behind the cloth: once the incense has died down, lightning throws a figure's
 *   shadow along the tent's back cloth while Sora is inside.
 * - The follower: on the path, steps answer Sora's own a beat late, just behind her,
 *   and stop when she stops.
 * - The watchers: the Ting Mong and the primary ancestral shrine effigy, once seen,
 *   turn to face her while she isn't looking.
 */
export class Apparitions {
  private time = 0;
  private readonly figure: Mesh;
  private readonly form: ShadowFigure;
  private readonly presence = new SpiritPresence();
  private shrineGlow = false;
  private readonly glow: PointLight;
  private readonly cloth: Mesh;
  private readonly watchers: Watcher[] = [];
  private passing: Passing | null = null;
  private readonly done = new Set<string>();
  /** The figure standing somewhere (the shrine, the gate), until it goes. */
  private standing: Standing | null = null;
  /** The follower: steps answered until `until`, or until Sora stops. */
  private follower: { until: number; lastStep: number } | null = null;
  private sounds: Record<"vanish" | "breath" | "snap", StaticSound | null> = {
    vanish: null,
    breath: null,
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
    private readonly vigil: Vigil,
  ) {
    const scene = game.scene;
    const texture = new Texture(
      `${import.meta.env.BASE_URL}assets/ep1/T_ep1_shadow_figure.png`,
      scene,
    );
    texture.hasAlpha = true;
    // The forest presence has depth and a fixed facing, so moving sideways
    // reveals its profile rather than turning a flat card toward the player.
    this.form = new ShadowFigure(scene, "neakta_shadow", 2.5);
    this.figure = this.form.root;
    this.form.setPresence(0);
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
    for (const mesh of [this.figure, this.cloth]) {
      mesh.isPickable = false;
      mesh.setEnabled(false);
    }

    this.glow = new PointLight("neakta_glow", SHRINE_GLOW, scene);
    this.glow.diffuse = new Color3(0.45, 0.55, 0.75);
    this.glow.specular = Color3.Black();
    this.glow.range = 5;
    this.glow.intensity = 0;
    this.glow.shadowEnabled = false;
    this.glow.renderPriority = 3;
    limitLightToRange(this.glow, area.container.meshes);
    // Keep this light in the shader from startup; animate intensity rather than
    // enabling a new light (and compiling scene materials) during the scare.

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

  /** Render the forest form during loading; restore its hidden encounter state afterwards. */
  prepareRenderWarmup(): () => void {
    const position = this.figure.position.clone();
    this.figure.position.copyFrom(SHRINE_SPOT);
    this.figure.position.y = 0;
    this.form.setPresence(1);
    this.figure.setEnabled(true);
    return () => {
      this.figure.position.copyFrom(position);
      this.form.setPresence(0);
      this.figure.setEnabled(false);
    };
  }

  async makeSounds(): Promise<void> {
    const audio = this.game.audio;
    if (!audio) return;
    const rate = audio.context.sampleRate;
    const one = (name: string, samples: Float32Array, minDistance: number) =>
      audio.spatialSound(name, audio.buffer(samples, rate), "sfx", Vector3.Zero(), {
        minDistance,
        maxDistance: 50,
      });
    this.sounds = {
      vanish: await one("shadow_vanish", shadowVanish(rate, seededRandom(61)), 6),
      breath: await one("shadow_breath", breathOut(rate, seededRandom(62)), 1.5),
      snap: await one("branch_snap", branchSnap(rate, seededRandom(63)), 4),
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
      this.vanish(true);
      this.cloth.setEnabled(false);
      this.follower = null;
      return;
    }
    this.time += dt;
    this.form.animate(this.time);
    const t = this.time;
    const camera = this.game.camera;
    this.eye.copyFrom(camera.globalPosition);
    camera.getDirectionToRef(Axis.Z, this.forward);
    const bx = -this.eye.x,
      by = -this.eye.z;

    // Coming up the path towards the shrine, while it is still ahead of her.
    if (by > -50 && by < -40 && Math.abs(bx) < 4) this.once("shrine", () => this.startShrine());
    if (by > -24 && by < -16 && Math.abs(bx) < 4) this.once("watcher", () => this.startWatcher());
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

    this.updatePassing(t);
    this.updateStanding(dt, by);
    this.presence.update(dt);
    this.form.setPresence(this.presence.value);
    this.figure.setEnabled(this.presence.visible);
    this.glow.intensity = this.shrineGlow ? 4 * this.presence.value : 0;
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
    if (this.done.has(id) || this.passing || this.standing || this.presence.visible) return;
    this.done.add(id);
    start();
  }

  private ground(): number {
    return this.eye.y - EYE;
  }

  private startShrine(): void {
    this.stand(SHRINE_SPOT, {
      lookFor: 0.35,
      inView: false,
      near: 5,
      wait: 40,
      sound: this.sounds.vanish,
      scare: true,
      lure: 10,
    });
    this.shrineGlow = true;
  }

  private startWatcher(): void {
    // By the gate, just off the path: from the path the glowing tent is behind it,
    // so it stands out black against the funeral's light.
    const spot = at(0.9, -9.5);
    if (Vector3.Distance(spot, this.eye) < 9) return;
    this.stand(spot, {
      lookFor: 2,
      inView: true,
      near: 7,
      wait: 25,
      sound: this.sounds.breath,
      scare: false,
      lure: 0,
    });
  }

  private stand(spot: Vector3, how: Omit<Standing, "start" | "seenFor">): void {
    spot.y = this.ground();
    this.figure.position.copyFrom(spot);
    this.figure.rotation.y = Math.atan2(this.eye.x - spot.x, this.eye.z - spot.z);
    this.shrineGlow = false;
    this.presence.show();
    this.form.setPresence(0);
    this.figure.setEnabled(true);
    this.standing = { ...how, start: this.time, seenFor: 0 };
  }

  /** `by` is how far north Sora is (Blender y). */
  private updateStanding(dt: number, by: number): void {
    const s = this.standing;
    if (!s) return;
    const to = this.figure.position.add(new Vector3(0, 1.25, 0)).subtract(this.eye);
    const distance = to.length();
    const looking = s.inView
      ? this.game.camera.isInFrustum(this.figure)
      : Vector3.Dot(to.normalize(), this.forward) > LOOKING && distance < 22;
    // Give the entrance time to resolve before a direct look dismisses it.
    if (looking && this.presence.settled) s.seenFor += dt;
    if (s.lure > 0 && distance < s.lure && s.seenFor === 0) {
      // Something moves beside the shrine: a reason to turn and look.
      this.play(this.sounds.snap, this.figure.position.add(new Vector3(0, 0.05, 0)));
      s.lure = 0;
    }
    if (distance < s.near || s.seenFor > s.lookFor || this.vigil.lampRaised) {
      // A short recession into darkness keeps the exit sharp without a one-frame pop.
      this.play(s.sound, this.figure.position);
      if (s.scare) this.game.atmosphere.scare();
      this.vanish();
    } else if (this.time - s.start > s.wait || (s.scare && by > -28))
      // Never seen: it leaves as quietly as it came.
      this.vanish();
  }

  private vanish(immediate = false): void {
    this.presence.hide(immediate);
    this.standing = null;
    if (immediate) {
      this.form.setPresence(0);
      this.figure.setEnabled(false);
      this.glow.intensity = 0;
    }
  }

  private startCloth(): void {
    // Just inside the tent's back cloth (y = 7 m), walking its length while the flash lasts.
    const y = -6.92;
    this.cloth.rotation.y = 0;
    this.lights.storm.strike();
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
    this.form.dispose();
    this.cloth.dispose(false, true);
    this.glow.dispose();
  }
}
