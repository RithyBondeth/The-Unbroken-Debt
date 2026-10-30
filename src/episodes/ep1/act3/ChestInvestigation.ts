import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import type { Game } from "../../../core/Game";
import { ChestProgress, CHEST_ITEMS, type ChestItem } from "./ChestProgress";
import type { ChestModels } from "./ChestModels";
import { CoffinEncounter } from "./CoffinEncounter";
import { CorpseProgress } from "./CorpseProgress";
import type { CorpseModels } from "./CorpseModels";
import { boardCreak, seededRandom } from "../../../audio/synth";
import { drawerOpen, pickUp } from "../audio/prologueSounds";

/** A3-02, A3-05–06. The chest discoveries prepare the later CP6 ritual. */
export class ChestInvestigation {
  readonly progress: ChestProgress;
  readonly corpse: CorpseProgress;
  readonly coffin: CoffinEncounter;
  private readonly entries: string[] = [];
  private readonly sounds = new Map<string, StaticSound>();
  private entryDelay = 0;
  private readyWas = false;
  private dialogue: Promise<void> = Promise.resolve();
  constructor(
    private readonly game: Game,
    readonly models: ChestModels,
    readonly body: CorpseModels,
    private readonly saveProgress: () => Promise<unknown>,
  ) {
    this.progress = new ChestProgress(game.flags, game.inventory);
    this.corpse = new CorpseProgress(game.flags);
    this.readyWas = this.progress.ready;
    models.restore(this.progress.planksOpen, this.progress.unlocked, (id) =>
      this.progress.taken(id),
    );
    this.coffin = new CoffinEncounter(game, body, saveProgress);
    game.interaction.add("interact_loose_planks", models.planks);
    game.interaction.add("interact_hidden_chest", models.chest);
    for (const id of CHEST_ITEMS) game.interaction.add(`interact_chest_${id}`, models.pickups[id]);
    game.bus.on("interact:use", ({ id }) => this.use(id));
    game.bus.on("interact:focus", ({ id }) => {
      if (!this.progress.available || !this.handsFree) return;
      if (this.progress.ready && ["interact_hidden_chest", "interact_loose_planks"].includes(id)) {
        game.hints.show("note.ritualPrepared", 7);
        return;
      }
      if (id === "interact_loose_planks")
        game.hints.show(this.progress.planksOpen ? "hint.chestRecess" : "hint.chestPlanks", 4);
      if (id === "interact_hidden_chest")
        game.hints.show(this.progress.unlocked ? "hint.chestContents" : "hint.chestLock", 4);
      if (id === "interact_chest_bronze_token") game.hints.show("hint.bronzeToken", 4);
      if (id === "interact_chest_seal_map") game.hints.show("hint.chestMap", 4);
      if (id === "interact_chest_folded_slip") game.hints.show("hint.foldedSlip", 4);
    });
  }
  private get handsFree(): boolean {
    const g = this.game;
    return (
      !g.cutscene &&
      !g.threatActive &&
      !g.hiding &&
      !g.satchel.isOpen &&
      !g.sketchbook?.isOpen &&
      !g.sketchbook?.isBusy
    );
  }
  async makeSounds(): Promise<void> {
    await this.coffin.makeSounds();
    const a = this.game.audio;
    if (!a) return;
    const rate = a.context.sampleRate;
    for (const [id, data] of [
      ["planks", boardCreak(rate, seededRandom(1401))],
      ["lid", drawerOpen(rate, seededRandom(1402))],
      ["pickup", pickUp(rate, seededRandom(1403))],
    ] as const)
      this.sounds.set(
        id,
        await a.spatialSound(
          `chest_${id}`,
          a.buffer(data, rate),
          "sfx",
          this.models.root.position,
          { minDistance: 2, volume: 0.5 },
        ),
      );
  }
  update(dt: number): void {
    const g = this.game,
      p = this.progress;
    this.models.update(dt, p.planksOpen, p.unlocked, (id) => p.taken(id));
    this.coffin.update(dt, p.taken("bronze_token"));
    const paused =
      g.cutscene ||
      g.hiding ||
      g.satchel.isOpen ||
      !!g.sketchbook?.isOpen ||
      !!g.sketchbook?.isBusy ||
      this.coffin.progress.phase !== "open";
    const changed = this.corpse.update(dt, this.body.observed(g.camera), paused);
    if (this.coffin.progress.phase === "open") this.body.pose(this.corpse.pose);
    if (changed) void this.saveProgress();
    this.entryDelay = Math.max(0, this.entryDelay - dt);
    if (this.entries.length && this.entryDelay <= 0 && this.handsFree && !g.inspecting) {
      const entries = this.entries.splice(0).filter((id) => !g.sketchbook?.written.has(id));
      g.sketchbook?.restore(entries.slice(0, -1));
      const last = entries.at(-1);
      if (last) g.sketchbook?.write(last);
    }
    if (p.ready && !this.readyWas) {
      this.readyWas = true;
      this.remember("SB-07");
      this.entryDelay = 4;
      g.hints.show("note.ritualPrepared", 9);
      this.say("Before three. The burner. The blessed matches. Don’t turn around.", 6);
      g.bus.emit("sequence:end", { id: "A3-05" });
      g.bus.emit("sequence:start", { id: "A3-06" });
      void this.saveProgress();
    }
  }
  private use(id: string): void {
    if (!this.handsFree || !this.progress.available) return;
    const g = this.game,
      p = this.progress;
    if (id === "interact_loose_planks") {
      if (!p.liftPlanks()) return;
      this.sounds.get("planks")?.play();
      g.hints.show("note.chestRevealed", 6);
      g.bus.emit("sequence:start", { id: "A3-05" });
    } else if (id === "interact_hidden_chest") {
      if (!this.models.planksReady) return;
      if (p.ready) return g.hints.show("note.ritualPrepared", 7);
      if (p.unlocked) return g.hints.show("hint.chestContents", 5);
      if (!p.unlock()) return g.hints.show("note.chestNeedsKey", 5);
      this.sounds.get("lid")?.play();
      g.hints.show("hint.chestContents", 6);
    } else {
      const item = CHEST_ITEMS.find((item) => id === `interact_chest_${item}`);
      if (!item || !this.models.lidReady || !p.take(item)) return;
      this.models.pickups[item].setEnabled(false);
      this.sounds.get("pickup")?.play();
      const note: Record<ChestItem, "note.tokenTaken" | "note.mapTaken" | "note.slipTaken"> = {
        bronze_token: "note.tokenTaken",
        seal_map: "note.mapTaken",
        folded_slip: "note.slipTaken",
      };
      g.hints.show(note[item], 6);
      if (item === "bronze_token") this.say("Grandfather’s token. This is the first seal.", 4);
      if (item === "seal_map") this.remember("SB-CHEST-MAP");
      if (item === "folded_slip") this.remember("SB-CHEST-SLIP");
      this.entryDelay = 3;
    }
    void this.saveProgress();
  }
  private say(text: string, seconds: number): void {
    this.dialogue = this.dialogue.then(() => this.game.subtitles.say("Sora", text, seconds));
  }
  private remember(id: string): void {
    const g = this.game;
    const written = new Set([
      ...g.flags.get("sketchbook.written", "").split(",").filter(Boolean),
      ...(g.sketchbook?.written ?? []),
      id,
    ]);
    g.flags.set("sketchbook.written", [...written].join(","));
    this.entries.push(id);
  }
}
