import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { Game } from "../../../core/Game";
import type { SaveData } from "../../../systems/saves/SaveData";
import type { Vigil } from "../act1/Vigil";
import type { SokInvestigation } from "./SokInvestigation";
import { WalkerBrain } from "./WalkerBrain";
import type { WalkerModels } from "./WalkerModels";
import { WardrobeHiding } from "./WardrobeHiding";
import { CP3_FEET, CP3_YAW } from "../data/walker";
import { boardCreak, seededRandom, wetStep } from "../../../audio/synth";
import { breathOut } from "../audio/nightSounds";
import { heartbeat } from "../audio/houseSounds";
import { StalkerVoice } from "../audio/StalkerVoice";

const copySave = (save: SaveData): SaveData => structuredClone(save);
const after = (seconds: number) =>
  new Promise<void>((resolve) => setTimeout(resolve, seconds * 1000));

/** A2-06: durable CP3, a blind hallway traversal, hiding and a local checkpoint restart. */
export class HallwayWalker {
  readonly brain = new WalkerBrain();
  readonly hiding: WardrobeHiding;
  private checkpoint: SaveData | null = null;
  private preparing = false;
  private recovering = false;
  private stepIn = 0;
  private hissIn = 0;
  private hinted = false;
  private readonly steps: StaticSound[] = [];
  private breath: StaticSound | null = null;
  private creak: StaticSound | null = null;
  private heartbeat: StaticSound | null = null;
  private heartbeatOn = false;
  private readonly voice = new StalkerVoice(0.5);
  private pendingEntry = false;
  private readonly caught = document.createElement("div");
  restarts = 0;

  constructor(
    private readonly game: Game,
    readonly models: WalkerModels,
    private readonly vigil: Vigil,
    private readonly investigation: SokInvestigation,
    private readonly saveProgress: () => Promise<SaveData>,
  ) {
    this.hiding = new WardrobeHiding(game, models, vigil.lamp);
    if (game.resumedSave?.checkpoint === "CP3") this.checkpoint = copySave(game.resumedSave);
    const previousAllow = game.interaction.allow;
    game.interaction.allow = (id) =>
      previousAllow(id) &&
      (!(this.brain.active || this.recovering) || id.startsWith("interact_wardrobe_"));
    game.bus.on("noise:made", ({ position, loudness, source }) => {
      if (source !== "player" || this.recovering) return;
      this.brain.hear(
        new Vector3(position.x, position.y, position.z),
        loudness,
        this.hiding.concealed,
      );
    });
    this.caught.className = "walker-caught";
    this.caught.hidden = true;
    const page = document.createElement("p");
    page.textContent = "The page tears.\nThe footsteps begin again.";
    this.caught.append(page);
    document.body.append(this.caught);
  }

  get restarting(): boolean {
    return this.recovering;
  }
  get armed(): boolean {
    return !!this.checkpoint && this.game.flags.get("ep1.walker.armed", false);
  }

  async makeSounds(): Promise<void> {
    const audio = this.game.audio;
    if (!audio) return;
    const rate = audio.context.sampleRate;
    for (let k = 0; k < 3; k++) {
      const recorded = this.game.footsteps?.buffers.get("teak")?.[k];
      const buffer = recorded ?? audio.buffer(wetStep(rate, seededRandom(940 + k)), rate);
      const sound = await audio.spatialSound(
        `hallway_walker_step_${k}`,
        buffer,
        "threat",
        this.brain.position,
        { minDistance: 2, volume: 0.65 },
      );
      sound.playbackRate = 0.66 + k * 0.035;
      this.steps.push(sound);
    }
    this.creak = await audio.spatialSound(
      "hallway_walker_creak",
      audio.buffer(boardCreak(rate, seededRandom(947)), rate),
      "threat",
      this.brain.position,
      { minDistance: 3, volume: 0.6 },
    );
    this.breath = await audio.sound(
      "hallway_caught_breath",
      audio.buffer(breathOut(rate, seededRandom(948)), rate),
      "threat",
      0.7,
    );
    this.heartbeat = await audio.sound(
      "wardrobe_heartbeat",
      audio.buffer(heartbeat(rate, seededRandom(949)), rate),
      "sfx",
      0.08,
    );
    this.heartbeat.loop = true;
    await this.voice.load(audio, "hallway_walker", 950);
  }

  update(dt: number): void {
    this.hiding.update(dt);
    if (this.recovering) return;
    const game = this.game,
      p = game.player.feet;
    if (this.pendingEntry && !game.hiding && !game.cutscene && !game.sketchbook?.isBusy) {
      this.pendingEntry = false;
      game.sketchbook?.write("SB-A2-06");
    }
    const completed = game.flags.get("ep1.walker.complete", false);
    if (
      !completed &&
      !this.armed &&
      !this.preparing &&
      game.flags.get("ep1.gramophone.heard", false) &&
      !this.investigation.playingMessage &&
      !game.cutscene &&
      !game.sketchbook?.isBusy &&
      !game.sketchbook?.isOpen &&
      p.y > 2.2
    )
      void this.prepare();
    if (
      this.armed &&
      !completed &&
      this.brain.state === "idle" &&
      !this.investigation.playingMessage &&
      !game.cutscene &&
      !game.sketchbook?.isBusy &&
      !game.sketchbook?.isOpen &&
      p.y > 2.2 &&
      p.z < -11.4 &&
      p.z > -18.1 &&
      p.x > -3.55 &&
      p.x < 3
    )
      this.start();
    if (!this.brain.active) return;
    this.hissIn -= dt;
    if (this.hissIn <= 0 && this.hiding.wardrobe && this.vigil.lamp.state === "open") {
      // This walker has no sight. An exposed wick is only a close, audible cue.
      this.hissIn = 1;
      this.brain.hear(this.hiding.wardrobe.front, 0.12, false);
    }
    this.brain.update(dt, p, this.hiding.concealed);
    this.models.pose(this.brain.position, this.brain.direction, this.brain.elapsed);
    if (this.brain.state === "caught") {
      void this.restart();
      return;
    }
    if (this.brain.state === "complete") {
      this.complete();
      return;
    }
    this.stepIn -= dt;
    if (this.stepIn <= 0 && !this.brain.waiting) {
      const index = Math.floor(this.brain.elapsed / 0.85) % Math.max(1, this.steps.length);
      const step = this.steps[index];
      if (step) {
        step.spatial.position = this.brain.position.add(new Vector3(0, 0.05, 0));
        step.play();
      }
      this.voice.step(this.brain.position);
      if (index === 0 && this.creak) {
        this.creak.spatial.position = this.brain.position.clone();
        this.creak.play();
      }
      this.stepIn = 0.85;
    }
    // Its breath goes with it, heavier while it stands listening at a door.
    this.voice.breathe(this.brain.position, this.brain.waiting ? 0.2 : 0);
    if (!this.hinted && this.brain.elapsed > 4 && !game.hiding) {
      this.hinted = true;
      game.hints.show("hint.walkerHide", 10);
    }
    if (game.hiding && !this.heartbeatOn) {
      this.heartbeat?.play();
      this.heartbeatOn = true;
    }
    if (!game.hiding && this.heartbeatOn) {
      this.heartbeat?.stop();
      this.heartbeatOn = false;
    }
  }

  private async prepare(): Promise<void> {
    this.preparing = true;
    try {
      this.game.flags.set("ep1.walker.armed", true);
      this.game.flags.set("ep1.checkpoint", "CP3");
      this.game.flags.set("ep1.clock", "01:20");
      this.checkpoint = copySave(await this.saveProgress());
    } finally {
      this.preparing = false;
    }
  }

  private start(): void {
    this.game.stopInspecting();
    this.game.satchel.close();
    this.game.threatActive = true;
    this.brain.start();
    this.models.walker.setEnabled(true);
    this.hinted = false;
    this.stepIn = 0;
    this.game.bus.emit("sequence:start", { id: "A2-06" });
    this.game.hints.show("note.walkerApproach", 4);
  }

  private complete(): void {
    const game = this.game;
    this.models.walker.setEnabled(false);
    this.voice.stop();
    this.heartbeat?.stop();
    this.heartbeatOn = false;
    game.threatActive = false;
    game.flags.set("ep1.walker.complete", true);
    game.flags.set("ep1.clock", "01:25");
    const written = new Set([
      ...game.flags.get("sketchbook.written", "").split(",").filter(Boolean),
      ...(game.sketchbook?.written ?? []),
      "SB-A2-06",
    ]);
    game.flags.set("sketchbook.written", [...written].join(","));
    // Save before an optional notebook animation; never open the book inside a wardrobe.
    if (!game.hiding) game.sketchbook?.write("SB-A2-06");
    else this.pendingEntry = true;
    game.hints.show("note.walkerPassed", 8);
    game.bus.emit("sequence:end", { id: "A2-06" });
    void this.saveProgress();
  }

  private async restart(): Promise<void> {
    if (this.recovering || !this.checkpoint) return;
    this.recovering = true;
    const game = this.game;
    const saved = copySave(this.checkpoint);
    game.bus.emit("player:caught", { by: "hallway_walker" });
    game.cutscene = true;
    game.gated.holdStill = true;
    game.gated.holdLook = true;
    game.stopInspecting();
    game.satchel.close();
    game.hints.hide();
    this.hiding.exit(false);
    this.heartbeat?.stop();
    this.heartbeatOn = false;
    this.voice.breathe(null);
    this.breath?.play();
    const eye = game.camera.globalPosition;
    const forward = game.camera.getForwardRay().direction;
    this.models.walker.position.copyFrom(
      eye.add(forward.scale(0.8)).subtract(new Vector3(0, 2.05, 0)),
    );
    this.models.walker.rotation.y = Math.atan2(-forward.x, -forward.z);
    await after(0.8);
    this.caught.hidden = false;
    await after(0.7);
    await game.fade.to(1, 0.45);
    for (const sound of [...this.steps, this.creak]) sound?.stop();
    this.voice.stop();
    game.flags.load(saved.flags);
    game.inventory.load(saved.inventory);
    this.vigil.restoreCheckpoint(saved);
    game.sketchbook?.restore(
      String(saved.flags["sketchbook.written"] ?? "")
        .split(",")
        .filter(Boolean),
    );
    game.player.teleport(CP3_FEET, CP3_YAW);
    game.player.pitch = 0;
    this.brain.reset();
    this.models.walker.setEnabled(false);
    this.caught.hidden = true;
    await game.fade.to(0, 0.65);
    game.threatActive = false;
    game.cutscene = false;
    game.gated.holdStill = false;
    game.gated.holdLook = false;
    this.restarts++;
    this.recovering = false;
    game.bus.emit("sequence:end", { id: "A2-06" });
    game.hints.show("note.cp3Restart", 7);
  }
}
