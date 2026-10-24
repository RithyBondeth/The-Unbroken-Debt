import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { Game } from "../../../core/Game";
import type { Area } from "../../../core/AreaLoader";
import { boardCreak, seededRandom, wetStep } from "../../../audio/synth";
import { newGameSave } from "../../../systems/saves/SaveData";
import type { SaveData } from "../../../systems/saves/SaveData";
import { ACT_TWO_OPENING, ARRIVAL, ARRIVAL_NOTE, TENT_FLAME_MESH } from "../data/arrival";
import type { Line } from "../data/prologue";
import { coldGust } from "../audio/actTwoSounds";
import type { BetelOffering } from "./BetelOffering";
import type { NightLife } from "./NightLife";
import type { Vigil } from "./Vigil";
import type { VillageLights } from "./VillageLights";
import { INCENSE_SECONDS } from "./Vigil";
import { VigilProgress } from "./VigilProgress";
import { VillageDoor } from "./VillageDoor";
import type { ArrivalModels } from "./ArrivalModels";
import { ArrivalProgress } from "./ArrivalProgress";
import { DocumentReader } from "../../../ui/html/DocumentReader";
import { BLESSED_MATCHES } from "../data/betel";
import { phoneRing, lineStatic } from "../audio/prologueSounds";

/** CP2's clear aisle at the south end of the pavilion, facing the house. */
export const CP2_FEET = new Vector3(0, 0, -2);

/** Arrival, optional Act I exploration, and the A1-12 → A2-02 handover. */
export class ActOneBeats {
  readonly progress: VigilProgress;
  readonly arrival: ArrivalProgress;
  private readonly note = new DocumentReader(ARRIVAL_NOTE, "Mak Yey’s instructions");
  private ring: StaticSound | null = null;
  private line: StaticSound | null = null;
  private readonly sok: VillageDoor;
  private readonly shed: VillageDoor;
  private readonly flames;
  private readonly steps: StaticSound[] = [];
  private gust: StaticSound | null = null;
  private creak: StaticSound | null = null;
  private started = false;
  private busy = false;
  private opening = -1;
  private gustPlayed = false;
  private nextStep = 0;
  private playTime = 0;
  private courtyardPause = 0;
  private readonly entries: string[] = [];

  constructor(
    private readonly game: Game,
    private readonly area: Area,
    private readonly lights: VillageLights,
    private readonly vigil: Vigil,
    private readonly betel: BetelOffering,
    private readonly night: NightLife,
    private readonly arrivalModels: ArrivalModels,
  ) {
    this.progress = new VigilProgress(game.flags, INCENSE_SECONDS);
    this.arrival = new ArrivalProgress(game.flags);
    game.interaction.add("interact_arrival_note", arrivalModels.note);
    game.interaction.add("interact_arrival_phone", arrivalModels.phone);
    if (this.arrival.taken) arrivalModels.matches.setEnabled(false);
    else game.interaction.add("interact_blessed_matches", arrivalModels.matches);
    const door = (id: string, collider: string, lock: string) => {
      const marker = area.level.interactables.find((m) => m.name === id);
      if (!marker) throw new Error(`[Act I] missing ${id}`);
      return new VillageDoor(game.scene, marker, collider, lock);
    };
    this.sok = door("interact_door_sok", "col_door_sok", "door_sok_padlock");
    this.shed = door("interact_shed_door", "col_shed_door", "shed_padlock");
    this.flames = area.container.meshes.filter((m) => TENT_FLAME_MESH.test(m.name));
    if (game.flags.get("ep1.shed.opened", false)) this.shed.open(true);
    if (game.flags.get("ep1.act2.started", false)) {
      this.lights.hangingLevel = 0;
      for (const flame of this.flames) flame.setEnabled(false);
      this.sok.open(true);
      this.night.threatSilence = 1;
    }
    game.bus.on("interact:use", ({ id }) => this.use(id));
  }

  async makeSounds(): Promise<void> {
    const audio = this.game.audio;
    if (!audio) return;
    const rate = audio.context.sampleRate;
    const at = this.sok.marker.position;
    this.ring = await audio.spatialSound(
      "arrival_phone_ring",
      audio.buffer(phoneRing(rate, seededRandom(96)), rate),
      "sfx",
      this.arrivalModels.phone.position,
      { minDistance: 5, volume: 0.7, loop: true },
    );
    this.line = await audio.spatialSound(
      "arrival_phone_line",
      audio.buffer(lineStatic(rate, seededRandom(97)), rate),
      "sfx",
      this.arrivalModels.phone.position,
      { minDistance: 2, volume: 0.16, loop: true },
    );
    this.gust = await audio.spatialSound(
      "cold_gust",
      audio.buffer(coldGust(rate, seededRandom(91)), rate),
      "threat",
      CP2_FEET.add(new Vector3(0, 1.5, -2)),
      { minDistance: 5, volume: 0.8 },
    );
    this.creak = await audio.spatialSound(
      "upstairs_creak",
      audio.buffer(boardCreak(rate, seededRandom(92)), rate),
      "threat",
      at,
      { minDistance: 6, volume: 0.6 },
    );
    for (let k = 0; k < 3; k++)
      this.steps.push(
        await audio.spatialSound(
          `upstairs_step_${k}`,
          audio.buffer(wetStep(rate, seededRandom(93 + k)), rate),
          "threat",
          at,
          { minDistance: 7, volume: 0.85 },
        ),
      );
  }

  async begin(): Promise<void> {
    this.started = true;
    if (!this.arrival.called) this.ring?.play();
    if (this.game.flags.get("ep1.arrival.road", false)) return;
    await this.dialogue(ARRIVAL.road);
    this.game.flags.set("ep1.arrival.road", true);
  }

  update(dt: number): void {
    if (!this.started) return;
    this.playTime += dt;
    this.sok.update(dt);
    this.shed.update(dt);
    this.progress.update(dt);
    const game = this.game;
    const feet = game.player.feet;
    // A1-02: the first view of the white tent. Do not force the camera.
    if (
      !game.cutscene &&
      !game.flags.get("ep1.arrival.courtyard", false) &&
      feet.z < 9 &&
      feet.z > -1
    ) {
      game.flags.set("ep1.arrival.courtyard", true);
      game.bus.emit("sequence:start", { id: "A1-02" });
      game.gated.holdStill = true;
      this.courtyardPause = 3;
    }
    if (this.courtyardPause > 0) {
      this.courtyardPause -= dt;
      if (this.courtyardPause <= 0) {
        game.gated.holdStill = false;
        game.bus.emit("sequence:end", { id: "A1-02" });
      }
    }
    if (
      !this.busy &&
      this.courtyardPause <= 0 &&
      !game.cutscene &&
      !game.flags.get("ep1.vigil.started", false) &&
      this.underTent()
    )
      if (!game.flags.get("ep1.arrival.emptyNoticed", false)) {
        game.flags.set("ep1.arrival.emptyNoticed", true);
        game.hints.show("note.arrivalEmpty", 9);
      }
    if (this.entries.length && game.sketchbook && !game.sketchbook.isBusy && !game.cutscene) {
      const entry = this.entries.shift() as string;
      if (!game.sketchbook.written.has(entry)) game.sketchbook.write(entry);
    }
    if (this.opening >= 0) this.updateOpening(dt);
    else if (
      this.progress.ready(
        this.underTent(),
        !this.busy &&
          !game.inspecting &&
          !game.cutscene &&
          !game.satchel.isOpen &&
          !(game.sketchbook?.isBusy || game.sketchbook?.isOpen),
      )
    )
      this.startOpening();
  }

  private underTent(): boolean {
    const p = this.game.player.feet;
    return Math.abs(p.x) < 3.8 && p.z < -1 && p.z > -7 && p.y < 0.5;
  }

  /** Both relatives speak through the hall telephone; an interrupted call can be replayed. */
  private async call(): Promise<void> {
    if (this.busy || this.arrival.called) return;
    this.busy = true;
    this.ring?.stop();
    this.line?.play();
    this.arrivalModels.receiver.setEnabled(false);
    this.game.hands.holdPhone(true);
    try {
      await this.dialogue([...ARRIVAL.greeting, ...ARRIVAL.vuthy, ...ARRIVAL.duties], async () => {
        await this.betel.ask(true);
        await this.game.subtitles.say(
          "Mak Yey · Phone",
          "I must rest now. Vuthy will be there at dawn. Keep the watch, child.",
          5,
        );
      });
      this.arrival.finishCall();
      this.game.hints.show("note.arrivalMatches", 8);
      await this.saveProgress();
    } finally {
      this.line?.stop();
      this.arrivalModels.receiver.setEnabled(true);
      this.game.hands.holdPhone(false);
      this.busy = false;
    }
  }

  private readNote(): void {
    const game = this.game;
    this.busy = true;
    game.cutscene = true;
    game.gated.holdStill = true;
    game.satchel.close();
    game.sketchbook?.close();
    document.exitPointerLock();
    this.note.show(0, () => {
      game.flags.set("ep1.arrival.noteRead", true);
      game.cutscene = false;
      game.gated.holdStill = false;
      this.busy = false;
      if (!this.arrival.called) game.hints.show("note.arrivalPhone", 8);
      void this.saveProgress();
    });
  }

  private async dialogue(lines: Line[], extra?: () => Promise<void>): Promise<void> {
    const game = this.game;
    game.cutscene = true;
    game.gated.holdStill = true;
    game.satchel.close();
    if (game.sketchbook?.isOpen) game.sketchbook.toggle();
    try {
      for (const line of lines) await game.subtitles.say(line.speaker, line.text, line.seconds);
      await extra?.();
    } finally {
      game.gated.holdStill = false;
      game.cutscene = false;
    }
  }

  /** A1-07, A1-11: inspect the thread, find the key, open the shed and collect its lore. */
  private use(id: string): void {
    const game = this.game;
    if (game.cutscene || this.busy) return;
    if (id === "interact_arrival_note") return this.readNote();
    if (id === "interact_arrival_phone") {
      if (this.arrival.called) game.hints.show("note.arrivalCallEnded", 5);
      else void this.call();
      return;
    }
    if (id === "interact_blessed_matches") {
      if (this.arrival.takeMatches()) {
        game.inventory.add("blessed_matches", BLESSED_MATCHES);
        this.arrivalModels.matches.setEnabled(false);
        game.interaction.remove(id);
        game.hints.show("note.blessed", 4);
        void this.saveProgress();
      }
      return;
    }
    if (id === "interact_door_sok") {
      if (!game.flags.get("ep1.sok.unlocked", false)) game.hints.show("note.sokLocked", 4);
      return;
    }
    if (id === "interact_thread") {
      game.flags.set("ep1.thread.inspected", true);
      game.hints.show(
        game.flags.get("ep1.thread.broken", false) ? "note.threadBroken" : "note.threadWhole",
        4,
      );
    } else if (id === "interact_sewing_box") {
      if (game.inventory.has("shed_key")) return;
      game.inventory.add("shed_key");
      game.flags.set("ep1.sewingBox.opened", true);
      game.hints.show("note.shedKey", 4);
    } else if (id === "interact_shed_door") {
      if (!game.inventory.has("shed_key")) return game.hints.show("note.shedLocked", 4);
      this.shed.open();
      game.flags.set("ep1.shed.opened", true);
      game.interaction.remove(id);
    } else if (id === "interact_land_deed" || id === "interact_kanha_photo") {
      const marker = this.area.level.interactables.find((m) => m.name === id);
      if (!marker || game.flags.get(`ep1.pickup.${id}`, false)) return;
      game.flags.set(`ep1.pickup.${id}`, true);
      game.flags.set(`lore.ep1.${String(marker.extras.lore)}`, true);
      game.flags.increment("ep1.lore");
      game.interaction.remove(id);
      marker.node.setEnabled(false);
      this.entries.push(id === "interact_land_deed" ? "L4" : "L5");
      game.hints.show(id === "interact_land_deed" ? "note.landDeed" : "note.kanhaPhoto", 5);
    }
  }

  private startOpening(): void {
    const game = this.game;
    game.flags.set("ep1.act1.complete", true);
    game.flags.set("ep1.act2.started", true);
    game.flags.set("ep1.clock", "01:00");
    game.bus.emit("sequence:start", { id: "A2-01" });
    game.cutscene = true;
    game.gated.holdStill = true;
    this.opening = 0;
  }

  /** Game-time timeline: hidden tabs cannot race timers past the sound cues. */
  private updateOpening(dt: number): void {
    this.opening += dt;
    const t = this.opening;
    const timing = ACT_TWO_OPENING;
    this.night.threatSilence = Math.min(1, t / timing.quietSeconds);
    if (t >= timing.quietSeconds) {
      if (!this.gustPlayed) {
        this.gustPlayed = true;
        this.gust?.play();
      }
      const snuff = Math.min(1, (t - timing.quietSeconds) / timing.snuffSeconds);
      this.lights.hangingLevel = 1 - snuff;
      for (const flame of this.flames) flame.visibility = 1 - snuff;
    }
    while (this.nextStep < timing.stepTimes.length && t >= timing.stepTimes[this.nextStep]) {
      // The sound crosses the actual upper hall towards Sok's door, at floor height.
      const k = this.nextStep++;
      const at = new Vector3(1.5 - k * 0.9, 2.55, -13.45);
      const sound = this.steps[k % Math.max(1, this.steps.length)];
      if (sound) {
        sound.spatial.position = at;
        sound.play();
      }
      if (k === 0) this.creak?.play();
    }
    if (t < timing.endSeconds) return;
    this.opening = -1;
    for (const flame of this.flames) flame.setEnabled(false);
    this.game.flags.set("ep1.checkpoint", "CP2");
    this.game.flags.set("ep1.sok.unlocked", true);
    this.sok.open();
    this.game.interaction.remove("interact_door_sok");
    this.game.gated.holdStill = false;
    this.game.cutscene = false;
    this.game.bus.emit("sequence:end", { id: "A2-01" });
    void this.game.subtitles.say("Sora", "Footsteps? But they’ve both gone…", 2.5);
    this.entries.push("SB-A2-01");
    this.game.hints.show("note.upstairs", 6);
    void this.saveProgress();
  }

  /** Capture synchronously so a catch cannot race an in-flight disk write. */
  captureProgress(): SaveData {
    const game = this.game;
    this.progress.save();
    this.vigil.saveState();
    this.betel?.saveState();
    const written = new Set([
      ...game.flags.get("sketchbook.written", "").split(",").filter(Boolean),
      ...(game.sketchbook?.written ?? []),
      ...this.entries,
      ...(this.betel?.pendingEntries ?? []),
    ]);
    game.flags.set("sketchbook.written", [...written].join(","));
    return {
      ...newGameSave(),
      checkpoint: game.flags.get(
        "ep1.checkpoint",
        game.flags.get("ep1.act2.started", false) ? "CP2" : "CP1",
      ),
      clock: game.flags.get(
        "ep1.clock",
        game.flags.get("ep1.act2.started", false) ? "01:00" : "23:30",
      ),
      flags: game.flags.toJSON(),
      inventory: game.inventory.toJSON(),
      lamp: this.vigil.toJSON(),
      playTimeSec: (game.resumedSave?.playTimeSec ?? 0) + Math.round(this.playTime),
    };
  }

  async saveProgress(): Promise<SaveData> {
    const game = this.game;
    const save = this.captureProgress();
    try {
      await game.saves.save("autosave", save);
      game.bus.emit("checkpoint:reached", { id: save.checkpoint });
    } catch (error) {
      // Storage can be unavailable or full: the story must still be playable.
      console.warn(`[${save.checkpoint}] could not save`, error);
      game.hints.show("note.saveFailed", 6);
    }
    return save;
  }
}
