import type { Scene } from "@babylonjs/core/scene";
import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { Color4 } from "@babylonjs/core/Maths/math.color";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import { ParticleSystem } from "@babylonjs/core/Particles/particleSystem";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import type { Material } from "@babylonjs/core/Materials/material";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import type { Game } from "../../../core/Game";
import type { Area } from "../../../core/AreaLoader";
import type { LevelMarker } from "../../../core/LevelBuilder";
import { seededRandom } from "../../../audio/synth";
import { drawerOpen, pickUp } from "../audio/prologueSounds";
import { lampWick, matchStrike, pourOil, whispers } from "../audio/vigilSounds";
import { Lamp } from "../../../systems/lamp/Lamp";
import { Upkeep } from "../../../systems/upkeep/Upkeep";
import { BottomScaler, HeldLamp } from "../../../player/HeldLamp";
import type { VillageLights } from "./VillageLights";
import "@babylonjs/core/Particles/particleSystemComponent";
import type { SaveData } from "../../../systems/saves/SaveData";

/** Episode 1 Beat Sheet, section 5: corner sticks burn down every 10–12 minutes. */
export const INCENSE_SECONDS = 11 * 60;
/** Incense left at the two warnings (A1-10: "the tent dims, whispers rise"). */
const INCENSE_WARNINGS: [number, number] = [0.25, 0.1];
/** Out this long through neglect costs the respect point (Beat Sheet, section 7). */
const NEGLECT_SECONDS = 60;
/** A second box of matches in the kitchen drawer (Beat Sheet, section 5: "10 + 10"). */
const DRAWER_MATCHES = 10;
/** A match takes this long to strike and catch before the wick lights. */
const STRIKE_SECONDS = 0.55;
/** Where the lamp's light sits, in camera space (m): a little left of and below the eye. */
const LIGHT_AT = new Vector3(-0.06, -0.14, 0.1);

interface Burner {
  marker: LevelMarker;
  sticks: AbstractMesh[];
  materials: (Material | null)[];
  /** Burn each stick down from its tip. */
  heights: BottomScaler[];
  /** The glowing ends ride down with the tips: rest height and the sticks' full length. */
  embers: { mesh: AbstractMesh; y: number; drop: number }[];
  smoke: ParticleSystem;
}

/**
 * The vigil's three duties in play (Episode 1, section 6): Sora's lamp burns
 * kerosene and is lit with matches (F), refilled from bottles (left mouse) and
 * read by raising it (right mouse); the four corner incense sticks burn down
 * and are renewed with a bundle from the house altar and a match. Pickups of
 * oil, incense and the spare matches. The thread and the betel tray come with
 * the Act I beats.
 */
export class Vigil {
  readonly lamp: Lamp;
  readonly incense: Upkeep;
  private held: HeldLamp | null = null;

  /** The lamp in Sora's hand, for lights that must leave it alone. */
  get heldMeshes(): AbstractMesh[] {
    return this.held?.meshes ?? [];
  }
  private readonly burners: Burner[] = [];
  private readonly ash: PBRMaterial;
  private readonly sfx = new Map<string, StaticSound>();
  private whisper: StaticSound | null = null;
  private raising = false;
  private striking = false;
  private lightingLamp = false;
  private time = 0;
  private readonly abort = new AbortController();

  constructor(
    private readonly game: Game,
    private readonly area: Area,
    private readonly lights: VillageLights,
  ) {
    this.ash = new PBRMaterial("M_scripted_incense_ash", game.scene);
    this.ash.albedoColor = Color3.FromHexString("#c7c0ac").toLinearSpace();
    this.ash.roughness = 1;
    this.ash.maxSimultaneousLights = 8;
    const saved = game.savedLamp;
    // CP1 starts with a full lamp, unlit: the darkness at the carriage forces the first match.
    this.lamp = new Lamp(game.bus, saved?.oil ?? 1, saved?.state ?? "out");
    this.lamp.restoreAtLeast(0.5);
    this.incense = new Upkeep(
      "incense",
      { duration: INCENSE_SECONDS, warnings: INCENSE_WARNINGS },
      game.bus,
    );
    this.incense.restore(
      game.flags.get("ep1.incense.remaining", 1),
      game.flags.get("ep1.incense.outFor", 0),
    );
    for (const marker of area.level.interactables)
      if (marker.extras.action === "tend") this.burners.push(this.makeBurner(marker));
    game.bus.on("interact:use", ({ id }) => this.use(id));
    game.bus.on("upkeep:warning", ({ id, stage }) => {
      if (id === "incense" && stage === 1 && !game.inventory.has("incense"))
        game.hints.show("note.needIncense", 6);
    });
    const signal = this.abort.signal;
    window.addEventListener("keydown", (e) => this.onKey(e), { signal });
    window.addEventListener("mousedown", (e) => this.onMouse(e, true), { signal });
    window.addEventListener("mouseup", (e) => this.onMouse(e, false), { signal });
    window.addEventListener(
      "contextmenu",
      (e) => {
        if (game.input.pointerLocked) e.preventDefault();
      },
      { signal },
    );
  }

  /** Loads the lamp in Sora's hand and places the lamp's light. */
  async load(): Promise<void> {
    const game = this.game;
    this.held = await HeldLamp.load(game.scene, game.camera);
    game.hands.attachLamp(this.held.root, () => this.lamp.burning || this.lightingLamp);
    // The light stays just below Sora's eyes, fixed to the camera, not at the wick:
    // from the hand, off to one side and swinging, every turn of the head swept the
    // shadows of leaves and posts across the scene and the mist. From near the eye
    // the shadows fall behind what casts them, and hold still as she looks round.
    this.lights.lamp.parent = game.camera;
    this.lights.lamp.position.copyFrom(LIGHT_AT);
    // Lit from a few centimetres the lamp's own cage and glass would blaze; they glow
    // from their own materials instead (HeldLamp).
    this.lights.lamp.excludedMeshes.push(...this.held.meshes, ...game.hands.meshes);
    await this.makeSounds();
  }

  /** At the carriage: the dark asks for the lamp (A1-01, match tutorial). */
  begin(): void {
    if (!this.lamp.burning)
      setTimeout(() => {
        if (!this.lamp.burning && !this.game.threatActive && !this.game.hiding)
          this.game.hints.show("hint.lamp", 10);
      }, 2500);
  }

  update(dt: number): void {
    const game = this.game;
    this.time += dt;
    this.lamp.update(dt);
    if (!this.lamp.burning) this.raising = false;
    if (
      game.flags.get("ep1.vigil.started", false) &&
      !game.flags.get("ep1.ritual.tokenPlaced", false)
    )
      this.incense.update(dt);
    const flame = this.lamp.flame(this.time);
    this.lights.lampFlame = flame;
    this.held?.update(dt, flame, this.lamp.oil, this.raising, game.player.speed);

    if (this.lamp.burning && this.lamp.oil < 0.5) game.hints.show("hint.raise", 6);
    if (this.lamp.oil < 0.3 && game.inventory.has("oil")) game.hints.show("hint.refill", 6);

    // The incense: sticks shorten, smoke thins, the tent dims, whispers rise.
    const left = this.incense.alive ? this.incense.fraction : 0;
    for (const b of this.burners) {
      const scripted = game.flags.get("ep1.incense.scripted", false);
      const k = !this.incense.alive && scripted ? 0.9 : 0.15 + 0.85 * left;
      b.sticks.forEach((stick, i) => {
        stick.isVisible = true;
        stick.material = this.incense.alive ? b.materials[i] : this.ash;
        b.heights[i].set(k);
      });
      for (const e of b.embers) {
        e.mesh.isVisible = left > 0;
        e.mesh.position.y = e.y - e.drop * (1 - k);
      }
      b.smoke.emitRate = this.incense.alive ? 4 + 6 * left : 0;
    }
    const warning = this.incense.alive ? this.incense.warning : 3;
    this.lights.tentLevel = [1, 0.9, 0.75, 0.55][warning];
    if (this.whisper) this.whisper.volume = [0, 0.2, 0.45, 0.8][warning];
    if (
      !this.incense.alive &&
      !game.flags.get("ep1.ritual.tokenPlaced", false) &&
      !game.flags.get("ep1.incense.scripted", false) &&
      this.incense.outFor >= NEGLECT_SECONDS &&
      !game.flags.get("ep1.incense.neglected", false)
    )
      game.flags.set("ep1.incense.neglected", true);
  }

  /** Sora is holding the lamp up (right mouse). */
  get lampRaised(): boolean {
    return this.raising;
  }

  /** The lamp for a checkpoint save. */
  toJSON(): ReturnType<Lamp["toJSON"]> {
    return this.lamp.toJSON();
  }

  saveState(): void {
    this.game.flags.set("ep1.incense.remaining", this.incense.fraction);
    this.game.flags.set("ep1.incense.outFor", this.incense.outFor);
  }

  /** A2-09 is authored ash; it never erases earlier neglect or creates a new penalty. */
  scriptedAsh(): void {
    this.game.flags.set("ep1.incense.scripted", true);
    this.incense.extinguish();
    this.saveState();
  }

  restoreCheckpoint(save: SaveData): void {
    this.lamp.restore(save.lamp);
    this.lamp.restoreAtLeast(0.5);
    this.incense.restore(
      Number(save.flags["ep1.incense.remaining"] ?? 1),
      Number(save.flags["ep1.incense.outFor"] ?? 0),
    );
    this.raising = false;
  }

  // ------------------------------------------------------------- the lamp

  private get handsFree(): boolean {
    const game = this.game;
    return (
      !game.cutscene &&
      !game.threatActive &&
      !(game.sketchbook?.isOpen ?? false) &&
      !game.satchel.isOpen
    );
  }

  private onKey(e: KeyboardEvent): void {
    // Extinguishing a wick is the hiding action; the threat gate only prevents
    // striking a new match or handling resources during an encounter.
    if (
      e.repeat ||
      e.code !== "KeyF" ||
      this.game.cutscene ||
      this.game.satchel.isOpen ||
      this.game.sketchbook?.isOpen
    )
      return;
    if (this.lamp.burning) {
      this.lamp.putOut();
      this.raising = false;
      this.play("wick");
      return;
    }
    if (this.handsFree) void this.lightLamp();
  }

  private onMouse(e: MouseEvent, down: boolean): void {
    if (!this.game.input.pointerLocked) return;
    if (e.button === 2) {
      this.raising = down && this.handsFree && this.lamp.burning;
      if (this.raising) this.game.hints.performed("hint.raise");
    }
    if (e.button === 0 && down && this.handsFree) this.pour();
  }

  private async lightLamp(): Promise<void> {
    const game = this.game;
    if (this.striking) return;
    if (this.lamp.oil <= 0) return game.hints.show("note.lampDry", 4);
    this.lightingLamp = true;
    try {
      if (!(await this.strikeMatch())) return;
      this.lamp.light();
      this.play("wick");
      game.hints.performed("hint.lamp");
    } finally {
      this.lightingLamp = false;
    }
  }

  /** Strikes one ordinary match; false if there are none. */
  private async strikeMatch(): Promise<boolean> {
    const game = this.game;
    if (!game.inventory.remove("matches")) {
      game.hints.show("note.noMatches", 4);
      return false;
    }
    this.striking = true;
    game.hands?.animate("strike");
    this.play("match");
    await new Promise((done) => setTimeout(done, STRIKE_SECONDS * 1000));
    this.striking = false;
    return true;
  }

  private pour(): void {
    const game = this.game;
    if (!game.inventory.has("oil")) return;
    if (this.lamp.oil > 0.9) return game.hints.show("note.lampFull", 3);
    game.inventory.remove("oil");
    this.lamp.refill(1);
    game.hands?.animate("pour");
    this.play("pour");
    game.hints.performed("hint.refill");
  }

  // ---------------------------------------------------------- using things

  private use(id: string): void {
    const marker = this.area.level.interactables.find((m) => m.name === id);
    if (!marker || !this.handsFree) return;
    const { action, item } = marker.extras;
    const game = this.game;
    if (action === "pickup" && item === "oil") {
      game.inventory.add("oil");
      this.take(marker);
      game.hints.show("note.oil", 3);
      if (this.lamp.oil < 0.9) game.hints.show("hint.refill", 6);
    } else if (action === "pickup" && item === "incense") {
      // The altar's bundle can be taken again whenever it has been used.
      if (game.inventory.has("incense")) return game.hints.show("note.haveIncense", 3);
      game.inventory.add("incense");
      this.play("pickup");
      game.hints.show("note.incense", 3);
    } else if (action === "open" && item === "matches") {
      if (game.flags.get("ep1.drawer.matches", false)) return;
      game.flags.set("ep1.drawer.matches", true);
      game.inventory.add("matches", DRAWER_MATCHES);
      this.play("drawer");
      game.hints.show("note.matches", 3);
    } else if (action === "tend") void this.tendIncense();
  }

  /** One bundle and one match renew all four corner sticks. */
  private async tendIncense(): Promise<void> {
    const game = this.game;
    if (this.striking) return;
    if (this.incense.alive && this.incense.fraction > 0.5)
      return game.hints.show("note.stillBurning", 3);
    if (!game.inventory.has("incense")) return game.hints.show("note.needIncense", 4);
    if (!(await this.strikeMatch())) return;
    game.inventory.remove("incense");
    this.incense.renew();
    game.flags.set("ep1.incense.scripted", false);
    game.hints.performed("hint.incense");
  }

  private take(marker: LevelMarker): void {
    this.game.flags.set(`ep1.pickup.${marker.name}`, true);
    this.game.interaction.remove(marker.name);
    marker.node.setEnabled(false);
    this.play("pickup");
  }

  // --------------------------------------------------------- the incense

  private makeBurner(marker: LevelMarker): Burner {
    const scene = this.game.scene;
    const meshes = marker.node.getChildMeshes(false);
    const sticks = meshes.filter((m) => m.material?.name === "M_incense");
    const embers = meshes.filter((m) => m.material?.name === "M_ember");
    const length = sticks.reduce((most, m) => {
      const box = m.getBoundingInfo().boundingBox;
      return Math.max(most, m.scaling.y * (box.maximum.y - box.minimum.y));
    }, 0);
    const sand = meshes.find((m) => m.material?.name === "M_incense_sand");
    sand?.computeWorldMatrix(true);
    const base = sand
      ? sand.getBoundingInfo().boundingBox.maximumWorld.clone()
      : marker.position.clone();
    const smoke = new ParticleSystem(`incense_smoke_${marker.name}`, 60, scene);
    smoke.particleTexture = smokePuff(scene);
    smoke.emitter = base.add(new Vector3(0, 0.3, 0));
    smoke.minEmitBox.set(-0.02, 0, -0.02);
    smoke.maxEmitBox.set(0.02, 0.02, 0.02);
    smoke.direction1 = new Vector3(-0.05, 1, -0.05);
    smoke.direction2 = new Vector3(0.05, 1, 0.05);
    smoke.minEmitPower = 0.08;
    smoke.maxEmitPower = 0.16;
    smoke.minLifeTime = 2.5;
    smoke.maxLifeTime = 4;
    smoke.minSize = 0.03;
    smoke.maxSize = 0.07;
    smoke.addSizeGradient(0, 0.03);
    smoke.addSizeGradient(1, 0.25);
    smoke.minAngularSpeed = -0.6;
    smoke.maxAngularSpeed = 0.6;
    smoke.color1 = new Color4(0.75, 0.72, 0.68, 0.18);
    smoke.color2 = new Color4(0.65, 0.62, 0.6, 0.12);
    smoke.colorDead = new Color4(0.6, 0.6, 0.6, 0);
    smoke.blendMode = ParticleSystem.BLENDMODE_STANDARD;
    smoke.emitRate = 8;
    smoke.preWarmCycles = 120;
    smoke.start();
    return {
      marker,
      sticks,
      materials: sticks.map((stick) => stick.material),
      heights: sticks.map((s) => new BottomScaler(s)),
      embers: embers.map((mesh) => ({ mesh, y: mesh.position.y, drop: length })),
      smoke,
    };
  }

  // ------------------------------------------------------------- sounds

  private async makeSounds(): Promise<void> {
    const audio = this.game.audio;
    if (!audio) return;
    const rate = audio.context.sampleRate;
    const eye = this.game.camera.globalPosition;
    const make = async (name: string, samples: Float32Array) =>
      this.sfx.set(
        name,
        await audio.spatialSound(name, audio.buffer(samples, rate), "sfx", eye, { minDistance: 2 }),
      );
    await make("match", matchStrike(rate, seededRandom(21)));
    await make("wick", lampWick(rate, seededRandom(22)));
    await make("pour", pourOil(rate, seededRandom(23)));
    await make("pickup", pickUp(rate, seededRandom(24)));
    await make("drawer", drawerOpen(rate, seededRandom(25)));
    const tent = this.burners.length
      ? this.burners
          .reduce((sum, b) => sum.addInPlace(b.marker.position), Vector3.Zero())
          .scaleInPlace(1 / this.burners.length)
      : eye.clone();
    this.whisper = await audio.spatialSound(
      "incense_whispers",
      audio.buffer(whispers(rate, seededRandom(26)), rate),
      "threat",
      tent,
      {
        loop: true,
        minDistance: 3,
        volume: 0,
      },
    );
    this.whisper.play();
  }

  /** Sora's own sounds come from where she stands. */
  private play(name: string): void {
    const sound = this.sfx.get(name);
    if (!sound) return;
    sound.spatial.position = this.game.camera.globalPosition.clone();
    sound.play();
  }

  dispose(): void {
    this.abort.abort();
    this.held?.dispose();
    for (const b of this.burners) b.smoke.dispose();
  }
}

/** A soft round puff for incense smoke. */
function smokePuff(scene: Scene): DynamicTexture {
  const texture = new DynamicTexture("T_incense_smoke", { width: 64, height: 64 }, scene, false);
  const ctx = texture.getContext();
  const g = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
  g.addColorStop(0, "rgba(255,255,255,0.8)");
  g.addColorStop(1, "rgba(255,255,255,0)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 64, 64);
  texture.hasAlpha = true;
  texture.update();
  return texture;
}
