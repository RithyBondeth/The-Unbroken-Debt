import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import type { AnimationGroup } from "@babylonjs/core/Animations/animationGroup";
import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { LoadAssetContainerAsync } from "@babylonjs/core/Loading/sceneLoader";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { PointLight } from "@babylonjs/core/Lights/pointLight";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { Ray } from "@babylonjs/core/Culling/ray";
import type { Game } from "@/core/Game";
import { seededRandom } from "@/audio/synth";
import { heartbeat, pinpeatLure, robamSong } from "../audio/dancerSounds";

/**
 * How long she dances once seen, in seconds (the user asked for three or four): the
 * length of her music (tools/audio/make-ep1-apsara.mjs), which runs down to nothing
 * just as every light in the house goes out and takes her with it.
 */
export const DANCER_SHOWN = 3.6;
/** She comes out of the dark over this long, the light on her stuttering on. */
const FADE_IN = 0.35;
/** The light that falls on her alone: pale and cold, leaving her colours dull. */
const FILL = 1.3;
/** She appears once she is within this angle of the centre of Sora's view. */
const SEEN_COS = Math.cos((30 * Math.PI) / 180);
/** Sora is in the back room once her eye is past the doorway (runtime z; Blender y 9.45). */
const BACK_ROOM_Z = -9.45;

/**
 * The headless dancer in Sora's back room (Episode 1 prologue, November 2026): a
 * royal-ballet dancer with no head (art-source/library/scans/dancer_ghost.glb,
 * prepared by tools/characters/import-dancer-ghost.py), standing in the dark between
 * the family altar and the shutters, her hands cut off at the wrists. An Apsara
 * dance plays faintly behind the wall until Sora steps into the room (the user's
 * recording, muffled); the moment she looks that way the dancer is there,
 * dancing to it (tools/characters/rig-dancer-ghost.py: a slow robam, her weight
 * passing from foot to foot), with her music suddenly close, for
 * `DANCER_SHOWN` seconds, coming out of the dark as the light on her stutters on; the music runs down like a dying record, every light in the
 * house goes out (StudioLights.powerCut), and when they stutter back she is gone and
 * Sora's heart is pounding, until she answers the telephone. Player control is never
 * taken away.
 */
export class DancerGhost {
  private root: TransformNode | null = null;
  private meshes: AbstractMesh[] = [];
  private fill: PointLight | null = null;
  private lure: StaticSound | null = null;
  private heart: StaticSound | null = null;
  private song: StaticSound | null = null;
  private dance: AnimationGroup | null = null;
  private phase: "waiting" | "shown" | "gone" = "waiting";
  private shownFor = 0;
  private done: (() => void) | null = null;
  private readonly ray = new Ray(Vector3.Zero(), Vector3.Forward(), 1);
  private readonly chest: Vector3;
  /** Called the moment she is seen. */
  onAppear: (() => void) | null = null;
  /** Called when she vanishes: every light in the house goes out (Studio.ts). */
  onVanish: (() => void) | null = null;

  constructor(
    private readonly game: Game,
    private readonly at: Vector3,
    private readonly doorway: Vector3,
  ) {
    this.chest = at.add(new Vector3(0, 1.05, 0));
  }

  /** Loads the figure, hidden, facing the doorway. A missing file leaves only the sounds. */
  async load(): Promise<void> {
    const scene = this.game.scene;
    try {
      const asset = await LoadAssetContainerAsync(
        `${import.meta.env.BASE_URL}assets/ep1/dancer_ghost.glb`,
        scene,
      );
      asset.addAllToScene();
      // The loader starts the first clip; she waits, still, until she is seen.
      for (const group of asset.animationGroups) group.stop();
      this.dance = asset.animationGroups[0] ?? null;
      const root = (this.root = new TransformNode("dancer_ghost", scene));
      root.position.copyFrom(this.at);
      // The figure faces +Z as loaded (Blender -Y).
      const face = this.doorway.subtract(this.at);
      root.rotation.y = Math.atan2(face.x, face.z);
      for (const node of asset.rootNodes) node.parent = root;
      this.meshes = root.getChildMeshes(false);
      for (const mesh of this.meshes) {
        mesh.isPickable = false;
        mesh.receiveShadows = true;
        // Skinned: her bounds move with the dance, so she is never culled mid-step.
        mesh.alwaysSelectAsActiveMesh = true;
        if (mesh.material instanceof PBRMaterial) mesh.material.maxSimultaneousLights = 8;
      }
      root.setEnabled(false);
      // A faint light that falls on her alone: she is seen in the gloom without the
      // room around her brightening. It stays enabled at nothing when she is not there:
      // switching a light on re-checks every material's shader, a hitch at the worst moment.
      const fill = (this.fill = new PointLight(
        "dancer_ghost_fill",
        this.at.add(face.normalize().scale(0.7)).add(new Vector3(0, 1.9, 0)),
        scene,
      ));
      fill.diffuse = new Color3(0.84, 0.84, 0.78);
      fill.intensity = 0;
      fill.range = 3;
      fill.includedOnlyMeshes = [...this.meshes];
    } catch (error) {
      console.warn("[DancerGhost] figure did not load", error);
    }
  }

  /** The lure, her music and the heartbeat; the lure starts at once unless she has been seen. */
  async makeSounds(): Promise<void> {
    const audio = this.game.audio;
    if (!audio) return;
    const rate = audio.context.sampleRate;
    // The user's Apsara recording, warped (mus_ep1_apsara_*); the synthesised robam
    // stands in if it cannot be loaded.
    const recording = (name: string) => {
      const base = `${import.meta.env.BASE_URL}assets/ep1/audio/${name}`;
      return audio.load([`${base}.ogg`, `${base}.m4a`]);
    };
    const [lureFile, songFile] = await Promise.all([
      recording("mus_ep1_apsara_lure"),
      recording("mus_ep1_apsara_ghost"),
    ]);
    const [lure, heart, song] = await Promise.all([
      audio.spatialSound(
        "dancer_lure",
        lureFile ?? audio.buffer(pinpeatLure(rate, seededRandom(1907)), rate),
        "sfx",
        this.at.add(new Vector3(0, 1.2, 0)),
        { loop: true, minDistance: 1.2, maxDistance: 16, volume: lureFile ? 0.55 : 0.32 },
      ),
      audio.sound("dancer_heart", audio.buffer(heartbeat(rate), rate), "sfx", 0.55),
      audio.spatialSound(
        "dancer_robam",
        songFile ?? audio.buffer(robamSong(rate, seededRandom(1909)), rate),
        "threat",
        this.chest,
        { minDistance: 4, volume: 1 },
      ),
    ]);
    this.song = song;
    this.lure = lure;
    this.heart = heart;
    heart.loop = true;
    if (this.phase === "waiting") lure.play();
  }

  /**
   * Draws her for a few frames while the screen is still black (before the player
   * presses Enter), half-faded and whole, dancing and lit, so every shader, pipeline and
   * skinning buffer she needs exists before the scare: built on the spot they stalled
   * the frame she appeared on. She is drawn even behind the walls
   * (alwaysSelectAsActiveMesh), so where the camera is does not matter.
   */
  async warm(): Promise<void> {
    const root = this.root;
    if (!root || this.phase !== "waiting") return;
    const frames = (n: number) =>
      new Promise<void>((done) => {
        const observer = this.game.scene.onAfterRenderObservable.add(() => {
          if (--n > 0) return;
          observer.remove();
          done();
        });
      });
    root.setEnabled(true);
    if (this.fill) this.fill.intensity = 0.001;
    this.dance?.start(true, 1, this.dance.from, this.dance.to);
    for (const visibility of [0.5, 1]) {
      for (const mesh of this.meshes) mesh.visibility = visibility;
      await frames(3);
    }
    this.dance?.stop();
    if (this.phase === "waiting") root.setEnabled(false);
    if (this.fill && this.phase === "waiting") this.fill.intensity = 0;
  }

  /** Resolves when she has been seen and is gone again. */
  seen(): Promise<void> {
    if (this.phase === "gone") return Promise.resolve();
    return new Promise((resolve) => (this.done = resolve));
  }

  /** Sora's pounding heart: on after the dancer, off once she lifts the earpiece. */
  heartbeat(on: boolean): void {
    if (!this.heart) return;
    if (on) this.heart.play();
    else this.heart.stop();
  }

  /** For a restored checkpoint: she has been and gone; no lure. */
  skip(): void {
    this.phase = "gone";
    this.lure?.stop();
  }

  update(dt: number): void {
    if (this.phase === "waiting") {
      if (this.done && this.sees()) this.appear();
      return;
    }
    if (this.phase !== "shown") return;
    this.shownFor += dt;
    const t = this.shownFor;
    // Out of the dark, eased: she is there before the eye can say when she came.
    const come = Math.min(1, t / FADE_IN);
    const eased = come * come * (3 - 2 * come);
    for (const mesh of this.meshes) mesh.visibility = eased;
    // The light on her stutters on like a failing bulb, then trembles more and more as
    // the music dies.
    const unrest = Math.min(1, t / DANCER_SHOWN);
    const tremble =
      1 - (0.12 + 0.45 * unrest * unrest) * Math.abs(Math.sin(t * 23) * Math.sin(t * 7.1));
    const stutter = come < 1 ? (Math.sin(t * 90) > -0.2 ? 1 : 0.25) : 1;
    if (this.fill) this.fill.intensity = FILL * eased * tremble * stutter;
    if (t >= DANCER_SHOWN) this.vanish();
  }

  /** Sora is in the back room, looking her way, with nothing between them. */
  private sees(): boolean {
    const camera = this.game.camera;
    const eye = camera.globalPosition;
    if (eye.z > BACK_ROOM_Z) return false;
    const to = this.chest.subtract(eye);
    const distance = to.length();
    to.scaleInPlace(1 / distance);
    if (Vector3.Dot(camera.getDirection(Vector3.Forward()), to) < SEEN_COS) return false;
    this.ray.origin.copyFrom(eye);
    this.ray.direction.copyFrom(to);
    this.ray.length = distance;
    const hit = this.game.scene.pickWithRay(
      this.ray,
      (m) => m.isEnabled() && m.isVisible && m.isPickable && m.visibility > 0,
    );
    return !hit?.pickedMesh || hit.distance > distance - 0.4;
  }

  private appear(): void {
    this.phase = "shown";
    this.shownFor = 0;
    this.game.flags.set("ep1.studio.dancerSeen", true);
    this.lure?.stop();
    this.song?.play();
    for (const mesh of this.meshes) mesh.visibility = 0;
    this.root?.setEnabled(true);
    this.onAppear?.();
    // Somewhere in the dance, not always the same moment of it.
    if (this.dance) {
      this.dance.start(true, 1, this.dance.from, this.dance.to);
      this.dance.goToFrame(this.dance.from + Math.random() * (this.dance.to - this.dance.from));
    }
  }

  /** Gone with the light: the lights go out on this frame (onVanish), and she with them. */
  private vanish(): void {
    this.phase = "gone";
    this.song?.stop();
    this.dance?.stop();
    this.root?.setEnabled(false);
    if (this.fill) this.fill.intensity = 0;
    this.onVanish?.();
    this.heartbeat(true);
    this.done?.();
    this.done = null;
  }
}
