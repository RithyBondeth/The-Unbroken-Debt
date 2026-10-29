import { setControlText } from "../../../ui/html/controlText";
import type { Game } from "../../../core/Game";
import type { Vigil } from "./Vigil";
import type { SaveData } from "../../../systems/saves/SaveData";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Ray } from "@babylonjs/core/Culling/ray";
import { ShadowFigure } from "../entities/ShadowFigure";
import { StalkerVoice } from "../audio/StalkerVoice";
import { EarlyStealthBrain } from "./EarlyStealthBrain";
import {
  passageReady,
  passageRequired,
  PASSAGE_SECONDS,
  PASSAGE_WARNING_SECONDS,
} from "./VigilPassage";
import { SpiritPresence } from "../entities/SpiritPresence";
import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { seededRandom } from "../../../audio/synth";
import { dreadBed, spiritRattle } from "../audio/presenceSounds";

/** A1-11b: keep the vigil in darkness while a listening figure crosses the gate.
 * The historic class/flags are retained so existing checkpoints still restore.
 */
export class EarlyStealth {
  readonly brain = new EarlyStealthBrain();
  readonly figure: ShadowFigure;
  private running = false;
  private finishing = false;
  private recovering = false;
  private starting = false;
  private time = 0;
  private travel = 0;
  private yaw = Math.PI;
  private walked = 0;
  private readonly presence = new SpiritPresence(1.8, 1.4);
  private tension: StaticSound | null = null;
  private rattle: StaticSound | null = null;
  private nextRattle = 9;
  private lastState = "patrol";
  private readonly voice = new StalkerVoice(0.6);
  private readonly hud = document.createElement("div");
  private lastMessage = "";
  constructor(
    private readonly game: Game,
    private readonly vigil: Vigil,
    private readonly capture: () => SaveData,
  ) {
    this.brain.direction.set(0, 0, -1);
    this.figure = new ShadowFigure(game.scene, "road_watcher", 2.5);
    this.figure.root.setEnabled(false);
    this.hud.className = "road-stealth-status";
    this.hud.hidden = true;
    this.hud.setAttribute("role", "status");
    document.body.append(this.hud);
    const previous = game.interaction.allow;
    game.interaction.allow = (id) => previous(id) && !this.active;
    game.bus.on("noise:made", ({ source, loudness, position }) => {
      if (this.running && game.threatActive && !game.cutscene && source === "player")
        this.brain.hear(new Vector3(position.x, position.y, position.z), loudness);
    });
  }
  get required(): boolean {
    return passageRequired(this.game.flags);
  }
  get active(): boolean {
    return this.starting || this.running || this.finishing || this.recovering;
  }
  async makeSounds(): Promise<void> {
    const audio = this.game.audio;
    await this.voice.load(audio, "vigil_presence", 2230);
    if (!audio) return;
    const rate = audio.context.sampleRate;
    this.tension = await audio.sound(
      "vigil_dread",
      audio.buffer(dreadBed(rate, seededRandom(2240)), rate),
      "threat",
      0,
    );
    this.tension.loop = true;
    this.rattle = await audio.spatialSound(
      "vigil_brass_strain",
      audio.buffer(spiritRattle(rate, seededRandom(2241)), rate),
      "threat",
      this.brain.position,
      { minDistance: 3, maxDistance: 35, volume: 0.34 },
    );
  }
  async begin(): Promise<void> {
    if (!this.required || this.active) return;
    this.starting = true;
    const g = this.game;
    // Preserve the completed offering, matches and incense cycle before danger.
    // A retry restarts this passage beneath the pavilion, never the taxi ride.
    const save = this.capture();
    Object.assign(save.flags, {
      "checkpoint.spawn.cp": save.checkpoint,
      "checkpoint.spawn.x": 0,
      "checkpoint.spawn.y": 0,
      "checkpoint.spawn.z": -2,
      "checkpoint.spawn.yaw": 0,
    });
    try {
      await g.checkpoints.mark(save, "Village · Keep the vigil");
    } catch {
      g.hints.show("note.saveFailed", 8);
    }
    g.flags.set("ep1.early.started", true);
    g.threatActive = true;
    g.notebook.close();
    g.sketchbook?.close();
    g.satchel.close();
    this.starting = false;
    this.running = true;
    this.hud.hidden = false;
    this.figure.root.position.copyFrom(this.brain.position);
    this.figure.root.rotation.y = this.yaw;
    this.figure.setPresence(0);
    this.figure.root.setEnabled(true);
    this.presence.show();
    this.tension?.play();
    this.voice.step(this.brain.position);
    this.message(
      "Footsteps at the gate. F puts out the lamp.\nStay beneath the pavilion. Hold C and let it pass.",
    );
    void g.subtitles.say("Sora", "Those footsteps… Keep the lamp out. Let it pass.", 5);
  }
  update(dt: number): void {
    const g = this.game,
      feet = g.player.feet;
    if (!this.active) {
      const underTent = Math.abs(feet.x) < 3.8 && feet.z < -1 && feet.z > -7 && feet.y < 0.5;
      const handsFree =
        !g.cutscene &&
        !g.inspecting &&
        !g.satchel.isOpen &&
        !g.notebook.isOpen &&
        !g.sketchbook?.isBusy &&
        !g.sketchbook?.isOpen;
      if (passageReady(g.flags, underTent, handsFree)) void this.begin();
      return;
    }
    if (!this.running || this.recovering || this.finishing || g.cutscene) return;
    this.time += dt;
    this.presence.update(dt);
    this.figure.setPresence(this.presence.value);
    const before = this.brain.position.clone();
    if (this.time > PASSAGE_WARNING_SECONDS) {
      // It searches for light and movement. Stillness and an extinguished lamp
      // let it pass without teaching the full chase mechanics at the opening.
      const lit = this.vigil.lamp.state === "open",
        crouched = g.player.stance === "crouch";
      // Reject range and view cone before picking the forest's geometry.
      const visible = this.brain.sees(feet, lit, crouched, true) && this.canSeeSora();
      this.brain.update(dt, feet, lit, crouched, visible);
    }
    const distance = Vector3.Distance(before, this.brain.position);
    const speed = dt > 0 ? distance / dt : 0;
    this.travel += (Math.min(1, speed / 0.85) - this.travel) * (1 - Math.exp(-dt * 8));
    this.figure.root.position.copyFrom(this.brain.position);
    const want = Math.atan2(this.brain.direction.x, this.brain.direction.z);
    const error = Math.atan2(Math.sin(want - this.yaw), Math.cos(want - this.yaw));
    this.yaw += error * (1 - Math.exp(-dt * 2.3));
    this.figure.root.rotation.y = this.yaw;
    this.walked += distance;
    this.figure.animate(this.time, this.travel, Math.max(-1, Math.min(1, error)));
    const urgency = this.brain.state === "chase" ? 1 : this.brain.suspicion;
    this.voice.breathe(this.brain.position, urgency, this.presence.value);
    // No footsteps while it listens or turns in place.
    if (this.walked >= 0.48) {
      this.voice.step(this.brain.position);
      this.walked %= 0.48;
    }
    if (this.lastState !== this.brain.state && this.brain.state === "search")
      this.voice.sniffAt(this.brain.position);
    this.lastState = this.brain.state;
    const proximity = Math.max(0, 1 - Vector3.Distance(feet, this.brain.position) / 24);
    if (this.tension)
      this.tension.volume +=
        ((0.08 + proximity * 0.15 + urgency * 0.12) * this.presence.value - this.tension.volume) *
        (1 - Math.exp(-dt * 1.4));
    this.nextRattle -= dt;
    if (this.nextRattle <= 0) {
      this.nextRattle = 8.7 + Math.sin(this.time) * 2.5;
      if (this.rattle) {
        this.rattle.spatial.position = this.brain.position.add(new Vector3(0, 1.3, 0));
        this.rattle.play();
      }
    }
    if (this.time > PASSAGE_WARNING_SECONDS)
      this.message(
        this.brain.state === "chase"
          ? "It noticed you. Put out the lamp; break its view behind the pavilion.\nCrouch and wait for the footsteps to move away."
          : this.brain.suspicion > 0.12
            ? "It stopped to listen…\nF puts out the lamp. Hold C and stay still."
            : "Keep the vigil in darkness.\nLet its footsteps pass the gate. Hold C; F puts out the lamp.",
      );
    if (this.brain.state === "caught") {
      this.recovering = true;
      this.hud.hidden = true;
      this.voice.stop();
      this.tension?.stop();
      this.rattle?.stop();
      g.bus.emit("player:caught", { by: "road_watcher" });
      void g.retryFromCheckpoint();
      return;
    }
    if (
      this.time >= PASSAGE_SECONDS &&
      this.brain.state !== "chase" &&
      this.brain.suspicion < 0.12
    ) {
      this.presence.hide();
      if (!this.presence.visible) void this.finish();
    }
  }
  canSeeSora(): boolean {
    const g = this.game,
      from = this.brain.position.add(new Vector3(0, 1.7, 0)),
      to = g.camera.globalPosition.subtract(from),
      length = to.length();
    if (length < 0.01) return true;
    const own = new Set([...this.figure.meshes, ...this.vigil.heldMeshes, ...g.hands.meshes]);
    const hit = g.scene.pickWithRay(
      new Ray(from, to.scale(1 / length), length),
      (m) =>
        m.isEnabled() && m.isVisible && m.visibility > 0 && m.renderingGroupId === 0 && !own.has(m),
    );
    return !hit?.hit || hit.distance >= length - 0.12;
  }
  private message(text: string): void {
    if (text === this.lastMessage) return;
    this.lastMessage = text;
    setControlText(this.hud, text);
  }
  private async finish(): Promise<void> {
    if (this.finishing) return;
    this.finishing = true;
    const g = this.game;
    g.threatActive = false;
    this.voice.stop();
    this.tension?.stop();
    this.rattle?.stop();
    this.figure.root.setEnabled(false);
    this.hud.hidden = true;
    g.flags.set("ep1.early.complete", true);
    const save = this.capture();
    Object.assign(save.flags, {
      "checkpoint.spawn.cp": save.checkpoint,
      "checkpoint.spawn.x": 0,
      "checkpoint.spawn.y": 0,
      "checkpoint.spawn.z": -2,
      "checkpoint.spawn.yaw": 0,
    });
    try {
      await g.checkpoints.mark(save, "Village · Passage survived");
      g.hints.show("note.checkpointSaved", 6);
    } catch {
      g.hints.show("note.saveFailed", 8);
    }
    this.running = false;
    this.finishing = false;
    void g.subtitles.say("Sora", "It’s gone. Something is moving upstairs…", 4);
  }
}
