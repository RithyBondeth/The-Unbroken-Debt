import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import type { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { CreateBox } from "@babylonjs/core/Meshes/Builders/boxBuilder";
import type { Game } from "@/core/Game";
import { loadArea, type Area } from "@/core/areaLoader";
import { meshesOf } from "@/systems/interaction/Interaction";
import type { BusName, SpatialOptions } from "@/audio/AudioSystem";
import { seededRandom } from "@/audio/synth";
import * as sounds from "../audio/prologueSounds";
import { DreadScore } from "@/audio/DreadScore";
import { PhoneBell } from "../audio/PhoneBell";
import { studioRoom } from "@/audio/sounds/dreadSounds";
import { newGameSave } from "@/systems/saves/SaveData";
import { INK_BLOT_ENTRY, KIT, LINES, STARTING_MATCHES, TIMING, type Line } from "../data/prologue";
import { loadStudioLightmap, StudioLights } from "./Studio";
import { Rain } from "@/render/weather/Rain";
import { InkMarks } from "./InkMarks";
import { t, type StringKey } from "@/data/strings";
import { Objectives, type Objective } from "@/ui/html/StoryUi";
import { StudioDetails } from "./StudioDetails";
import { DancerGhost } from "./DancerGhost";
import { shufflePosters } from "./posterShuffle";
import { creak, knock, powerDown, powerUp, whisper } from "../audio/dancerSounds";
import { POWER_RETURN_LENGTH } from "../data/powerCut";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import type { SaveData } from "@/systems/saves/SaveData";
import { SavePoint } from "@/systems/saves/SavePoint";
import { warmSceneViews } from "@/render/warmSceneViews";

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

/** The packing checklist: each kit item and where it is in the room. */
const KIT_PLACES: Record<(typeof KIT)[number], StringKey> = {
  satchel: "objective.satchel",
  sketchbook: "objective.sketchbook",
  matches: "objective.matches",
  lamp: "objective.lamp",
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
  private readonly rain: Rain[] = [];
  private ink!: InkMarks;
  private readonly waiting = new Map<string, () => void>();
  private readonly loops: StaticSound[] = [];
  private sfx = new Map<string, StaticSound>();
  private score = new DreadScore(null);
  private drawerOpen = false;
  private ringing = false;
  private bell = new PhoneBell(null);
  private room: StaticSound | null = null;
  private playTime = 0;
  private wasFlashing = false;
  private readonly taking = new Set<string>();
  private readonly objectives = new Objectives();
  details!: StudioDetails;
  dancer!: DancerGhost;
  /** When the house next makes a sound of its own (play time, s). */
  private nextScare = 24;

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
        /^window_glass/,
        // Lamp fixtures stay apart so their own lights can leave them out (Studio.ts).
        /^sconce_/,
        /^airwell_bulb/,
        /^back_room_pendant/,
        // The posters' slots keep their own UVs (posterShuffle.ts).
        /^poster90_[pl]_\d+$/,
        // Sora's diary is the save point: it stays itself to be picked and hinted.
        /^save_journal/,
      ],
    });
    this.details = new StudioDetails(game.scene, this.area);
    // Contact shadows and generous targets for what Sora takes (nothing is baked under them).
    this.details.groundPickups();
    shufflePosters(game.scene);
    // The plaster cracks are decals 1.5 mm off the walls: drawn over them, never into them.
    for (const material of game.scene.materials)
      if (material instanceof PBRMaterial && material.name.startsWith("M_studio_cracks")) {
        material.zOffset = -2;
        material.disableDepthWrite = true;
        material.backFaceCulling = true;
      }
    // The dancer ghost in the back room, against the far wall, facing the doorway.
    this.dancer = new DancerGhost(
      game,
      this.area.level.markers.get("dancer_ghost")?.position.clone() ?? new Vector3(-3.0, 0, -13.4),
      new Vector3(-0.6, 0, -9.27),
    );
    await this.dancer.load();
    if (
      game.flags.get("ep1.studio.dancerSeen", false) ||
      game.flags.get("ep1.phone.answered", false)
    )
      this.dancer.skip();
    // She comes with the dark: every lamp in the house dies as Sora steps into the
    // doorway, she can only stand and look, and the lights stutter back when she is gone.
    this.dancer.onBlackout = () => {
      this.lights.lightsOut();
      this.play("powerDown", game.camera.globalPosition);
      game.cutscene = true;
      game.player.inputEnabled = false;
      game.satchel.close();
    };
    this.dancer.onAppear = () => this.score.pressure(1);
    this.dancer.onVanish = () => {
      this.lights.lightsBack();
      this.play("powerUp", game.camera.globalPosition);
    };
    // Every press of E counts here: with nothing quite under the eye, the nearest thing
    // within 14 degrees is taken.
    game.interaction.pressAssistDegrees = 14;
    const lightmap = await loadStudioLightmap(game.scene, game.preset);
    this.lights = new StudioLights(game.scene, this.area, game.preset, lightmap);
    // Rain runs down the glass of both balcony doors.
    for (const glass of game.scene.meshes.filter((m) => /^window_glass/.test(m.name)))
      this.rain.push(new Rain(game.scene, glass));
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
    for (const ladder of this.area.level.ladders) game.player.addLadder(ladder);
    game.player.pitch = 0.6;

    // Studio checkpoints restore the collected props and drawer, not just inventory.
    for (const [id, pickup] of Object.entries(PICKUPS)) {
      if (!game.inventory.has(pickup.item)) continue;
      const names =
        id === "letters" ? ["letters_string", ...[0, 1, 2, 3, 4].map((i) => `letter_${i}`)] : [id];
      for (const name of names) this.node(name)?.setEnabled(false);
    }
    if (game.flags.get("ep1.studio.drawerOpen", false)) this.openDrawer(true);

    // The illustration is no longer something to use (the opening drawing beat was
    // cut in November 2026): it is simply there, half inked, until the ink spills.
    for (const { name, node } of this.area.level.interactables)
      if (node.isEnabled() && name !== ILLUSTRATION && !(name === DRAWER && this.drawerOpen))
        game.interaction.add(name, node);
    game.bus.on("interact:use", ({ id }) => this.onUse(id));
    const savePoint =
      this.area.level.markers.get("save_studio")?.position.clone() ??
      new Vector3(-0.18, 0.8, -3.12);
    // Sora's diary open on the writing desk is the safe place (tools/areas/ep1_area_studio.py,
    // open_journal); the stock folio and votive stand in if it is missing.
    const journal = game.scene.getTransformNodeByName("save_journal");
    new SavePoint(
      game,
      "interact_save_studio",
      savePoint,
      "STUDIO",
      () => game.checkpoints.mark(this.captureProgress(), "Studio · Writing desk"),
      undefined,
      journal
        ? {
            root: journal,
            hint: "hint.savePoint",
            saving: () => undefined,
            settled: () => undefined,
          }
        : undefined,
    );
    game.bus.on("interact:focus", ({ id }) => {
      if (id === DRAWER && !this.drawerOpen) game.hints.show("hint.drawer", 8);
      if (id === "matchbox") game.hints.show("hint.takeMatches", 8);
      if (id === PHONE) {
        game.hints.hide();
        if (this.ringing) game.hints.show("hint.phone", 8);
      }
    });
  }

  /**
   * Draws every room of the floor once behind the black opening screen, the dancer in
   * her corner among them: built the first time they came into view, the airwell's and
   * the back room's shaders and pipelines stalled the frame for most of a second, the
   * second of them just as the dancer was revealed (November 2026). Runtime coordinates
   * (x = -Blender x, z = -Blender y).
   */
  async warmup(): Promise<void> {
    const game = this.game;
    const view = (eye: [number, number], target: [number, number, number]) => ({
      eye: new Vector3(eye[0], 1.58, eye[1]),
      target: new Vector3(...target),
    });
    const hide = this.dancer.prepareWarm();
    try {
      await warmSceneViews(game.scene, game.camera, [
        view([-2.3, -0.6], [-2.3, 1.3, -5.5]),
        view([-2.5, -3.0], [-0.3, 1.0, -2.7]),
        view([-2.3, -5.0], [-2.3, 1.4, 0.5]),
        view([-1.2, -6.6], [-2.5, 1.0, -8.5]),
        view([-2.3, -6.8], [-1.0, 1.2, -9.4]),
        view([-3.5, -8.5], [-0.5, 1.0, -7.5]),
        view([-0.9, -10.3], [-1.9, 1.0, -13.5]),
        view([-2.5, -11.5], [-3.5, 1.0, -9.8]),
        view([-2.0, -13.0], [-0.6, 1.3, -9.3]),
      ]);
    } finally {
      hide();
    }
  }

  /** Starts the prologue once the game's post-processing exists. */
  async begin(): Promise<void> {
    const game = this.game;
    // No TAA in the studio: standing still, its jitter never settled in this dark,
    // flickering room, and the whole picture crawled and shook (November 2026). FXAA
    // smooths the edges on its own and the image holds still.
    if (game.pipeline.taa) game.pipeline.taa.isEnabled = false;
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
    for (const rain of this.rain) rain.update(dt, this.lights.lightning.intensity / 60);
    this.ink.update(dt);
    this.score.update(dt);
    this.bell.update(dt);
    this.dancer.update(dt);
    // In the power cut the dark is total: no eyes adjusting, no night sight.
    const power = this.lights.power;
    // Held down for the dancer, the dark is not total: Sora's eyes stay open to the glow
    // that is left, and the room reads round her (the user found it too dark).
    const eyes = this.lights.dimmed ? 0.8 : power;
    game.atmosphere.baseExposure = 1.25 * (0.3 + 0.7 * eyes);
    game.atmosphere.nightSightIntensity = 1.8 * eyes;
    game.atmosphere.update(dt, this.lights.lightAtEye(game.camera.globalPosition));
    this.houseSounds();
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

    // P01: rain, the storm and the desk lamp; Sora at her drafting table, the Wat
    // Phnom illustration inked to the middle. Look and move hints if she sits still.
    void game.fade.to(0, 3);
    game.cutscene = false;
    game.interaction.allow = () => true;
    void this.idleHints();
    void this.ink.inkLine(0.01);

    game.flags.set("ep1.opening.version", 2);
    if (!game.flags.has("game.run")) game.flags.set("game.run", crypto.randomUUID());
    if (!game.resumedSave) await this.saveProgress("Studio · Drafting table");

    // P03–P04: the drawer, the letters and the kit, in any order (see onUse). The
    // satchel is on the bed in the back room, and the back room is where the dancer
    // waits: the moment Sora sees her, the storm breaks and the telephone rings, packed
    // or not; whatever is still unpacked is packed after the call.
    this.showObjectives();
    if (!game.flags.get("ep1.phone.answered", false)) {
      if (!game.flags.get("ep1.studio.dancerSeen", false)) {
        await this.dancer.seen();
        // The lights come back first; then she can move again.
        await this.wait(POWER_RETURN_LENGTH + 0.25);
        game.cutscene = false;
        game.player.inputEnabled = true;
      }
      // P05: lightning, the candle dies, the ink spills across the drawing, the clock stops.
      game.satchel.close();
      if (!game.flags.has("ep1.clock.stopped")) {
        this.lights.strike();
        void this.ink.spill(2.4);
        game.flags.set("ep1.clock.stopped", "20:12");
        // Written into the book quietly: it must not open over the ringing phone.
        const book = game.sketchbook;
        if (book && !book.written.has(INK_BLOT_ENTRY))
          book.restore([...book.written, INK_BLOT_ENTRY]);
        void this.saveProgress("Studio · The telephone call");
      } else void this.ink.spill(0.01);
      this.lights.snuffCandle();
      // P06: a breath of silence, then the telephone, ringing until Sora answers.
      await this.wait(1.1);
      game.sketchbook?.close();
      this.ringing = true;
      this.room?.play();
      this.score.pressure(0.6);
      this.bell.start();
      this.showObjectives();
      game.hints.show("hint.phone", 12);
      await this.used(PHONE);
      await this.phoneCall();
      await this.saveProgress("Studio · After the phone call");
    } else void this.ink.spill(0.01);
    if (game.flags.has("ep1.clock.stopped")) this.lights.snuffCandle();
    this.showObjectives();
    await this.until(() => KIT.every((item) => game.inventory.has(item)));
    game.flags.set("ep1.kit.collected", true);
    game.satchel.close();

    // P07: out of the door, into the night.
    this.showObjectives();
    await this.used(DOOR);
    this.objectives.hide();
    await this.leave();
  }

  private async phoneCall(): Promise<void> {
    const game = this.game;
    this.ringing = false;
    this.dancer.heartbeat(false);
    game.hints.performed("hint.phone");
    this.bell.stop();
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
    this.score.sting("shock", 0.75);
    this.lights.strike();
    await cutOff;
    await this.wait(1.6);
    // The line dies: a blow of pressure, then nothing but her ears ringing.
    this.sfx.get("static")?.stop();
    this.score.sting("drop");
    this.score.ring();
    this.score.pressure(0);
    await this.wait(0.9);
    await this.say(LINES.call4);
    this.score.pressure(0.35);
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
    this.score.pressure(0);
    await game.fade.to(1, 1.5);
    for (const sound of this.loops) sound.stop();
    this.score.stop();
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
    if (pickup) {
      void this.take(id, pickup.item, pickup.count);
      return void setTimeout(() => this.lights.refreshShadows(), 600);
    }
    if (id === DRAWER && !this.drawerOpen) {
      setTimeout(() => this.lights.refreshShadows(), 600);
      return this.openDrawer();
    }
    if ((id === PHONE || id === DOOR) && !this.ringing) {
      const missing = KIT.find((item) => !game.inventory.has(item));
      if (!game.flags.get("ep1.phone.answered", false))
        game.hints.show(missing ? KIT_HINTS[missing] : "hint.phoneQuiet", 8);
      else if (id === DOOR && missing) game.hints.show(KIT_HINTS[missing], 8);
    }
  }

  /** P03: the drawer slides out: Yay Mey's letters, tied with red string, and the matchbox. */
  private openDrawer(restoring = false): void {
    this.drawerOpen = true;
    this.game.flags.set("ep1.studio.drawerOpen", true);
    // Open, it is nothing to use: it must not take E from the matches and letters in it.
    this.game.interaction.remove(DRAWER);
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
          if (!this.game.inventory.has("matches")) this.game.hints.show("hint.takeMatches", 10);
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
    // Where things go, without opening the satchel over the room (that took E away).
    if (item === "satchel") game.hints.show("hint.satchel", 6);
    if (!game.flags.get("ep1.kit.collected", false)) this.showObjectives();
    // The dread rises with each thing packed, before anything has happened.
    if (!this.ringing && !game.flags.get("ep1.phone.answered", false))
      this.score.pressure(0.12 + 0.07 * KIT.filter((k) => game.inventory.has(k)).length);
    await this.saveProgress();
  }

  /** The checklist: the telephone while it rings, what is left to pack, then the stairs. */
  private showObjectives(): void {
    const game = this.game;
    const list: Objective[] = [];
    if (this.ringing) list.push({ text: t("objective.phone") });
    if (!KIT.every((item) => game.inventory.has(item))) list.push(...this.packingList());
    else if (game.flags.get("ep1.phone.answered", false)) list.push({ text: t("objective.leave") });
    if (list.length) this.objectives.show(list);
    else this.objectives.hide();
  }

  /**
   * The house between the scares, while Sora packs and until she leaves: a board
   * taking a weight overhead, three slow knocks in the back room (until the dancer has
   * been seen), and once she has, something breathing words just behind Sora.
   */
  private houseSounds(): void {
    const game = this.game;
    if (this.playTime < this.nextScare || game.cutscene || !this.sfx.has("creak")) return;
    const eye = game.camera.globalPosition;
    const forward = game.camera.getDirection(Vector3.Forward());
    const seen = game.flags.get("ep1.studio.dancerSeen", false);
    const roll = Math.random();
    if (!seen && roll < 0.4) this.play("knock", new Vector3(-2.6, 1.0, -13.7));
    else if (seen && roll < 0.45 && !this.ringing)
      this.play("whisper", eye.subtract(forward.scale(0.7)).add(new Vector3(0, 0.05, 0)));
    else
      this.play(
        "creak",
        eye.add(new Vector3((Math.random() - 0.5) * 3, 1.7, (Math.random() - 0.5) * 3)),
      );
    this.nextScare = this.playTime + (seen ? 20 : 14) + Math.random() * 14;
  }

  /** P04: what Sora still has to pack, and where each thing is, ticked off as she takes it. */
  private packingList(): Objective[] {
    const inventory = this.game.inventory;
    return [
      { text: t("objective.pack") },
      ...KIT.map((item) => ({ text: t(KIT_PLACES[item]), done: inventory.has(item), sub: true })),
    ];
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
      ["train", sounds.trainPassing, "ambience", desk, { minDistance: 20 }],
      ["knock", knock, "sfx", desk, { minDistance: 2, volume: 0.7 }],
      ["creak", creak, "sfx", desk, { minDistance: 2, volume: 0.8 }],
      ["whisper", whisper, "threat", desk, { minDistance: 0.6, volume: 0.45 }],
      ["powerDown", powerDown, "threat", desk, { minDistance: 3, volume: 1 }],
      ["powerUp", powerUp, "threat", desk, { minDistance: 3, volume: 0.9 }],
    ];
    // A small plastered room: Sora's own steps and the telephone ring in it.
    audio.setSpace("studio", 0);
    const sampleRate = audio.context.sampleRate;
    // The room's own air, and Phnom Penh beyond the rain: it joins with the phone.
    const room = (this.room = await audio.sound(
      "studio_room",
      audio.buffer(studioRoom(sampleRate), sampleRate),
      "room",
      0.55,
    ));
    room.loop = true;
    if (this.game.flags.get("ep1.phone.answered", false)) room.play();
    this.loops.push(room);
    this.score = new DreadScore(audio);
    await this.score.load();
    await this.dancer.makeSounds();
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
      if (options.loop && name === "rain") {
        made[i].play();
        this.loops.push(made[i]);
      }
    });
    this.loops.push(made[list.findIndex(([n]) => n === "static")]);
    this.bell = new PhoneBell(this.sfx.get("ring") ?? null);
  }

  /** Plays a one-shot; `position` moves it first (the train plays at Sora's ears). */
  private play(name: string, position?: Vector3): void {
    const sound = this.sfx.get(name);
    if (!sound) return;
    if (position) sound.spatial.position = position.clone();
    sound.play();
  }
}
