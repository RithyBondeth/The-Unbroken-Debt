import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Axis } from "@babylonjs/core/Maths/math.axis";
import { PhysicsRaycastResult } from "@babylonjs/core/Physics/physicsRaycastResult";
import type { PhysicsEngine } from "@babylonjs/core/Physics/v2/physicsEngine";
import type { Game } from "../../../core/Game";
import type { Vigil } from "../act1/Vigil";
import type { SaveData } from "../../../systems/saves/SaveData";
import { seededRandom } from "../../../audio/synth";
import { setControlText } from "../../../ui/html/controlText";
import { inKrasueKitchen, KRASUE_WINDOWS, throughKrasueWindow } from "../data/krasue";
import { krasueLament, krasueShriek } from "../audio/krasueSounds";
import { KrasueBrain } from "./KrasueBrain";
import { KrasueModel } from "./KrasueModel";
import "../../../ui/html/krasue.css";

/** Repeatable kitchen obstacle, independent of story progress and audio availability. */
export class KrasueEncounter {
  readonly brain = new KrasueBrain();
  readonly model: KrasueModel;
  private readonly warning = document.createElement("div");
  private readonly forward = new Vector3();
  private readonly sightHit = new PhysicsRaycastResult();
  private lament: StaticSound | null = null;
  private shriek: StaticSound | null = null;
  private soundOn = false;
  private recovering = false;
  private ownsThreat = false;
  private stopped = false;
  private lastSighting = 0;
  private screamAt = -Infinity;
  private message = "";
  private volume = 0;
  private readonly abort = new AbortController();

  get debugSight(): string {
    const hit = this.sightHit;
    return `${this.brain.state} · sight blocker: ${hit.hasHit ? (hit.body?.transformNode.name ?? "unknown") : "none"} · distance ${hit.hitDistance.toFixed(2)}`;
  }

  get activeScreams(): number {
    return this.shriek?.activeInstancesCount ?? 0;
  }

  constructor(
    private readonly game: Game,
    private readonly vigil: Vigil,
    private readonly capture: () => SaveData,
  ) {
    this.model = new KrasueModel(game.scene);
    this.warning.className = "krasue-warning";
    this.warning.setAttribute("role", "status");
    this.warning.hidden = true;
    document.body.append(this.warning);
    document.addEventListener(
      "visibilitychange",
      () => {
        if (document.hidden) this.silence();
      },
      { signal: this.abort.signal },
    );
    document.addEventListener(
      "pointerlockchange",
      () => {
        if (!game.input.pointerLocked) this.silence();
      },
      { signal: this.abort.signal },
    );
    game.scene.onDisposeObservable.addOnce(() => {
      this.stop();
      this.abort.abort();
      this.warning.remove();
      this.lament?.dispose();
      this.shriek?.dispose();
    });
  }

  async makeSounds(): Promise<void> {
    const audio = this.game.audio;
    if (!audio) return;
    const rate = audio.context.sampleRate;
    this.lament = await audio.spatialSound(
      "krasue_lament",
      audio.buffer(krasueLament(rate, seededRandom(739)), rate),
      "threat",
      this.brain.position,
      { loop: true, minDistance: 2, maxDistance: 14, volume: 0 },
    );
    this.shriek = await audio.spatialSound(
      "krasue_shriek",
      audio.buffer(krasueShriek(rate, seededRandom(741)), rate),
      "threat",
      this.brain.position,
      { minDistance: 2, maxDistance: 16, volume: 0.5 },
    );
  }

  update(dt: number, protectedMoment = false): void {
    if (this.stopped || this.recovering) return;
    if (!this.model.ready) {
      this.reset();
      return;
    }
    const g = this.game;
    const eye = g.camera.globalPosition;
    // Pausing preserves the encounter, but never advances an attack off-screen.
    if (document.hidden || !g.input.pointerLocked) {
      this.silence();
      return;
    }
    if (
      g.cutscene ||
      protectedMoment ||
      (g.threatActive && !this.ownsThreat) ||
      g.flags.get("ep1.seal1.broken", false)
    ) {
      this.reset();
      return;
    }
    const near = Vector3.DistanceSquared(eye, this.brain.window.center) < 100;
    const inKitchen = inKrasueKitchen(eye);
    g.camera.getDirectionToRef(Axis.Z, this.forward);
    if (!this.brain.active && inKitchen) {
      const window = KRASUE_WINDOWS.find((w) => Vector3.Dot(this.forward, w.normal) > 0.45);
      if (window) this.brain.selectWindow(window);
    }
    const visible = this.canSeePlayer();
    this.brain.update(dt, eye, visible, this.vigil.lamp.state === "open");
    if (this.brain.active && !this.ownsThreat) {
      this.ownsThreat = true;
      g.threatActive = true;
      g.stopInspecting();
      g.satchel.close();
      g.sketchbook?.close();
      g.bus.emit("sequence:start", { id: "krasue-window" });
    } else if (!this.brain.active) this.releaseThreat();
    if (this.ownsThreat) g.threatActive = true;
    this.model.root.setEnabled(near || this.brain.active);
    const attack = this.brain.state === "charging" || this.brain.state === "caught";
    if (this.brain.sightings !== this.lastSighting) {
      this.screamAt = this.brain.elapsed;
      if (this.shriek) this.shriek.spatial.position = this.brain.position.clone();
      this.shriek?.play();
      this.lastSighting = this.brain.sightings;
    }
    this.model.pose(
      this.brain.position,
      this.brain.active ? eye : this.brain.window.center,
      this.brain.elapsed,
      attack,
      this.brain.direction,
      this.brain.active,
      this.brain.elapsed - this.screamAt,
    );
    const audible = near && (inKitchen || this.brain.active);
    this.volume +=
      ((audible ? (attack ? 0.2 : this.brain.active ? 0.25 : 0.13) : 0) - this.volume) *
      Math.min(1, dt * 5);
    if (this.lament) {
      this.lament.volume = this.volume;
      this.lament.spatial.position = this.brain.position.clone();
      if (audible && !this.soundOn) {
        this.lament.play();
        this.soundOn = true;
      } else if (!audible && this.volume < 0.002) this.silence();
    }
    if (this.shriek) this.shriek.spatial.position = this.brain.position.clone();
    this.warning.hidden = !this.brain.active;
    const message = attack
      ? "It saw you. Get away from the window!"
      : this.brain.state === "searching"
        ? "Stay behind the wall. It is still searching."
        : "Something is watching through the window.\nBack away. Break its line of sight.";
    if (message !== this.message) {
      setControlText(this.warning, message);
      this.message = message;
    }
    if (this.brain.state === "caught") void this.kill();
  }

  canSeePlayer(): boolean {
    const g = this.game,
      eye = g.camera.globalPosition;
    const from = this.brain.position;
    if (g.hiding || !inKrasueKitchen(eye)) return false;
    if (!throughKrasueWindow(from, eye, this.brain.window)) return false;
    const delta = eye.subtract(from),
      length = delta.length();
    if (length < 0.01) return true;
    // The physics broadphase checks the actual window/room colliders without
    // intersecting millions of render triangles or the player's held lantern.
    const physics = g.scene.getPhysicsEngine() as PhysicsEngine | null;
    if (!physics) return false;
    physics.raycastToRef(from, eye, this.sightHit);
    return (
      !this.sightHit.hasHit ||
      this.sightHit.shape === g.player.collisionShape ||
      this.sightHit.body?.shape === g.player.collisionShape ||
      this.sightHit.hitDistance >= length - 0.1
    );
  }

  stop(): void {
    this.stopped = true;
    this.reset();
  }

  private reset(): void {
    this.brain.reset();
    this.model.root.setEnabled(false);
    this.warning.hidden = true;
    this.lastSighting = this.brain.sightings;
    this.releaseThreat();
    this.silence();
  }

  private releaseThreat(): void {
    if (!this.ownsThreat) return;
    this.game.threatActive = false;
    this.ownsThreat = false;
    this.game.bus.emit("sequence:end", { id: "krasue-window" });
  }

  private silence(): void {
    this.screamAt = -Infinity;
    this.lament?.stop();
    this.shriek?.stop();
    this.soundOn = false;
    this.volume = 0;
  }

  private async kill(): Promise<void> {
    if (this.recovering) return;
    this.recovering = true;
    const g = this.game;
    g.bus.emit("player:caught", { by: "krasue" });
    g.cutscene = true;
    g.gated.holdStill = true;
    g.gated.holdLook = true;
    g.stopInspecting();
    g.satchel.close();
    g.sketchbook?.close();
    this.warning.hidden = true;
    // The lethal contact stays in the world briefly before the shared death/retry UI.
    await new Promise((resolve) => setTimeout(resolve, 450));
    this.silence();
    if (!g.checkpoints.last) {
      // Legacy games may predate safe checkpoints. Retry outside the ambush room.
      const save = this.capture();
      Object.assign(save.flags, {
        "checkpoint.location": "House · Kitchen passage",
        "checkpoint.spawn.cp": save.checkpoint,
        "checkpoint.spawn.x": 1,
        "checkpoint.spawn.y": 2.5,
        "checkpoint.spawn.z": -12,
        "checkpoint.spawn.yaw": Math.PI / 2,
      });
      // Loading accepts this immutable fallback even if browser storage is full;
      // the shared retry UI owns any later write failure and its retry button.
      await g.checkpoints.load(save);
    }
    await g.retryFromCheckpoint();
  }
}
