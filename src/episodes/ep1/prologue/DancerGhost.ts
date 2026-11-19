import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import type { AnimationGroup } from "@babylonjs/core/Animations/animationGroup";
import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { LoadAssetContainerAsync } from "@babylonjs/core/Loading/sceneLoader";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { PointLight } from "@babylonjs/core/Lights/pointLight";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import type { Game } from "@/core/Game";
import { seededRandom } from "@/audio/synth";
import { hauntDrone, heartbeat, pinpeatLure, robamSong } from "../audio/dancerSounds";

/** How long she is there, in seconds (the user, November 19: four seconds). */
export const DANCER_SHOWN = 4;
/** The house is black this long, a breath at Sora's ear, before she is there. */
const DARK = 1.1;
/** The light on her comes up this long, sputtering. */
const REVEAL = 0.5;
/**
 * The light that falls on her alone, cold and blue-white, a failing bulb over her: it
 * carries across the room with the house's lights down to a glow.
 */
const FILL = 20;
/**
 * Her music, muffled through the wall, begins only when Sora comes near the back room
 * (within this many metres of her: the airwell's far half) and fades away again if she
 * goes back (beyond LURE_OFF); it rises and falls over LURE_FADE seconds.
 */
const LURE_ON = 7;
const LURE_OFF = 8.5;
const LURE_FADE = 1.5;
/** For the last of it she stops dead, mid-gesture, while the music dies. */
const STILL = 1.1;
/** Sora's eyes are turned to her over this long, from the moment the lights die. */
const TURN = 0.9;
/**
 * The lights die as Sora's eye passes the back room's doorway (runtime z; the doorway's
 * jamb is at Blender y 9.45): she stops there, as far from the dancer as the room allows.
 */
const DOORWAY_Z = -9.3;

/**
 * The dancer ghost in Sora's back room (Episode 1 prologue, November 2026): a royal-ballet
 * dancer in red, her face painted white under a gold crown, her throat cut and her hands
 * clawed and bloody (the user's model, art-source/library/scans/dancer_ghost.glb, prepared
 * by tools/characters/import-dancer-ghost.py), standing against the far wall. As Sora
 * comes near the back room an Apsara dance begins faintly behind the wall (the user's
 * recording, muffled). As the user asked (November 19): the moment Sora steps into the
 * doorway the house's lights die to a glow (StudioLights.lightsOut) and she can do nothing
 * but wait, kept at the doorway, as far from the dancer as the room allows; her eyes are
 * drawn to the far wall; after a breath of dark, under a cold light that sputters like a
 * failing bulb, the dancer is there, dancing to her music close by, a drone and whispers
 * rising under it and Sora's heart pounding (tools/characters/rig-dancer-ghost.py: a slow
 * robam, her head rolling over); for the last second she stops dead, mid-gesture, as the
 * music dies; after `DANCER_SHOWN` seconds she is gone, the lights stutter back
 * (lightsBack) and Sora can move again. Opaque throughout: revealed by light alone.
 */
export class DancerGhost {
  private root: TransformNode | null = null;
  private meshes: AbstractMesh[] = [];
  private fill: PointLight | null = null;
  private lure: StaticSound | null = null;
  private heart: StaticSound | null = null;
  private song: StaticSound | null = null;
  private drone: StaticSound | null = null;
  /** Seconds since the lights died. */
  private since = 0;
  /** Where Sora was looking when the lights died, and where her eyes are drawn. */
  private readonly look = { yaw: 0, pitch: 0, toYaw: 0, toPitch: 0 };
  private dance: AnimationGroup | null = null;
  private phase: "waiting" | "dark" | "shown" | "gone" = "waiting";
  private lureOn = false;
  /** The lure's level now (0–1 of its full volume) and its full volume. */
  private lureLevel = 0;
  private lureFull = 0.55;
  /** Runs her light's slow swell; starts somewhere different each time. */
  private clock = Math.random() * 10;
  private done: (() => void) | null = null;
  private readonly chest: Vector3;
  /** Called as Sora steps into the doorway: every light dies, and she is held still. */
  onBlackout: (() => void) | null = null;
  /** Called when she is there. */
  onAppear: (() => void) | null = null;
  /** Called when she is gone: the lights come back (Studio.ts). */
  onVanish: (() => void) | null = null;

  constructor(
    private readonly game: Game,
    private readonly at: Vector3,
    private readonly doorway: Vector3,
  ) {
    // Where Sora's eyes go: her chest, below the painted face.
    this.chest = at.add(new Vector3(0, 1.25, 0));
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
      // The loader starts the first clip; she waits, still and hidden, until the lights die.
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
        // Over her head and a little in front: a cold pool falling on her from above.
        this.at.add(face.normalize().scale(0.5)).add(new Vector3(0, 2.4, 0)),
        scene,
      ));
      fill.diffuse = new Color3(0.72, 0.8, 1);
      fill.intensity = 0;
      fill.range = 4;
      fill.includedOnlyMeshes = [...this.meshes];
    } catch (error) {
      console.warn("[DancerGhost] figure did not load", error);
    }
  }

  /** The lure, her music and the heartbeat (the lure waits until Sora comes near: update). */
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
    const [lure, heart, song, drone] = await Promise.all([
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
      audio.sound(
        "dancer_drone",
        audio.buffer(hauntDrone(rate, seededRandom(1913)), rate),
        "threat",
        0.9,
      ),
    ]);
    this.drone = drone;
    this.song = song;
    this.lure = lure;
    this.heart = heart;
    heart.loop = true;
    this.lureFull = lure.volume;
  }

  /**
   * Puts her in her corner, dancing and lit, for the views drawn behind the black
   * opening screen (Prologue.warmup), so every shader, pipeline and skinning buffer she
   * needs exists before she appears. Returns what hides her again.
   */
  prepareWarm(): () => void {
    const root = this.root;
    if (!root || this.phase !== "waiting") return () => undefined;
    root.setEnabled(true);
    if (this.fill) this.fill.intensity = 0.001;
    this.dance?.start(true, 1, this.dance.from, this.dance.to);
    return () => {
      if (this.phase !== "waiting") return;
      this.dance?.stop();
      root.setEnabled(false);
      if (this.fill) this.fill.intensity = 0;
    };
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
    this.clock += dt;
    const player = this.game.player;
    if (this.phase === "waiting") {
      this.updateLure(dt);
      if (this.done && this.game.camera.globalPosition.z < DOORWAY_Z) this.blackout();
      return;
    }
    if (this.phase === "gone") return;
    this.since += dt;
    const t = this.since;
    // Her eyes drawn to the far wall, eased, the shorter way round.
    if (player) {
      const k = smooth(Math.min(1, Math.max(0, (t - 0.15) / TURN)));
      let dy = this.look.toYaw - this.look.yaw;
      dy = Math.atan2(Math.sin(dy), Math.cos(dy));
      player.yaw = this.look.yaw + dy * k;
      player.pitch = this.look.pitch + (this.look.toPitch - this.look.pitch) * k;
    }
    if (this.phase === "dark") {
      if (t >= DARK) this.appear();
      return;
    }
    const shown = t - DARK;
    // The light comes up on her sputtering, then holds like a bulb about to go: dips that
    // come and go smoothly, deeper as the end comes.
    const rise = smooth(Math.min(1, shown / REVEAL));
    const unrest = 0.35 + 0.5 * Math.min(1, shown / DANCER_SHOWN);
    const dip = Math.max(0, Math.sin(this.clock * 7.3) * Math.sin(this.clock * 2.9 + 1.4)) ** 3;
    const sputter = shown < REVEAL ? 0.55 + 0.45 * Math.abs(Math.sin(shown * 31)) : 1;
    if (this.fill) this.fill.intensity = FILL * rise * sputter * (1 - unrest * dip);
    // Her eyes close in on her as she dances.
    // For the last of it she stops dead, mid-gesture.
    if (shown >= DANCER_SHOWN - STILL && this.dance?.isPlaying) this.dance.pause();
    if (shown >= DANCER_SHOWN) this.vanish();
  }

  /** The music behind the wall: only near the back room, faded in and out. */
  private updateLure(dt: number): void {
    const lure = this.lure;
    if (!lure) return;
    const near = Vector3.Distance(this.game.camera.globalPosition, this.at);
    const want = near < LURE_ON ? 1 : near > LURE_OFF ? 0 : this.lureLevel > 0 ? 1 : 0;
    const step = dt / LURE_FADE;
    this.lureLevel = Math.max(0, Math.min(1, this.lureLevel + (want ? step : -step)));
    if (this.lureLevel > 0 && !this.lureOn) {
      lure.volume = 0;
      lure.play();
      this.lureOn = true;
    }
    if (this.lureOn) lure.volume = this.lureFull * this.lureLevel;
    if (this.lureLevel === 0 && this.lureOn) {
      lure.stop();
      this.lureOn = false;
    }
  }

  /** Sora steps into the doorway: the house goes dark and she is held where she is. */
  private blackout(): void {
    this.phase = "dark";
    this.since = 0;
    if (this.lureOn) {
      this.lure?.stop();
      this.lureOn = false;
    }
    const player = this.game.player;
    if (player) {
      const eye = this.game.camera.globalPosition;
      const to = this.chest.subtract(eye);
      this.look.yaw = player.yaw;
      this.look.pitch = player.pitch;
      this.look.toYaw = Math.atan2(to.x, to.z);
      this.look.toPitch = Math.atan2(-to.y, Math.hypot(to.x, to.z));
    }
    this.onBlackout?.();
  }

  /** Out of the black, she is there. */
  private appear(): void {
    this.phase = "shown";
    this.game.flags.set("ep1.studio.dancerSeen", true);
    this.root?.setEnabled(true);
    for (const mesh of this.meshes) mesh.visibility = 1;
    // Somewhere in the dance, not always the same moment of it.
    if (this.dance) {
      this.dance.start(true, 1, this.dance.from, this.dance.to);
      this.dance.goToFrame(this.dance.from + Math.random() * (this.dance.to - this.dance.from));
    }
    this.song?.play();
    this.drone?.play();
    this.heartbeat(true);
    this.onAppear?.();
  }

  /** Gone, and the lights come back (onVanish). */
  private vanish(): void {
    this.phase = "gone";
    this.song?.stop();
    this.drone?.stop();
    this.dance?.stop();
    this.root?.setEnabled(false);
    if (this.fill) this.fill.intensity = 0;
    this.onVanish?.();
    this.done?.();
    this.done = null;
  }
}

/** Eased in and out. */
function smooth(x: number): number {
  return x * x * (3 - 2 * x);
}
