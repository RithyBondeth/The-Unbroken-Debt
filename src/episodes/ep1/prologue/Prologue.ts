import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import type { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { Game } from "../../../core/Game";
import { loadArea, type Area } from "../../../core/AreaLoader";
import { meshesOf } from "../../../systems/interaction/Interaction";
import type { BusName, SpatialOptions } from "../../../audio/AudioSystem";
import { seededRandom } from "../../../audio/synth";
import * as sounds from "../../../audio/prologueSounds";
import { newGameSave } from "../../../systems/saves/SaveData";
import {
  INK_BLOT_ENTRY,
  KIT,
  LINES,
  STARTING_MATCHES,
  TIMING,
  TITLE_CARD,
  type Line,
} from "../data/prologue";
import { StudioLights } from "./Studio";
import { Rain } from "../Rain";
import { InkMarks } from "./InkMarks";

const ILLUSTRATION = "interact_illustration";
const DRAWER = "interact_drawer";
const DOOR = "interact_door";
const PHONE = "interact_telephone";
/** Interactables that are items: what Sora gains by taking each one. */
const PICKUPS: Record<string, { item: string; count?: number }> = {
  interact_satchel: { item: "satchel" },
  interact_sketchbook: { item: "sketchbook" },
  interact_lamp: { item: "lamp" },
  matchbox: { item: "matches", count: STARTING_MATCHES },
  letters: { item: "letters" },
};
/** How far the desk drawer slides out, in metres. */
const DRAWER_TRAVEL = 0.28;

type SoundMaker = (sampleRate: number, rand: () => number) => Float32Array;

/**
 * Episode 1 prologue: Sora's studio in Phnom Penh, 8:00 PM, rain (Beat Sheet,
 * section 3.1, beats P01–P07). The beats run as one script; using things in
 * the room (drawer, kit, door) is answered as it happens.
 */
export class Prologue {
  area!: Area;
  lights!: StudioLights;
  private rain!: Rain;
  private ink!: InkMarks;
  private readonly waiting = new Map<string, () => void>();
  private readonly loops: StaticSound[] = [];
  private sfx = new Map<string, StaticSound>();
  private drawerOpen = false;
  private ringing = false;
  private playTime = 0;
  private wasFlashing = false;

  constructor(private readonly game: Game) {}

  async load(): Promise<void> {
    const game = this.game;
    this.area = await loadArea(game.scene, "ep1", "ep1_area_studio", {
      keep: ["window_glass", "drawer_knob", "letters_string", "matchbox", /^letter_\d/],
    });
    this.lights = new StudioLights(game.scene, this.area, game.preset);
    const glass = game.scene.getMeshByName("window_glass");
    if (glass) this.rain = new Rain(game.scene, glass);
    this.ink = new InkMarks(game.scene, this.mesh(ILLUSTRATION));

    // P01: fade in at the drafting table, looking down at the illustration.
    const spawn = this.area.level.spawns.get("player");
    game.spawnPlayer(spawn?.position, spawn?.yaw ?? Math.PI);
    game.player.pitch = 0.6;

    for (const { name, node } of this.area.level.interactables) game.interaction.add(name, node);
    game.bus.on("interact:use", ({ id }) => this.onUse(id));
    game.bus.on("interact:focus", ({ id }) => {
      if (id === ILLUSTRATION) game.hints.show("hint.use");
    });
  }

  /** Starts the prologue once the game's post-processing exists. */
  async begin(): Promise<void> {
    const game = this.game;
    game.addFlameLights(this.lights.deskLamp, this.lights.candle);
    game.scene.onBeforeRenderObservable.add(() => this.update(game.deltaSeconds));
    if (import.meta.env.DEV) (window as unknown as { prologue: Prologue }).prologue = this;
    await this.run();
  }

  private update(dt: number): void {
    const game = this.game;
    this.playTime += dt;
    this.lights.update(dt);
    this.rain?.update(dt, this.lights.lightning.intensity / 60);
    this.ink.update(dt);
    game.atmosphere.update(dt, this.lights.lightAtEye(game.camera.globalPosition));
    // Thunder follows each flash after a few seconds (sound travels about 1 km in 3 s).
    const flashing = this.lights.flashing;
    if (flashing && !this.wasFlashing)
      setTimeout(() => this.play("thunder"), 1500 + Math.random() * 2500);
    this.wasFlashing = flashing;
  }

  // ------------------------------------------------------------------ beats

  private async run(): Promise<void> {
    const game = this.game;
    game.cutscene = true;
    await game.fade.to(1, 0);
    await game.fade.waitForClick(() => {
      void game.input.lockPointer();
      void game.audio?.unlock();
    });
    await this.makeSounds();

    // P01: rain, the clock, the desk lamp. Pencil hints if the player sits still.
    void game.fade.to(0, 3);
    game.cutscene = false;
    game.interaction.allow = (id) => id === ILLUSTRATION;
    void this.idleHints();

    // P02: only the illustration can be used: Sora inks a line.
    await this.used(ILLUSTRATION);
    game.cutscene = true;
    this.play("pen");
    await this.ink.inkLine(1.1);
    game.cutscene = false;
    game.flags.set("ep1.illustration.inked", true);
    game.interaction.allow = () => true;

    // P03–P04: the drawer, the letters and the kit, in any order (see onUse).
    await this.until(() => KIT.every((item) => game.inventory.has(item)));
    game.flags.set("ep1.kit.collected", true);

    // P05: dread. Ink across the drawing, the candle out, the clock stops at 8:12.
    await this.wait(TIMING.dreadDelay);
    this.lights.strike();
    void this.ink.spill(2.4);
    this.lights.snuffCandle();
    this.play("candle");
    this.sfx.get("clock")?.stop();
    this.play("clockStop");
    game.flags.set("ep1.clock.stopped", "20:12");
    game.satchel.close();
    game.sketchbook?.write(INK_BLOT_ENTRY);
    await this.wait(2.5);
    game.hints.show("hint.sketchbook", 8);

    // P06: the telephone rings until Sora answers.
    await this.wait(TIMING.ringDelay);
    this.ringing = true;
    this.sfx.get("ring")?.play();
    setTimeout(() => {
      if (this.ringing) game.hints.show("hint.phone");
    }, 5000);
    await this.used(PHONE);
    await this.phoneCall();

    // P07: out of the door, into the night.
    await this.used(DOOR);
    await this.leave();
  }

  private async phoneCall(): Promise<void> {
    const game = this.game;
    this.ringing = false;
    game.hints.performed("hint.phone");
    this.sfx.get("ring")?.stop();
    game.cutscene = true;
    game.gated.holdStill = true;
    this.node("telephone_earpiece")?.setEnabled(false);
    this.play("static");
    await this.say(LINES.call1);
    await this.wait(0.4);
    await this.say(LINES.call2);
    await this.wait(0.3);
    const cutOff = this.say(LINES.call3);
    await this.wait(LINES.call3.seconds * 0.75);
    this.play("scream");
    this.lights.strike();
    await cutOff;
    await this.wait(1.6);
    this.sfx.get("static")?.stop();
    await this.wait(0.9);
    await this.say(LINES.call4);
    this.node("telephone_earpiece")?.setEnabled(true);
    game.gated.holdStill = false;
    game.cutscene = false;
    game.flags.set("ep1.phone.answered", true);
  }

  private async leave(): Promise<void> {
    const game = this.game;
    game.cutscene = true;
    game.gated.holdStill = true;
    game.gated.holdLook = true;
    this.play("drawer");
    await game.fade.to(1, 1.5);
    for (const sound of this.loops) sound.stop();
    this.play("train", game.camera.globalPosition);
    await this.wait(5);
    await game.fade.show({ title: TITLE_CARD.title, khmer: TITLE_CARD.khmer });
    // Checkpoint CP1: the carriage at the village, lamp full (Beat Sheet, section 7).
    game.bus.emit("checkpoint:reached", { id: "CP1" });
    game.flags.set("sketchbook.written", [...(game.sketchbook?.written ?? [])].join(","));
    await game.saves.save("autosave", {
      ...newGameSave(),
      checkpoint: "CP1",
      clock: TIMING.cp1Clock,
      flags: game.flags.toJSON(),
      inventory: game.inventory.toJSON(),
      lamp: { oil: 1, state: "out" },
      playTimeSec: Math.round(this.playTime),
    });
    await this.wait(3.5);
    // Act I loads from the checkpoint just saved, as it will after any restart.
    location.replace(`${location.pathname}?continue`);
  }

  // ------------------------------------------------------- using the room

  private onUse(id: string): void {
    const game = this.game;
    this.waiting.get(id)?.();
    this.waiting.delete(id);

    const pickup = PICKUPS[id];
    if (pickup) return void this.take(id, pickup.item, pickup.count);
    if (id === DRAWER && !this.drawerOpen) return this.openDrawer();
    if (id === DOOR && !game.flags.get("ep1.phone.answered", false)) {
      if (!game.flags.get("ep1.kit.collected", false)) game.hints.show("hint.notYet", 3);
    }
  }

  /** P03: the drawer slides out: Yay Mey's letters, tied with red string, and the matchbox. */
  private openDrawer(): void {
    this.drawerOpen = true;
    this.play("drawer");
    const parts = [DRAWER, "drawer_knob", "letters_string", "matchbox"].map((n) => this.node(n));
    for (let i = 0; i < 5; i++) parts.push(this.node(`letter_${i}`));
    const start = parts.map((n) => n?.getAbsolutePosition().clone());
    let t = 0;
    const slide = this.game.scene.onBeforeRenderObservable.add(() => {
      t = Math.min(1, t + this.game.deltaSeconds / 0.45);
      const ease = 1 - (1 - t) ** 3;
      parts.forEach((n, i) => {
        // Out of the desk towards the room: Blender +X, Babylon −X.
        const from = start[i];
        if (n && from) n.setAbsolutePosition(from.add(new Vector3(-DRAWER_TRAVEL * ease, 0, 0)));
      });
      if (t >= 1) slide.remove();
    });
    const letters = [
      this.node("letters_string"),
      ...[0, 1, 2, 3, 4].map((i) => this.node(`letter_${i}`)),
    ];
    this.game.interaction.add(
      "letters",
      letters.flatMap((n) => (n ? meshesOf(n) : [])),
    );
    const matchbox = this.node("matchbox");
    if (matchbox) this.game.interaction.add("matchbox", matchbox);
  }

  private async take(id: string, item: string, count = 1): Promise<void> {
    const game = this.game;
    if (id === "letters") {
      // P03: she hesitates, then takes them anyway.
      game.cutscene = true;
      await this.say(LINES.letters);
      game.cutscene = false;
      game.flags.set("ep1.letters.taken", true);
      game.flags.increment("ep1.lore");
    }
    game.interaction.remove(id);
    const nodes =
      id === "letters" ? ["letters_string", ...[0, 1, 2, 3, 4].map((i) => `letter_${i}`)] : [id];
    for (const name of nodes) this.node(name)?.setEnabled(false);
    this.play("pickup");
    game.inventory.add(item, count);
    // P04: the satchel opens once by itself, to show where things go.
    if (item === "satchel") {
      game.toggleSatchel();
      game.hints.show("hint.satchel", 8);
    }
  }

  // ------------------------------------------------------------ plumbing

  private node(name: string): TransformNode | null {
    const scene = this.game.scene;
    return scene.getMeshByName(name) ?? scene.getTransformNodeByName(name);
  }

  private mesh(name: string): AbstractMesh {
    const mesh = this.game.scene.getMeshByName(name);
    if (!mesh) throw new Error(`[Prologue] the studio has no ${name}`);
    return mesh;
  }

  /** Resolves the next time `id` is used. */
  private used(id: string): Promise<void> {
    return new Promise((done) => this.waiting.set(id, done));
  }

  /** Waits in game time (it stops when the tab is hidden). */
  private wait(seconds: number): Promise<void> {
    return this.until(
      (() => {
        let left = seconds;
        return () => (left -= this.game.deltaSeconds) <= 0;
      })(),
    );
  }

  private until(condition: () => boolean): Promise<void> {
    return new Promise((done) => {
      const observer = this.game.scene.onBeforeRenderObservable.add(() => {
        if (!condition()) return;
        observer.remove();
        done();
      });
    });
  }

  private say(line: Line): Promise<void> {
    return this.game.subtitles.say(line.speaker, line.text, line.seconds);
  }

  /** P01: look and move hints, only if the player hasn't done either after a few seconds. */
  private async idleHints(): Promise<void> {
    const game = this.game;
    const yaw = game.player.yaw;
    const feet = game.player.feet.clone();
    const looked = () => Math.abs(game.player.yaw - yaw) > 0.25;
    const moved = () => Vector3.Distance(game.player.feet, feet) > 0.4;
    await this.wait(TIMING.idleHint);
    if (!looked()) game.hints.show("hint.look");
    await this.until(looked);
    game.hints.performed("hint.look");
    await this.wait(1.5);
    if (!moved()) game.hints.show("hint.move");
    await this.until(moved);
    game.hints.performed("hint.move");
  }

  /** Placeholder sounds (src/audio/prologueSounds.ts), placed where they happen. */
  private async makeSounds(): Promise<void> {
    const audio = this.game.audio;
    if (!audio) return;
    const at = (name: string, fallback: Vector3) =>
      this.node(name)?.getAbsolutePosition().clone() ?? fallback;
    const markers = this.area.level.markers;
    const window = at("window_glass", new Vector3(-3, 1.8, 0));
    const desk = at(ILLUSTRATION, new Vector3(-3, 0.9, -0.7));
    const list: [string, SoundMaker, BusName, Vector3, SpatialOptions][] = [
      ["rain", sounds.rainLoop, "ambience", window, { loop: true, minDistance: 3, volume: 0.8 }],
      [
        "clock",
        sounds.clockLoop,
        "sfx",
        markers.get("clock")?.position ?? desk,
        { loop: true, volume: 0.35 },
      ],
      ["ring", sounds.phoneRing, "sfx", at(PHONE, desk), { loop: true, minDistance: 2 }],
      [
        "static",
        sounds.lineStatic,
        "voice",
        at(PHONE, desk),
        { loop: true, volume: 0.5, minDistance: 3 },
      ],
      ["scream", sounds.callScream, "voice", at(PHONE, desk), { minDistance: 3 }],
      [
        "thunder",
        sounds.thunder,
        "ambience",
        markers.get("lightning")?.position ?? window,
        { minDistance: 30, volume: 0.9 },
      ],
      ["pen", sounds.penScratch, "sfx", desk, { volume: 0.6 }],
      ["pickup", sounds.pickUp, "sfx", desk, { volume: 0.6 }],
      ["drawer", sounds.drawerOpen, "sfx", at(DRAWER, desk), { volume: 0.8 }],
      ["candle", sounds.candleOut, "sfx", this.lights.candle.position, { volume: 0.7 }],
      ["clockStop", sounds.clockStop, "sfx", markers.get("clock")?.position ?? desk, {}],
      ["train", sounds.trainPassing, "ambience", desk, { minDistance: 20 }],
    ];
    const sampleRate = audio.context.sampleRate;
    const made = await Promise.all(
      list.map(([name, make, bus, position, options], i) =>
        audio.spatialSound(
          name,
          audio.buffer(make(sampleRate, seededRandom(1932 + i)), sampleRate),
          bus,
          position,
          options,
        ),
      ),
    );
    list.forEach(([name, , , , options], i) => {
      this.sfx.set(name, made[i]);
      if (options.loop && (name === "rain" || name === "clock")) {
        made[i].play();
        this.loops.push(made[i]);
      }
    });
    this.loops.push(made[list.findIndex(([n]) => n === "static")]);
  }

  /** Plays a one-shot; `position` moves it first (the train plays at Sora's ears). */
  private play(name: string, position?: Vector3): void {
    const sound = this.sfx.get(name);
    if (!sound) return;
    if (position) sound.spatial.position = position.clone();
    sound.play();
  }
}
