import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Ray } from "@babylonjs/core/Culling/ray";
import type { Game } from "../../../core/Game";
import type { SaveData } from "../../../systems/saves/SaveData";
import type { Vigil } from "../act1/Vigil";
import { wetStep, seededRandom } from "../../../audio/synth";
import { jarLid } from "../audio/actThreeSounds";
import { StalkerVoice } from "../audio/StalkerVoice";
import { CP5_FEET, CP5_YAW, FRAGMENT_IDS, JARS, inHunt } from "../data/hunt";
import { HuntProgress } from "./HuntProgress";
import { RoamerBrain } from "./RoamerBrain";
import type { HuntModels } from "./HuntModels";
import "../../../ui/html/walker.css";

const after = (seconds: number) => new Promise<void>((done) => setTimeout(done, seconds * 1000));

/** A3-03–05: sound / light hunt, durable loot, and a safe three-piece assembly. */
export class UnderHouseHunt {
  readonly progress: HuntProgress;
  readonly brain = new RoamerBrain();
  restarts = 0;
  private checkpoint: SaveData | null = null;
  private recovering = false;
  private intro = 0;
  private stepIn = 0;
  private assembly = -1;
  private actionState = "";
  private readonly entries: string[] = [];
  private readonly steps: StaticSound[] = [];
  private lidSound: StaticSound | null = null;
  private readonly voice = new StalkerVoice(0.55);
  private lastState = "";
  private readonly caught = document.createElement("div");

  constructor(
    private readonly game: Game,
    readonly models: HuntModels,
    private readonly vigil: Vigil,
    private readonly captureProgress: () => SaveData,
    private readonly saveProgress: () => Promise<SaveData>,
  ) {
    this.progress = new HuntProgress(game.flags, game.inventory);
    if (game.resumedSave?.checkpoint === "CP5") this.checkpoint = structuredClone(game.resumedSave);
    models.createPreview(game.camera);
    this.restoreModels();
    for (const jar of models.jars) {
      game.interaction.add(`interact_jar_${jar.id}`, jar.root, { outline: false });
      game.interaction.add(`interact_jar_contents_${jar.id}`, jar.contents, { outline: false });
    }
    game.bus.on("interact:use", ({ id }) => this.use(id));
    game.bus.on("interact:focus", ({ id }) => {
      if (!this.progress.available || !id.startsWith("interact_jar_")) return;
      const jar = models.jars.find((j) => id.endsWith(j.id));
      if (!jar) return;
      const taken = game.flags.get(`ep1.jar.${jar.id}.taken`, false);
      game.hints.show(
        taken ? "hint.jarEmpty" : jar.opening > 0.9 ? "hint.jarTake" : "hint.jarOpen",
        3,
      );
    });
    game.bus.on("noise:made", ({ source, position, loudness }) => {
      if (this.recovering || this.intro > 0 || !["player", "jar"].includes(source)) return;
      this.brain.hear(new Vector3(position.x, position.y, position.z), loudness, source === "jar");
    });
    this.caught.className = "walker-caught";
    this.caught.hidden = true;
    const text = document.createElement("p");
    text.textContent = "The page tears.\nSomething moves beneath the house again.";
    this.caught.append(text);
    document.body.append(this.caught);
  }

  get restarting(): boolean {
    return this.recovering;
  }

  async makeSounds(): Promise<void> {
    const audio = this.game.audio;
    if (!audio) return;
    const rate = audio.context.sampleRate;
    for (let i = 0; i < 3; i++) {
      const buffer =
        this.game.footsteps?.buffers.get("mud")?.[i] ??
        audio.buffer(wetStep(rate, seededRandom(1200 + i)), rate);
      const sound = await audio.spatialSound(
        `roamer_drag_${i}`,
        buffer,
        "threat",
        this.brain.position,
        { minDistance: 2.5, volume: 0.6 },
      );
      sound.playbackRate = 0.58 + i * 0.04;
      this.steps.push(sound);
    }
    this.lidSound = await audio.spatialSound(
      "jar_lid_scrape",
      audio.buffer(jarLid(rate, seededRandom(1205)), rate),
      "sfx",
      CP5_FEET,
      { minDistance: 2, volume: 0.45 },
    );
    await this.voice.load(audio, "roamer", 1210);
  }

  update(dt: number): void {
    this.models.updateJars(dt);
    if (this.game.flags.get("ep1.ritual.tokenPlaced", false)) {
      this.models.roamer.setEnabled(false);
      return;
    }
    if (!this.progress.available || this.recovering) return;
    const g = this.game,
      inside = inHunt(g.player.feet);
    if (inside && !g.cutscene && !this.progress.started) {
      g.flags.set("ep1.hunt.started", true);
      g.flags.set("ep1.checkpoint", "CP5");
      g.flags.set("ep1.clock", "02:05");
      this.commit();
      g.bus.emit("sequence:start", { id: "A3-03" });
    }
    if (this.progress.started && this.brain.state === "idle" && inside && !g.cutscene) {
      g.stopInspecting();
      g.satchel.close();
      g.sketchbook?.close();
      this.brain.start();
      this.intro = 2.5;
      this.stepIn = 0;
      g.hints.show("hint.underHouse", 12);
      void g.subtitles.say(
        "Sora",
        "Something is dragging through the mud. Keep the lamp out. Move quietly.",
        5,
      );
    }
    // The ground floor is the danger zone. Upstairs and the courtyard remain safe to read / assemble.
    if (this.progress.started) g.threatActive = inside;
    if (inside) {
      g.satchel.close();
      g.sketchbook?.close();
    }
    if (this.brain.active && !g.cutscene) {
      this.intro = Math.max(0, this.intro - dt);
      if (this.intro <= 0)
        this.brain.update(dt, g.player.feet, this.vigil.lamp.state === "open", this.canSeeSora());
      this.models.pose(
        this.brain.position,
        this.brain.direction,
        this.brain.elapsed,
        Math.min(1, Math.max(0, 1 - this.intro)),
      );
      this.stepIn -= dt;
      if (this.stepIn <= 0) {
        const step =
          this.steps[Math.floor(this.brain.elapsed * 1.2) % Math.max(1, this.steps.length)];
        if (step) {
          step.spatial.position = this.brain.position.add(new Vector3(0, 0.1, 0));
          step.play();
        }
        this.voice.step(this.brain.position);
        this.stepIn = this.brain.state === "chasing" ? 0.55 : 0.95;
      }
      const state = this.brain.state;
      // Wet breath on its patrol, ragged when it hunts; it stops to scent where it lost her.
      this.voice.breathe(
        this.intro < 1 ? this.brain.position : null,
        state === "chasing" ? 1 : state === "investigating" ? 0.4 : 0,
      );
      if (state === "investigating" && this.lastState !== "investigating")
        this.voice.sniffAt(this.brain.position);
      this.lastState = state;
      if (this.brain.state === "caught") {
        void this.restart();
        return;
      }
    } else if (this.lastState) {
      this.voice.breathe(null);
      this.lastState = "";
    }
    if (
      !inside &&
      !g.cutscene &&
      !g.sketchbook?.isBusy &&
      !g.sketchbook?.isOpen &&
      !g.satchel.isOpen &&
      this.entries.length
    ) {
      const entries = this.entries.splice(0);
      g.sketchbook?.restore(entries.slice(0, -1));
      g.sketchbook?.write(entries.at(-1)!);
    }
    if (this.assembly >= 0) {
      this.assembly = Math.min(1, this.assembly + dt / 1.1);
      if (this.assembly >= 1) this.finishAssembly();
    }
    const pieces = FRAGMENT_IDS.map((id) => g.inventory.has(id));
    const carryingKey = g.inventory.has("brass_key");
    this.models.showPreview(
      (g.satchel.isOpen || this.assembly >= 0) && (pieces.some(Boolean) || carryingKey),
      pieces,
      this.progress.assembled,
      Math.max(0, this.assembly),
    );
    const state = `${this.progress.pieces}:${this.progress.assembled}:${inside}:${this.assembly >= 0}:${carryingKey}`;
    if (state !== this.actionState) {
      this.actionState = state;
      g.satchel.setAction(
        !pieces.some(Boolean) && !carryingKey
          ? null
          : {
              label: this.progress.assembled
                ? "Key assembled · return to Sok’s room"
                : inside
                  ? "Find a safe place to fit the pieces"
                  : this.progress.pieces < 3
                    ? `Key pieces: ${this.progress.pieces} / 3`
                    : "E · Fit the three key pieces",
              enabled:
                !inside &&
                !this.progress.assembled &&
                this.progress.pieces === 3 &&
                this.assembly < 0,
              perform: () => this.beginAssembly(),
            },
      );
    }
  }

  /** The floor, posts, jars and stored clutter occlude sight; the held lamp does not. */
  canSeeSora(): boolean {
    if (!inHunt(this.game.player.feet)) return false;
    const start = this.brain.position.add(new Vector3(0, 1.4, 0));
    const end = this.game.camera.globalPosition;
    const to = end.subtract(start),
      length = to.length();
    if (length < 0.01) return true;
    const own = new Set([...this.models.roamer.getChildMeshes(), ...this.vigil.heldMeshes]);
    const hit = this.game.scene.pickWithRay(
      new Ray(start, to.scale(1 / length), length),
      (m) =>
        m.isEnabled() && m.isVisible && m.visibility > 0 && m.renderingGroupId === 0 && !own.has(m),
    );
    return !hit?.hit || hit.distance >= length - 0.12;
  }

  private use(id: string): void {
    const g = this.game;
    if (
      !this.progress.started ||
      this.recovering ||
      g.cutscene ||
      g.satchel.isOpen ||
      g.sketchbook?.isOpen
    )
      return;
    const jar = this.models.jars.find(
      (j) => id === `interact_jar_${j.id}` || id === `interact_jar_contents_${j.id}`,
    );
    if (!jar || !inHunt(g.player.feet)) return;
    if (this.progress.open(jar.id)) {
      this.models.jarState(jar.id, true, false);
      g.bus.emit("noise:made", { source: "jar", loudness: 0.6, position: jar.root.position });
      if (this.lidSound) {
        this.lidSound.spatial.position = jar.root.position.clone();
        this.lidSound.play();
      }
      g.hints.show("hint.jarTake", 4);
    } else {
      if (jar.opening < 0.9 || !this.progress.take(jar.id)) return;
      this.models.jarState(jar.id, true, true);
      const spec = JARS.find((j) => j.id === jar.id)!;
      if (spec.contents === "key") {
        g.hints.show(this.progress.pieces === 3 ? "note.fragmentsReady" : "note.fragmentFound", 7);
        if (this.progress.pieces === 3) this.remember("SB-A3-04");
      } else if (spec.contents === "lore") {
        this.remember("L2");
        g.hints.show("note.jarLore", 5);
      } else g.hints.show("note.jarOil", 4);
    }
    this.commit();
  }

  private beginAssembly(): void {
    const g = this.game;
    if (
      this.assembly >= 0 ||
      inHunt(g.player.feet) ||
      g.cutscene ||
      !g.satchel.isOpen ||
      this.progress.pieces !== 3 ||
      this.progress.assembled
    )
      return;
    g.stopInspecting();
    g.gated.holdStill = true;
    g.gated.holdLook = true;
    g.cutscene = true;
    this.assembly = 0;
  }

  private finishAssembly(): void {
    const g = this.game;
    // Hide intermediate inventory events while the single recipe is committed.
    g.satchel.close();
    if (this.progress.assemble()) {
      this.remember("SB-A3-05");
      this.commit();
      g.hints.show("note.keyAssembled", 8);
      void g.subtitles.say("Sora", "It fits. The chest behind Sok’s floorboards.", 4);
      g.bus.emit("sequence:end", { id: "A3-04" });
    }
    this.assembly = -1;
    g.cutscene = false;
    g.gated.holdStill = false;
    g.gated.holdLook = false;
    g.toggleSatchel();
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
  /** Later discoveries must survive another visit to the roamer at CP5. */
  refreshCheckpoint(): void {
    if (this.progress.started) this.checkpoint = structuredClone(this.captureProgress());
  }
  private commit(): void {
    this.refreshCheckpoint();
    void this.saveProgress();
  }
  private restoreModels(): void {
    for (const jar of this.models.jars)
      this.models.jarState(
        jar.id,
        this.game.flags.get(`ep1.jar.${jar.id}.open`, false),
        this.game.flags.get(`ep1.jar.${jar.id}.taken`, false),
        true,
      );
    this.models.updateJars(0);
  }

  private async restart(): Promise<void> {
    if (this.recovering || !this.checkpoint) return;
    this.recovering = true;
    const g = this.game,
      saved = structuredClone(this.checkpoint);
    g.bus.emit("player:caught", { by: "under_house_roamer" });
    g.cutscene = true;
    g.threatActive = true;
    g.gated.holdStill = true;
    g.gated.holdLook = true;
    g.stopInspecting();
    g.satchel.close();
    g.hints.hide();
    const forward = g.camera.getForwardRay().direction;
    this.models.pose(
      g.camera.globalPosition.add(forward.scale(0.65)).subtract(new Vector3(0, 1.55, 0)),
      forward.negate(),
      0,
      1,
    );
    await after(0.65);
    this.caught.hidden = false;
    await after(0.65);
    await g.fade.to(1, 0.4);
    for (const step of this.steps) step.stop();
    this.voice.stop();
    this.lastState = "";
    g.flags.load(saved.flags);
    g.inventory.load(saved.inventory);
    this.vigil.restoreCheckpoint(saved);
    g.sketchbook?.restore(
      String(saved.flags["sketchbook.written"] ?? "")
        .split(",")
        .filter(Boolean),
    );
    this.entries.length = 0;
    this.restoreModels();
    this.brain.reset();
    this.models.roamer.setEnabled(false);
    g.player.teleport(CP5_FEET, CP5_YAW);
    g.player.pitch = 0;
    this.caught.hidden = true;
    await g.fade.to(0, 0.65);
    g.cutscene = false;
    g.threatActive = false;
    g.gated.holdStill = false;
    g.gated.holdLook = false;
    this.recovering = false;
    this.restarts++;
    g.hints.show("note.cp5Restart", 8);
  }
}
