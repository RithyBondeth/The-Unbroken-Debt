import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import type { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { CreateBox } from "@babylonjs/core/Meshes/Builders/boxBuilder";
import type { Game } from "../../../core/Game";
import { loadArea, type Area } from "../../../core/AreaLoader";
import { meshesOf } from "../../../systems/interaction/Interaction";
import type { BusName, SpatialOptions } from "../../../audio/AudioSystem";
import { seededRandom } from "../../../audio/synth";
import * as sounds from "../audio/prologueSounds";
import { newGameSave } from "../../../systems/saves/SaveData";
import { INK_BLOT_ENTRY, KIT, LINES, STARTING_MATCHES, TIMING, type Line } from "../data/prologue";
import { StudioLights } from "./Studio";
import { Rain } from "../Rain";
import { DRAWING_VIEW_RADIUS, drawingFocus } from "../../../player/DrawingPose";
import { InkMarks } from "./InkMarks";
import type { StringKey } from "../../../data/strings";
import { StudioDetails } from "./StudioDetails";
import type { SaveData } from "../../../systems/saves/SaveData";
import { SavePoint } from "../../../systems/saves/SavePoint";

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
const KIT_HINTS: Record<(typeof KIT)[number], StringKey> = {
  satchel: "hint.packSatchel",
  sketchbook: "hint.packSketchbook",
  matches: "hint.packMatches",
  lamp: "hint.packLamp",
};

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
  private readonly taking = new Set<string>();
  details!: StudioDetails;

  constructor(private readonly game: Game) {}

  /** Included in the development overlay when diagnosing browser input. */
  get debugStatus(): string {
    const missing = KIT.filter((item) => !this.game.inventory.has(item));
    return `phone ringing=${this.ringing} waiting=${this.waiting.has(PHONE)} answered=${this.game.flags.get("ep1.phone.answered", false)}\nkit missing: ${missing.join(", ") || "none"}`;
  }

  async load(): Promise<void> {
    const game = this.game;
    this.area = await loadArea(game.scene, "ep1", "ep1_area_studio", {
      keep: [
        "window_glass",
        "drawer_knob",
        "letters_string",
        "matchbox",
        /^letter_\d/,
        /^desk_lamp_/,
      ],
    });
    this.details = new StudioDetails(game.scene, this.area);
    this.lights = new StudioLights(game.scene, this.area, game.preset);
    const glass = game.scene.getMeshByName("window_glass");
    if (glass) this.rain = new Rain(game.scene, glass);
    this.ink = new InkMarks(game.scene, this.mesh(ILLUSTRATION), game.hands);

    // The lantern has open space through its centre. Give the whole visible
    // silhouette a pickup target so aiming at that opening still takes it.
    const lamp = this.node("interact_lamp");
    if (lamp) {
      lamp.computeWorldMatrix(true);
      const { min, max } = lamp.getHierarchyBoundingVectors(true);
      const size = max.subtract(min);
      const pickup = CreateBox(
        "studio_lamp_pickup",
        {
          width: size.x,
          height: size.y,
          depth: size.z,
        },
        game.scene,
      );
      pickup.position.copyFrom(Vector3.Center(min, max));
      pickup.visibility = 0;
      pickup.setParent(lamp);
    }

    // P01: fade in at the drafting table, looking down at the illustration.
    const spawn = this.area.level.spawns.get("player");
    game.spawnPlayer(spawn?.position, spawn?.yaw ?? Math.PI);
    game.player.pitch = 0.6;

    // Studio checkpoints restore the collected props and drawer, not just inventory.
    for (const [id, pickup] of Object.entries(PICKUPS)) {
      if (!game.inventory.has(pickup.item)) continue;
      const names =
        id === "letters" ? ["letters_string", ...[0, 1, 2, 3, 4].map((i) => `letter_${i}`)] : [id];
      for (const name of names) this.node(name)?.setEnabled(false);
    }
    if (game.flags.get("ep1.studio.drawerOpen", false)) this.openDrawer(true);

    for (const { name, node } of this.area.level.interactables)
      if (node.isEnabled())
        game.interaction.add(name, node, { outline: name !== PHONE && name !== DRAWER });
    game.bus.on("interact:use", ({ id }) => this.onUse(id));
    new SavePoint(game, "interact_save_studio", new Vector3(-0.18, 0.8, -3.12), "STUDIO", () =>
      game.checkpoints.mark(this.captureProgress(), "Studio · Writing desk"),
    );
    game.bus.on("interact:focus", ({ id }) => {
      if (id === ILLUSTRATION) game.hints.show("hint.use");
      if (id === DRAWER && !this.drawerOpen) game.hints.show("hint.drawer", 8);
      if (id === "matchbox") game.hints.show("hint.takeMatches", 8);
      if (id === PHONE) {
        game.hints.hide();
        if (this.ringing) game.hints.show("hint.phone", 8);
      }
    });
  }

  /** Starts the prologue once the game's post-processing exists. */
  async begin(): Promise<void> {
    const game = this.game;
    game.atmosphere.baseExposure = 1.25;
    game.atmosphere.maxExposure = 3.1;
    game.atmosphere.nightSightIntensity = 1.8;
    game.addFlameLights(this.lights.deskLamp, this.lights.candle);
    game.scene.onBeforeRenderObservable.add(() => this.update(game.deltaSeconds));
    if (import.meta.env.DEV) (window as unknown as { prologue: Prologue }).prologue = this;
    await this.run();
  }

  private update(dt: number): void {
    const game = this.game;
    this.playTime += dt;
    this.lights.update(dt);
    this.details.updateTelephoneCord(game.hands.phoneCordPoint);
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
    await game.fade.waitForEnter(() => {
      void game.input.lockPointer();
      void game.audio?.unlock();
    });
    await this.makeSounds();

    // P01: rain, the clock, the desk lamp. Pencil hints if the player sits still.
    void game.fade.to(0, 3);
    game.cutscene = false;
    game.interaction.allow = (id) => id === ILLUSTRATION || id === "interact_save_studio";
    void this.idleHints();

    game.flags.set("ep1.opening.version", 2);
    if (!game.flags.has("game.run")) game.flags.set("game.run", crypto.randomUUID());
    if (!game.resumedSave) await this.saveProgress("Studio · Drafting table");
    // Completed studio beats do not replay after a reload.
    if (!game.flags.get("ep1.illustration.inked", false)) {
      await this.used(ILLUSTRATION);
      game.cutscene = true;
      await this.drawIllustration();
      game.flags.set("ep1.illustration.inked", true);
      game.cutscene = false;
      await this.saveProgress("Studio · Packing for home");
    } else void this.ink.inkLine(0.01);
    game.interaction.allow = () => true;

    // P03–P04: the drawer, the letters and the kit, in any order (see onUse).
    await this.until(() => KIT.every((item) => game.inventory.has(item)));
    game.flags.set("ep1.kit.collected", true);

    if (!game.flags.has("ep1.clock.stopped")) {
      await this.wait(TIMING.dreadDelay);
      this.lights.strike();
      void this.ink.spill(2.4);
      this.play("candle");
      this.play("clockStop");
      game.flags.set("ep1.clock.stopped", "20:12");
      game.satchel.close();
      game.sketchbook?.write(INK_BLOT_ENTRY);
      await this.saveProgress("Studio · The telephone call");
      await this.wait(2.5);
      game.hints.show("hint.sketchbook", 8);
    } else void this.ink.spill(0.01);
    this.lights.snuffCandle();
    this.sfx.get("clock")?.stop();

    // P06: the telephone rings until Sora answers.
    if (!game.flags.get("ep1.phone.answered", false)) {
      await this.wait(TIMING.ringDelay);
      // The ink-blot entry opens the book automatically. Put it away as the
      // phone rings so the reading gate cannot silently block answering with E.
      game.sketchbook?.close();
      game.satchel.close();
      this.ringing = true;
      this.sfx.get("ring")?.play();
      setTimeout(() => {
        if (this.ringing) game.hints.show("hint.phone");
      }, 5000);
      await this.used(PHONE);
      await this.phoneCall();
      await this.saveProgress("Studio · After the phone call");
    }

    // P07: out of the door, into the night.
    await this.used(DOOR);
    await this.leave();
  }

  private async drawIllustration(): Promise<void> {
    const game = this.game;
    const yaw = game.player.yaw,
      pitch = game.player.pitch;
    const heldStill = game.gated.holdStill,
      heldLook = game.gated.holdLook;
    game.inspectObject(drawingFocus(this.mesh(ILLUSTRATION)), DRAWING_VIEW_RADIUS);
    game.gated.holdStill = true;
    game.gated.holdLook = true;
    try {
      this.play("pen");
      await this.ink.inkLine(3.6);
    } finally {
      game.stopInspecting();
      game.player.yaw = yaw;
      game.player.pitch = pitch;
      game.gated.holdStill = heldStill;
      game.gated.holdLook = heldLook;
    }
  }

  private async phoneCall(): Promise<void> {
    const game = this.game;
    this.ringing = false;
    game.hints.performed("hint.phone");
    this.sfx.get("ring")?.stop();
    game.cutscene = true;
    game.gated.holdStill = true;
    this.node("telephone_earpiece")?.setEnabled(false);
    game.hands.holdPhone(true);
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
    game.hands.holdPhone(false);
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
    game.flags.set("ep1.travel.pending", true);
    game.flags.set("ep1.opening.version", 2);
    game.flags.set("ep1.checkpoint", "CP0");
    game.flags.set("ep1.clock", "20:12");
    game.flags.set("sketchbook.written", [...(game.sketchbook?.written ?? [])].join(","));
    const checkpoint = {
      ...newGameSave(),
      checkpoint: "CP0",
      clock: "20:12",
      flags: game.flags.toJSON(),
      inventory: game.inventory.toJSON(),
      lamp: { oil: 1, state: "out" as const },
      playTimeSec: (game.resumedSave?.playTimeSec ?? 0) + Math.round(this.playTime),
    };
    while (true) {
      try {
        await game.checkpoints.mark(checkpoint, "Taxi · Departing Phnom Penh");
        game.bus.emit("checkpoint:reached", { id: "CP0" });
        break;
      } catch {
        await game.fade.show({
          title: "The journey could not be saved",
          body: "Your progress is still here. Free some browser storage, then retry.",
          button: "Retry save",
        });
      }
    }
    // The saved section selects the taxi; the village is saved after arrival.
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
    if (
      (id === PHONE || id === DOOR) &&
      !this.ringing &&
      !game.flags.get("ep1.phone.answered", false)
    ) {
      const missing = KIT.find((item) => !game.inventory.has(item));
      game.hints.show(missing ? KIT_HINTS[missing] : "hint.phoneQuiet", 8);
    }
  }

  /** P03: the drawer slides out: Yay Mey's letters, tied with red string, and the matchbox. */
  private openDrawer(restoring = false): void {
    this.drawerOpen = true;
    this.game.flags.set("ep1.studio.drawerOpen", true);
    this.play("drawer");
    const parts = [DRAWER, "drawer_knob", "letters_string", "matchbox"].map((n) => this.node(n));
    for (let i = 0; i < 5; i++) parts.push(this.node(`letter_${i}`));
    const start = parts.map((n) => n?.getAbsolutePosition().clone());
    let t = 0;
    const move = (ease: number) =>
      parts.forEach((n, i) => {
        const from = start[i];
        if (n && from)
          n.setAbsolutePosition(from.add(new Vector3(-this.details.drawerTravel * ease, 0, 0)));
      });
    if (restoring) move(1);
    else {
      const slide = this.game.scene.onBeforeRenderObservable.add(() => {
        t = Math.min(1, t + this.game.deltaSeconds / 0.45);
        const ease = 1 - (1 - t) ** 3;
        move(ease);
        if (t >= 1) {
          slide.remove();
          // Lean toward the exposed contents; movement keys leave inspection.
          const match = this.node("matchbox");
          if (match && !this.game.inventory.has("matches")) {
            this.game.inspectObject(match.getAbsolutePosition(), 0.2);
            this.game.hints.show("hint.takeMatches", 10);
          }
          void this.saveProgress();
        }
      });
    }
    const letters = [
      this.node("letters_string"),
      ...[0, 1, 2, 3, 4].map((i) => this.node(`letter_${i}`)),
    ];
    if (!this.game.inventory.has("letters"))
      this.game.interaction.add(
        "letters",
        letters.flatMap((n) => (n ? meshesOf(n) : [])),
      );
    const matchbox = this.node("matchbox");
    if (matchbox && !this.game.inventory.has("matches"))
      this.game.interaction.add("matchbox", matchbox);
  }

  private async take(id: string, item: string, count = 1): Promise<void> {
    const game = this.game;
    if (this.taking.has(id) || game.inventory.has(item)) return;
    this.taking.add(id);
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
    if (item === "matches") game.hints.performed("hint.takeMatches");
    // P04: the satchel opens once by itself, to show where things go.
    if (item === "satchel") {
      game.toggleSatchel();
      game.hints.show("hint.satchel", 8);
    }
    await this.saveProgress();
  }

  captureProgress(): SaveData {
    const g = this.game;
    g.flags.set("sketchbook.written", [...(g.sketchbook?.written ?? [])].join(","));
    g.flags.set("ep1.checkpoint", "CP0");
    const clock = g.flags.has("ep1.clock.stopped") ? "20:12" : "20:00";
    g.flags.set("ep1.clock", clock);
    return {
      ...newGameSave(),
      checkpoint: "CP0",
      clock,
      flags: g.flags.toJSON(),
      inventory: g.inventory.toJSON(),
      lamp: { oil: 1, state: "out" },
      playTimeSec: (g.resumedSave?.playTimeSec ?? 0) + Math.round(this.playTime),
    };
  }

  async saveProgress(location?: string): Promise<void> {
    const g = this.game;
    const name =
      location ??
      (g.flags.get("ep1.phone.answered", false)
        ? "Studio · After the phone call"
        : "Studio · Packing for home");
    try {
      await g.checkpoints.mark(this.captureProgress(), name);
    } catch {
      g.hints.show("note.saveFailed", 7);
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

  /** Placeholder sounds (src/episodes/ep1/audio/prologueSounds.ts), placed where they happen. */
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
    // A small plastered room: Sora's own steps and the telephone ring in it.
    audio.setSpace("studio", 0);
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
