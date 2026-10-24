import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { Game } from "../../../core/Game";
import type { SaveData } from "../../../systems/saves/SaveData";
import { encodeSaveCode } from "../../../systems/saves/saveCode";
import { ResolutionProgress } from "./ResolutionProgress";
import { ResolutionView } from "./ResolutionView";
import { RelicCraft } from "../act3/RelicCraft";

/** R01–R05. Save each decision before presenting the next reveal. */
export class DawnResolution {
  readonly progress: ResolutionProgress;
  readonly view = new ResolutionView();
  private running = false;
  private readonly vuthy;
  private walk = 0;
  constructor(
    private readonly game: Game,
    private readonly capture: () => SaveData,
    private readonly dawn: () => void,
  ) {
    this.progress = new ResolutionProgress(game.flags);
    const craft = new RelicCraft(game.scene);
    this.vuthy = craft.root("vuthy_dawn", [0.8, 0, 5]);
    const shirt = craft.mat("vuthy_dawn_shirt", "#b7aa8a"),
      skin = craft.mat("vuthy_dawn_skin", "#80553c"),
      trousers = craft.mat("vuthy_dawn_trousers", "#373c37");
    craft.sphere(this.vuthy, "vuthy_head", [0.21, 0.27, 0.22], [0, 1.58, 0], skin);
    craft.box(this.vuthy, "vuthy_shirt", [0.42, 0.6, 0.24], [0, 1.13, 0], shirt);
    for (const x of [-0.12, 0.12])
      craft.box(this.vuthy, "vuthy_leg", [0.15, 0.8, 0.18], [x, 0.43, 0], trousers);
    for (const mesh of this.vuthy.getChildMeshes()) mesh.isPickable = false;
    this.vuthy.setEnabled(false);
  }
  get active(): boolean {
    return this.running;
  }
  update(dt: number): void {
    if (this.running && this.vuthy.isEnabled()) {
      this.walk = Math.min(1, this.walk + dt / 8);
      this.vuthy.position.z = 5 - this.walk * 4.5;
    }
  }
  async begin(): Promise<void> {
    if (this.running || !this.progress.begin()) return;
    this.running = true;
    const g = this.game,
      p = this.progress;
    g.cutscene = true;
    g.threatActive = false;
    g.gated.holdStill = true;
    g.stopInspecting();
    g.satchel.close();
    g.sketchbook?.close();
    g.hints.hide();
    document.exitPointerLock();
    await g.fade.to(1, 1.5);
    this.dawn();
    g.player.teleport(new Vector3(0, 0, -1.6), 0);
    g.player.pitch = 0;
    await g.fade.to(0, 2);
    while (true) {
      const stage = p.stage;
      g.bus.emit("sequence:start", {
        id:
          stage === "dawn"
            ? "R01"
            : stage === "choice"
              ? "R02"
              : stage === "slip"
                ? "R03"
                : stage === "map"
                  ? "R04"
                  : "R05",
      });
      if (stage === "dawn") {
        await this.view.show(
          "5:30 AM",
          [
            "The rain has stopped. Birdsong carries across the wet fields. Sok lies still beneath the white cloth.",
          ],
          ["Wait for Vuthy"],
        );
      } else if (stage === "choice") {
        this.vuthy.setEnabled(true);
        if (!g.flags.has("ep1.journal.shared")) {
          const choice = await this.view.show(
            "Vuthy",
            [
              "Sora? You look… What happened here?",
              "Did my father leave anything? Papers, letters? Anything for me?",
            ],
            ["Show him the journal", "Keep the journal"],
          );
          p.choose(choice === 0);
          await this.persist();
          g.bus.emit("choice:made", {
            id: "ep1.journal.shared",
            option: choice === 0 ? "share" : "keep",
          });
        }
        await this.view.show(
          "Vuthy",
          g.flags.get("ep1.journal.shared", false)
            ? [
                "Sora: He left this. You should read it.",
                "…He believed all of it. Every word.",
                "I need to think. I’ll go back to Grandmother.",
                "He hands the journal back.",
              ]
            : [
                "Sora: Old papers. Manuscripts. Nothing for you.",
                "…Of course. Old papers. I’ll go back to Grandmother.",
              ],
          ["Let him return to Grandmother"],
        );
        this.vuthy.setEnabled(false);
      } else if (stage === "slip") {
        this.vuthy.setEnabled(false);
        g.player.teleport(new Vector3(2.7, 0, -1.4), Math.PI);
        g.player.pitch = 0.25;
        void g.subtitles.say("Sora", "…Me.", 3);
        await this.view.slip();
      } else if (stage === "map") {
        g.sketchbook?.restore(["SB-08"]);
        await this.view.map();
      } else if (stage === "title") {
        this.view.hide();
        await g.fade.to(1, 2);
        await this.view.show("Four nights remain.", [], ["Open the sketchbook"]);
      } else if (stage === "summary") {
        await this.view.summary(p);
      } else {
        await this.credits();
        return;
      }
      p.advance();
      await this.persist();
    }
  }
  private async persist(): Promise<void> {
    while (true) {
      try {
        const save = this.capture();
        await this.game.saves.save("autosave", save);
        if (this.game.flags.get("ep1.complete", false))
          await this.game.saves.save("episode1", save);
        return;
      } catch {
        await this.view.show(
          "The page could not be saved",
          ["Your progress is still here. Free some browser storage, then retry."],
          ["Retry save"],
        );
      }
    }
  }
  private async credits(): Promise<void> {
    const g = this.game;
    await g.fade.to(1, 0);
    while (true) {
      const action = await this.view.show(
        "Boon Sop: The Unbroken Debt",
        [
          "Episode 1 · The House of Mourning",
          "Created by Rithy Bondeth",
          "Built with Babylon.js · Havok · TypeScript · Vite",
          "Fonts: Ubuntu · Preah Vihear · Patrick Hand · Freehand. Original fonts retain their licences.",
          "Library assets: Poly Haven (CC0). Character base: MakeHuman Community (CC0). Sound library: Kenney (CC0).",
          "Story, art and audio © 2026 Rithy Bondeth. Third-party assets retain their own licences.",
          "Episode 1 complete. Your journal choice, lore and respect are saved for Episode 2: The Whispering Pagoda.",
        ],
        ["Episode summary", "Export completion save"],
      );
      if (action === 0) await this.view.summary(this.progress);
      else {
        const code = await encodeSaveCode(this.capture());
        const blob = new Blob([code], { type: "text/plain" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "boon-sop-episode-1.save.txt";
        a.click();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
      }
    }
  }
}
