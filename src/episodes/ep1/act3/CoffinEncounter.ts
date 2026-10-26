import type { Game } from "../../../core/Game";
import type { CorpseModels } from "./CorpseModels";
import { CoffinProgress } from "./CoffinProgress";
import { boardCreak, seededRandom } from "../../../audio/synth";
import { drawerOpen } from "../audio/prologueSounds";
import { coffinKnock } from "../audio/actThreeSounds";
import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";

export class CoffinEncounter {
  readonly progress: CoffinProgress;
  private sounds = new Map<string, StaticSound>();
  constructor(
    private game: Game,
    private body: CorpseModels,
    private save: () => Promise<unknown>,
  ) {
    this.progress = new CoffinProgress(game.flags);
    game.interaction.add("interact_coffin_close", body.closeGrip, { outline: false });
    this.apply();
  }
  get showingBody(): boolean {
    return ["open", "closing"].includes(this.progress.phase);
  }
  async makeSounds(): Promise<void> {
    const audio = this.game.audio;
    if (!audio) return;
    const rate = audio.context.sampleRate;
    const bang = coffinKnock(rate, seededRandom(1691));
    for (const [name, data] of [
      ["rattle", boardCreak(rate, seededRandom(1690))],
      ["bang", bang],
      ["scrape", drawerOpen(rate, seededRandom(1692))],
    ] as const)
      this.sounds.set(
        name,
        await audio.spatialSound(
          `coffin_${name}`,
          audio.buffer(data, rate),
          "sfx",
          new Vector3(0, 1, -5.9),
          { minDistance: 2, volume: 0.65 },
        ),
      );
  }
  update(dt: number, available: boolean): void {
    const g = this.game,
      p = this.progress;
    const paused =
      g.cutscene ||
      g.hiding ||
      g.satchel.isOpen ||
      !!g.sketchbook?.isOpen ||
      !!g.sketchbook?.isBusy ||
      g.threatActive;
    const near =
      Math.hypot(g.player.feet.x, g.player.feet.z + 5.9) < 1.85 && g.player.feet.y > 0.35;
    const focused = g.interaction.focus === "interact_coffin_close";
    const before = p.phase;
    const revealedBefore = g.flags.get("ep1.coffin.revealed", false);
    const event = p.update(
      dt,
      available,
      near,
      this.body.observed(g.camera),
      // Once grasped, the moving lid can occlude the handle without releasing Sora's grip.
      (focused || p.phase === "closing") && g.input.isHeld("KeyE"),
      paused,
    );
    if (!revealedBefore && g.flags.get("ep1.coffin.revealed", false)) void this.save();
    if (event === "rattle") {
      this.sounds.get("rattle")?.play();
      void this.save();
    }
    if (event === "bang") {
      this.sounds.get("bang")?.play();
      void g.subtitles.say("Sora", "I closed this… didn’t I?", 4);
    }
    if (p.phase === "closing" && before !== "closing") this.sounds.get("scrape")?.play();
    this.apply();
    if (
      p.phase === "closing" &&
      p.openness < 0.18 &&
      !g.flags.get("ep1.coffin.headTurned", false) &&
      this.body.headCovered(g.camera)
    ) {
      g.flags.set("ep1.coffin.headTurned", true);
      g.flags.set("ep1.corpse.pose", 1);
      this.body.pose(1);
    }
    if (event === "closed") {
      this.sounds.get("bang")?.play();
      g.hints.show("note.coffinClosed", 5);
      void this.save();
    } else if (!paused && this.showingBody)
      g.hints.show(p.seenSeconds < 2 ? "hint.coffinLook" : "hint.coffinClose", 1);
  }
  private apply(): void {
    const p = this.progress;
    const t = p.openness;
    this.body.setLid(t * t * (3 - 2 * t));
    this.body.closeGrip.setEnabled(this.showingBody && p.seenSeconds >= 2);
    // A closed lid must never have a raised arm or flower passing through it.
    if (!this.showingBody)
      this.body.pose(this.game.flags.get("ep1.coffin.headTurned", false) ? 1 : 0);
  }
}
