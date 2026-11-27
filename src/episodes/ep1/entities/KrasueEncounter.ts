import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Axis } from "@babylonjs/core/Maths/math.axis";
import type { Game } from "@/core/Game";
import type { Vigil } from "../act1/Vigil";
import { setControlText } from "@/ui/html/controlText";
import { exposedToPaddies } from "../data/krasue";
import type { VillageAudio } from "../audio/VillageAudio";
import { KrasueBrain } from "./KrasueBrain";
import { KrasueFlyer } from "./KrasueFlyer";
import "@/ui/html/krasue.css";

/**
 * Redesigned Rice-Field Krasue (អាប) encounter:
 * Floats over the flooded rice paddies with a heartbeat-pulsed green/red organ light.
 * Calm emerald-green while feeding over the fields; shifts blood-red and banks closer
 * if Sora keeps her kerosene lamp open while exposed. Dousing the lamp (`F`) or taking
 * shelter lets it drift back into the palms; ignoring the red warning causes a close
 * pass that snuffs Sora's lamp with an ear-ringing shriek.
 */
export class KrasueEncounter {
  readonly brain = new KrasueBrain();
  readonly model: KrasueFlyer;
  private readonly warning = document.createElement("div");
  private readonly forward = new Vector3();
  private hum: StaticSound | null = null;
  private humOn = false;
  private volume = 0;
  private lastAlert = 0;
  private lastPass = 0;
  private screamAt = -Infinity;
  private stopped = false;
  private message = "";
  private readonly abort = new AbortController();

  constructor(
    private readonly game: Game,
    private readonly vigil: Vigil,
    private readonly villageAudio: VillageAudio | null = null,
  ) {
    this.model = new KrasueFlyer(game.scene);
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
      this.hum?.dispose();
    });
  }

  async makeSounds(): Promise<void> {
    if (!this.villageAudio) return;
    this.hum = await this.villageAudio.createSpatialLoop(
      "krasue_paddy_hum",
      "amb_ep1_krasue_hum",
      this.brain.position,
      "threat",
      { panning: "HRTF", minDistance: 6, maxDistance: 58, volume: 0 },
    );
  }

  /** Forces an immediate rice-field flight pass (for story milestones or dev QA). */
  summon(pathIndex?: number): void {
    if (!this.stopped) this.brain.summon(pathIndex);
  }

  update(dt: number, protectedMoment = false): void {
    if (this.stopped) return;
    const g = this.game;
    if (document.hidden || !g.input.pointerLocked) {
      this.silence();
      return;
    }
    if (g.cutscene || protectedMoment || g.threatActive || g.flags.get("ep1.seal1.broken", false)) {
      if (!this.brain.hidden) this.reset();
      return;
    }

    const eye = g.camera.globalPosition;
    const feet = g.player.feet;
    g.camera.getDirectionToRef(Axis.Z, this.forward);

    const toKrasue = this.brain.position.subtract(eye);
    const dist = toKrasue.length();
    const looking =
      !this.brain.hidden &&
      dist > 0.5 &&
      Vector3.Dot(this.forward, toKrasue.scale(1 / dist)) > 0.72;
    const exposed = exposedToPaddies(feet);
    const lampOpen = this.vigil.lamp.state === "open";

    this.brain.update(dt, eye, looking, lampOpen, exposed);

    // Alert audio sting when glow turns blood-red
    if (this.brain.alerts !== this.lastAlert) {
      this.lastAlert = this.brain.alerts;
      this.screamAt = this.brain.elapsed;
      this.villageAudio?.play("krasueAlert", this.brain.position, 0.85, 0.94);
    }

    // Close-range fly-by pass: blows out Sora's lamp + physical camera flinch + visceral audio hit
    if (this.brain.passes !== this.lastPass) {
      this.lastPass = this.brain.passes;
      this.screamAt = this.brain.elapsed;
      this.villageAudio?.play("krasueAlert", this.brain.position, 1.15, 1.1);
      this.villageAudio?.play("shockHit", eye, 1.0);
      this.villageAudio?.play("soraGasp", eye, 0.95);
      this.game.player.jolt?.(1.05, 1);
      this.game.atmosphere.scare();
      if (this.vigil.lamp.burning) this.vigil.lamp.putOut();
      void g.subtitles.say("Sora", "The light—it came straight for the lamp…", 3.5);
    }

    this.model.root.setEnabled(!this.brain.hidden);
    this.model.redness = this.brain.redness;
    const attacking = this.brain.state === "approaching" || this.brain.state === "pass";
    this.model.pose(
      this.brain.position,
      this.brain.active ? eye : this.brain.position.add(this.brain.direction.scale(6)),
      this.brain.elapsed,
      attacking,
      this.brain.direction,
      this.brain.active,
      this.brain.elapsed - this.screamAt,
    );

    // Spatialized organic lament hum audible clearly across the paddies
    const audible = !this.brain.hidden && dist < 58;
    const targetVol = audible ? (attacking ? 0.68 : this.brain.active ? 0.52 : 0.36) : 0;
    this.volume += (targetVol - this.volume) * Math.min(1, dt * 3.5);
    if (this.hum) {
      this.hum.volume = this.volume;
      this.hum.spatial.position = this.brain.position.clone();
      this.hum.spatial.update?.();
      if (audible && !this.humOn) {
        this.hum.play();
        this.humOn = true;
      } else if (!audible && this.volume < 0.004) {
        this.silence();
      }
    }

    // Minimal diegetic warning only while Krasue has shifted blood-red and is actively hunting
    const showWarn = this.brain.state === "alert" || this.brain.state === "approaching";
    this.warning.hidden = !showWarn;
    if (showWarn) {
      const next = lampOpen
        ? "Blood-red glow over the paddies — F douses the lamp."
        : "Keep dark and look away until it drifts past.";
      if (next !== this.message) {
        this.message = next;
        setControlText(this.warning, next);
      }
    }
  }

  stop(): void {
    this.stopped = true;
    this.reset();
  }

  private reset(): void {
    this.brain.reset();
    this.model.root.setEnabled(false);
    this.warning.hidden = true;
    this.lastAlert = this.brain.alerts;
    this.lastPass = this.brain.passes;
    this.silence();
  }

  private silence(): void {
    this.screamAt = -Infinity;
    this.hum?.stop();
    this.humOn = false;
    this.volume = 0;
  }
}
