import type { Game } from "../../../core/Game";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { DocumentReader } from "../../../ui/html/DocumentReader";
import { GramophoneGovernor } from "./GramophoneGovernor";
import type { SokRoomModels } from "./SokRoomModels";
import { JOURNAL_A, SOK_RECORDING } from "../data/investigation";
import { GramophoneAudio } from "../audio/GramophoneAudio";

/** A2-03–05: journal discovery → supernatural record → sustained speed correction → key clue. */
export class SokInvestigation {
  readonly governor: GramophoneGovernor;
  readonly reader = new DocumentReader(JOURNAL_A);
  readonly audio = new GramophoneAudio();
  private readonly entries: string[] = [];
  private savingIn = -1;
  private awakening = -1;
  private paragraph = -1;
  private paragraphElapsed = 0;
  private paragraphAt = 0;
  private messagePlaying = false;

  constructor(
    private readonly game: Game,
    readonly models: SokRoomModels,
    private readonly saveProgress: () => Promise<unknown>,
  ) {
    this.governor = new GramophoneGovernor(game.flags);
    game.interaction.remove("interact_gramophone");
    game.interaction.add("interact_gramophone", models.gramophoneMeshes, { outline: false });
    if (!game.flags.get("ep1.journal.plankOpen", false))
      game.interaction.add("interact_sok_wall_plank", models.plank, { outline: false });
    game.interaction.add("interact_sok_journal", models.papers, { outline: false });
    models.update(
      0,
      this.governor.rpm,
      false,
      game.flags.get("ep1.journal.plankOpen", false),
      true,
    );
    game.bus.on("interact:use", ({ id }) => this.use(id));
    game.bus.on("interact:focus", ({ id }) => {
      if (!this.available || game.cutscene) return;
      if (id === "interact_sok_wall_plank") game.hints.show("hint.sokPlank", 4);
      if (id === "interact_sok_journal") game.hints.show("hint.sokJournal", 4);
      if (id === "interact_gramophone")
        game.hints.show(this.started ? "hint.gramophoneInspect" : "note.gramophoneQuiet", 4);
    });
    window.addEventListener("keydown", (event) => {
      if (!["ArrowLeft", "ArrowRight"].includes(event.code) || !this.tuning) return;
      event.preventDefault();
      this.governor.adjust(event.code === "ArrowRight" ? 1 : -1);
      this.savingIn = 0.45;
      game.hints.show(
        this.governor.clarity > 0.85 ? "hint.gramophoneClear" : "hint.gramophoneSpeed",
        5,
      );
    });
  }

  get available(): boolean {
    return this.game.flags.get("ep1.sok.unlocked", false);
  }
  get started(): boolean {
    return this.game.flags.get("ep1.gramophone.started", false);
  }
  get playingMessage(): boolean {
    return this.messagePlaying;
  }
  get tuning(): boolean {
    return (
      this.available &&
      this.started &&
      !this.governor.solved &&
      this.game.inspecting &&
      !this.game.cutscene &&
      !this.game.sketchbook?.isBusy &&
      !this.game.sketchbook?.isOpen &&
      Vector3.Distance(
        this.game.camera.globalPosition,
        this.models.gramophone.position.add(new Vector3(0, 1.05, 0.1)),
      ) < 2.1
    );
  }

  async makeSounds(): Promise<void> {
    await this.audio.load(
      this.game.audio,
      this.models.gramophone.position.add(new Vector3(0, 1.1, 0.1)),
    );
    if (
      this.started &&
      !this.game.flags.get("ep1.gramophone.heard", false) &&
      !this.governor.solved
    )
      this.audio.start();
    if (this.game.flags.get("ep1.journal.found", false) && !this.started) this.awakening = 2.5;
  }

  update(dt: number): void {
    const game = this.game;
    if (game.threatActive) return;
    const heard = game.flags.get("ep1.gramophone.heard", false);
    this.models.update(
      dt,
      this.governor.rpm,
      this.started && (!heard || this.messagePlaying),
      game.flags.get("ep1.journal.plankOpen", false),
    );
    if (this.savingIn >= 0) {
      this.savingIn -= dt;
      if (this.savingIn <= 0) {
        this.savingIn = -1;
        void this.saveProgress();
      }
    }
    if (this.awakening >= 0) {
      this.awakening -= dt;
      if (this.awakening <= 0) {
        this.awakening = -1;
        game.flags.set("ep1.gramophone.started", true);
        game.flags.set("ep1.clock", "01:10");
        this.audio.start();
        game.hints.show("note.gramophoneAwake", 6);
        void this.saveProgress();
      }
    }
    if (this.entries.length && !game.cutscene && !game.sketchbook?.isBusy) {
      const entry = this.entries.shift()!;
      if (!game.sketchbook?.written.has(entry)) game.sketchbook?.write(entry);
    }
    this.audio.tune(this.governor.rpm, this.governor.clarity);
    if (this.governor.update(dt, this.tuning)) {
      game.hints.hide();
      game.flags.set("ep1.clock", "01:15");
      void this.saveProgress();
      this.playMessage();
    }
    if (this.messagePlaying) {
      this.paragraphElapsed += dt;
      const elapsed =
        game.audio?.context.state === "running"
          ? game.audio.context.currentTime - this.paragraphAt
          : this.paragraphElapsed;
      if (elapsed >= (this.audio.durations[this.paragraph] ?? 3) + 0.25) this.nextParagraph();
    }
  }

  private use(id: string): void {
    const game = this.game;
    if (!this.available || game.cutscene || game.threatActive || game.hiding) return;
    if (id === "interact_sok_wall_plank") {
      if (game.flags.get("ep1.journal.plankOpen", false)) return;
      game.flags.set("ep1.journal.plankOpen", true);
      game.interaction.remove("interact_sok_wall_plank");
      game.hints.show("note.journalRevealed", 5);
      void this.saveProgress();
    } else if (id === "interact_sok_journal") {
      if (!game.flags.get("ep1.journal.plankOpen", false)) return;
      game.stopInspecting();
      game.satchel.close();
      if (game.sketchbook?.isOpen) game.sketchbook.toggle();
      game.cutscene = true;
      game.gated.holdStill = true;
      game.gated.holdLook = true;
      game.hints.hide();
      if (document.pointerLockElement) document.exitPointerLock();
      this.reader.show(0, () => {
        game.cutscene = false;
        game.gated.holdStill = false;
        game.gated.holdLook = false;
        if (!game.flags.get("ep1.journal.found", false)) {
          game.flags.set("ep1.journal.found", true);
          game.flags.set("ep1.clock", "01:05");
          game.inventory.add("sok_journal");
          this.remember("SB-04");
        }
        if (!this.started) this.awakening = 2.5;
        void this.saveProgress();
      });
    } else if (id === "interact_gramophone") {
      if (!game.flags.get("ep1.journal.found", false))
        return game.hints.show("note.gramophoneQuiet", 5);
      if (!this.started) return;
      game.inspectObject(this.models.gramophone.position.add(new Vector3(0, 1.05, 0.1)), 0.6);
      if (this.governor.solved) {
        if (!this.messagePlaying) this.playMessage();
      } else {
        this.audio.start();
        game.hints.show("hint.gramophoneSpeed", 12);
      }
    }
  }

  private remember(id: string): void {
    this.entries.push(id);
    const written = new Set([
      ...(this.game.sketchbook?.written ?? []),
      ...this.game.flags.get("sketchbook.written", "").split(",").filter(Boolean),
      id,
    ]);
    this.game.flags.set("sketchbook.written", [...written].join(","));
  }

  private playMessage(): void {
    if (this.messagePlaying) return;
    this.messagePlaying = true;
    this.audio.start();
    this.audio.beginMessage();
    this.paragraph = -1;
    this.nextParagraph();
  }

  private nextParagraph(): void {
    this.paragraph++;
    if (this.paragraph >= SOK_RECORDING.length) {
      this.messagePlaying = false;
      this.audio.endMessage();
      const game = this.game;
      if (!game.flags.get("ep1.gramophone.heard", false)) {
        game.flags.set("ep1.gramophone.heard", true);
        this.remember("SB-05");
        this.remember("SB-A2-05");
        game.stopInspecting();
        game.hints.show("note.deskKeyClue", 9);
        void this.saveProgress();
      }
      return;
    }
    this.paragraphElapsed = 0;
    this.paragraphAt = this.game.audio?.context.currentTime ?? 0;
    this.audio.playParagraph(this.paragraph);
    void this.game.subtitles.say(
      "Sok",
      SOK_RECORDING[this.paragraph],
      this.audio.durations[this.paragraph] ?? 3,
    );
  }
}
