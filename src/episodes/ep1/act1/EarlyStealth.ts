import type { Game } from "../../../core/Game";
import type { Vigil } from "./Vigil";
import type { SaveData } from "../../../systems/saves/SaveData";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { Ray } from "@babylonjs/core/Culling/ray";
import { CreateBox } from "@babylonjs/core/Meshes/Builders/boxBuilder";
import { CreateCylinder } from "@babylonjs/core/Meshes/Builders/cylinderBuilder";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { addStaticBox } from "../../../core/Physics";
import { ShadowFigure } from "../entities/ShadowFigure";
import { StalkerVoice } from "../audio/StalkerVoice";
import { EarlyStealthBrain, ROAD_COVER } from "./EarlyStealthBrain";

/** An early, sight-and-sound encounter; the funeral courtyard is its clear safe boundary. */
export class EarlyStealth {
  readonly brain = new EarlyStealthBrain();
  readonly figure: ShadowFigure;
  private running = false;
  private finishing = false;
  private recovering = false;
  private done: (() => void) | null = null;
  private stepIn = 0;
  private readonly voice = new StalkerVoice(0.6);
  private readonly hud = document.createElement("div");
  private lastMessage = "";
  constructor(
    private readonly game: Game,
    private readonly vigil: Vigil,
    private readonly capture: () => SaveData,
  ) {
    this.figure = new ShadowFigure(game.scene, "road_watcher", 2.05);
    this.figure.root.setEnabled(false);
    this.hud.className = "road-stealth-status";
    this.hud.hidden = true;
    this.hud.setAttribute("role", "status");
    this.hud.style.cssText =
      "position:fixed;bottom:9%;left:50%;transform:translateX(-50%);width:min(620px,86vw);padding:12px 18px;text-align:center;white-space:pre-line;font:16px/1.55 Georgia,serif;color:#f0e6cf;background:#101614dc;border:1px solid #8b8a7155;pointer-events:none;z-index:12";
    document.body.append(this.hud);
    const previous = game.interaction.allow;
    game.interaction.allow = (id) => previous(id) && !this.active;
    game.bus.on("noise:made", ({ source, loudness, position }) => {
      if (this.running && game.threatActive && !game.cutscene && source === "player")
        this.brain.hear(new Vector3(position.x, position.y, position.z), loudness);
    });
    if (game.flags.get("ep1.opening.version", 0) >= 2) this.makeCover();
  }
  get required(): boolean {
    return (
      this.game.flags.get("ep1.early.required", false) &&
      !this.game.flags.get("ep1.early.complete", false)
    );
  }
  get active(): boolean {
    return this.running || this.finishing || this.recovering;
  }
  async begin(): Promise<void> {
    if (!this.required) return;
    await this.voice.load(this.game.audio, "road_watcher", 2230);
    this.running = true;
    this.hud.hidden = false;
    this.figure.root.setEnabled(true);
    this.figure.root.position.copyFrom(this.brain.position);
    this.message(
      "Reach the lit funeral courtyard.\nHold C to crouch behind the carts. F puts out your lamp. Avoid its gaze.",
    );
    void this.game.subtitles.say(
      "Sora",
      "Someone’s on the path. I can get past while it’s looking away.",
      5,
    );
    await new Promise<void>((done) => {
      this.done = done;
    });
  }
  update(dt: number): void {
    if (!this.running || this.recovering || this.finishing || this.game.cutscene) return;
    const g = this.game,
      feet = g.player.feet;
    if (feet.z < 8 && Math.abs(feet.x) < 13) {
      void this.finish();
      return;
    }
    // The first metres are safe: the player can read Q and learn the controls.
    if (!g.threatActive && feet.z > 54) return;
    g.threatActive = true;
    g.notebook.close();
    g.sketchbook?.close();
    g.satchel.close();
    this.brain.update(
      dt,
      feet,
      this.vigil.lamp.state === "open",
      g.player.stance === "crouch",
      this.canSeeSora(),
    );
    this.figure.root.position.copyFrom(this.brain.position);
    this.figure.root.rotation.y = Math.atan2(this.brain.direction.x, this.brain.direction.z);
    this.figure.animate(this.brain.elapsed, 1);
    this.voice.breathe(this.brain.position, this.brain.state === "chase" ? 1 : 0);
    this.stepIn -= dt;
    if (this.stepIn <= 0) {
      this.voice.step(this.brain.position);
      this.stepIn = this.brain.state === "chase" ? 0.48 : 0.95;
    }
    this.message(
      this.brain.state === "chase"
        ? "It saw you. Run behind solid cover, then crouch.\nBreak its line of sight. The funeral courtyard is safe."
        : this.brain.suspicion > 0.12
          ? "It is looking toward you…\nCrouch behind solid cover. F puts out your lamp."
          : this.brain.state === "search" || this.brain.state === "investigate"
            ? "It is searching where it heard you.\nStay behind cover and wait for its footsteps to pass."
            : "Stay out of its gaze. Hold C to crouch; F puts out the lamp.\nFollow the path toward the lit funeral courtyard.",
    );
    if (this.brain.state === "caught") {
      this.recovering = true;
      this.hud.hidden = true;
      this.voice.stop();
      g.bus.emit("player:caught", { by: "road_watcher" });
      void g.retryFromCheckpoint();
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
    this.hud.textContent = text;
  }
  private async finish(): Promise<void> {
    if (this.finishing) return;
    this.finishing = true;
    const g = this.game;
    g.threatActive = false;
    this.voice.stop();
    this.figure.root.setEnabled(false);
    this.hud.hidden = true;
    g.flags.set("ep1.early.complete", true);
    const save = this.capture();
    Object.assign(save.flags, {
      "checkpoint.spawn.cp": save.checkpoint,
      "checkpoint.spawn.x": 0,
      "checkpoint.spawn.y": 0,
      "checkpoint.spawn.z": 6,
      "checkpoint.spawn.yaw": Math.PI,
    });
    try {
      await g.checkpoints.mark(save, "Village · Funeral courtyard");
      g.hints.show("note.checkpointSaved", 6);
    } catch {
      g.hints.show("note.saveFailed", 8);
    }
    this.running = false;
    this.finishing = false;
    this.done?.();
    this.done = null;
  }
  private makeCover(): void {
    const scene = this.game.scene;
    const wood = new PBRMaterial("road_cart_weathered_wood", scene);
    wood.albedoColor = Color3.FromHexString("#665341").toLinearSpace();
    wood.roughness = 0.9;
    const iron = new PBRMaterial("road_cart_iron", scene);
    iron.albedoColor = Color3.FromHexString("#373b35").toLinearSpace();
    iron.metallic = 0.65;
    iron.roughness = 0.7;
    for (const [i, cover] of ROAD_COVER.entries()) {
      const x = (cover.minX + cover.maxX) / 2,
        z = (cover.minZ + cover.maxZ) / 2,
        w = cover.maxX - cover.minX,
        d = cover.maxZ - cover.minZ;
      const body = CreateBox(
        `road_cart_${i}_solid_cover`,
        { width: w, height: 1.25, depth: d },
        scene,
      );
      body.position.set(x, 0.625, z);
      body.material = wood;
      addStaticBox(body, "teak");
      // Boards, frame rails, oxidised wheels and a sloping load of timber read as physical cover.
      for (let k = 0; k < 6; k++) {
        const plank = CreateBox(
          `road_cart_${i}_board_${k}`,
          { width: w + 0.07, height: 0.028, depth: d + 0.035 },
          scene,
        );
        plank.position.set(x, 0.22 + k * 0.2, z);
        plank.material = iron;
      }
      for (const side of [-1, 1])
        for (const end of [-1, 1]) {
          const wheel = CreateCylinder(
            `road_cart_${i}_wheel_${side}_${end}`,
            { height: 0.11, diameter: 0.55, tessellation: 20 },
            scene,
          );
          wheel.rotation.z = Math.PI / 2;
          wheel.position.set(x + side * (w / 2 + 0.06), 0.29, z + end * d * 0.3);
          wheel.material = iron;
        }
      for (let k = 0; k < 4; k++) {
        const log = CreateCylinder(
          `road_cart_${i}_load_${k}`,
          { height: w + 0.18, diameter: 0.12, tessellation: 8 },
          scene,
        );
        log.rotation.z = Math.PI / 2 + (k % 2 ? 0.025 : -0.025);
        log.position.set(x, 1.28, z - d * 0.35 + k * d * 0.22);
        log.material = wood;
      }
    }
  }
}
