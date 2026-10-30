import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Axis } from "@babylonjs/core/Maths/math.axis";
import type { Game } from "../../../core/Game";
import { seededRandom } from "../../../audio/synth";
import { foliageMovement } from "../audio/atmosphereSounds";
import { forestSource, inUneaseForest } from "../data/forestAtmosphere";
import { ForestUnease } from "./ForestUnease";

/** Small environmental false alarms, subordinate to every authored encounter. */
export class ForestAtmosphere {
  readonly director = new ForestUnease(seededRandom(19732));
  source: Vector3 | null = null;
  private readonly forward = new Vector3();
  private readonly sounds: StaticSound[] = [];
  private playing: StaticSound | null = null;
  private volume = 0;
  private stopped = false;
  private readonly abort = new AbortController();

  constructor(private readonly game: Game) {
    const cancel = () => {
      this.director.update(0.1, false, false);
      this.playing?.stop();
      this.playing = null;
      this.volume = 0;
    };
    // Render loops can stop in hidden tabs: don't leave a rustle playing until
    // another frame arrives. Re-entry gets a cooldown, never a queued scare.
    document.addEventListener(
      "visibilitychange",
      () => {
        if (document.hidden) cancel();
      },
      { signal: this.abort.signal },
    );
    document.addEventListener(
      "pointerlockchange",
      () => {
        if (!game.input.pointerLocked) cancel();
      },
      { signal: this.abort.signal },
    );
    game.scene.onDisposeObservable.add(() => this.stop());
  }

  get silence(): number {
    return this.director.silence;
  }

  async makeSounds(): Promise<void> {
    const audio = this.game.audio;
    if (!audio) return;
    const rate = audio.context.sampleRate;
    for (let i = 0; i < 3; i++) {
      this.sounds.push(
        await audio.spatialSound(
          `forest_brush_${i}`,
          audio.buffer(foliageMovement(rate, seededRandom(8500 + i)), rate),
          "ambience",
          Vector3.Zero(),
          { panning: "HRTF", minDistance: 3, maxDistance: 18, volume: 0 },
        ),
      );
    }
  }

  /** Only exposed to development fixtures; no scripted scare or story state is bypassed. */
  previewSequence(): void {
    if (import.meta.env.DEV) this.director.scheduleSoon();
  }

  update(dt: number, protectedMoment: boolean): void {
    if (this.stopped) return;
    const g = this.game,
      feet = g.player.feet,
      eye = g.camera.globalPosition;
    g.camera.getDirectionToRef(Axis.Z, this.forward);
    const candidate = forestSource(
      eye.x,
      eye.z,
      this.forward.x,
      this.forward.z,
      this.director.sequence,
    );
    let allowed =
      !document.hidden &&
      g.input.pointerLocked &&
      !g.cutscene &&
      !g.threatActive &&
      !g.hiding &&
      !g.inspecting &&
      !g.gated.reading &&
      !g.gated.holdStill &&
      !g.gated.holdLook &&
      !g.notebook.isOpen &&
      !g.satchel.isOpen &&
      !g.subtitles.active &&
      !protectedMoment &&
      this.sounds.length > 0 &&
      inUneaseForest(feet.x, feet.y, feet.z);
    // Leave the first shrine and gate apparition approaches entirely to their scripts.
    if (
      !g.flags.get("ep1.act2.started", false) &&
      ((feet.z >= 16 && feet.z <= 24) || (feet.z >= 40 && feet.z <= 50))
    )
      allowed = false;
    if (allowed && document.querySelector(".document-reader:not([hidden])")) allowed = false;
    const before = this.director.phase;
    if (before === "waiting" && !candidate) allowed = false;
    const dx = (this.source?.x ?? eye.x) - eye.x;
    const dz = (this.source?.z ?? eye.z) - eye.z;
    const distance = Math.hypot(dx, dz);
    const turned =
      this.source !== null &&
      distance > 0 &&
      (dx * this.forward.x + dz * this.forward.z) / distance > Math.cos(Math.PI / 5);
    // Walking away from the bush ends the cue as well; it never follows Sora.
    if (before !== "waiting" && distance > 16) allowed = false;
    this.director.update(dt, allowed, turned);
    if (before === "waiting" && this.director.phase === "hush" && candidate)
      this.source = new Vector3(candidate[0], feet.y + 0.35, candidate[1]);
    if (before !== "movement" && this.director.phase === "movement" && this.source) {
      this.playing?.stop();
      this.playing = this.sounds[(this.director.sequence - 1) % this.sounds.length];
      this.playing.spatial.position = this.source.clone();
      this.playing.volume = this.volume = 0;
      this.playing.play();
    }
    const moving = allowed && this.director.phase === "movement";
    const target = moving ? 0.24 : 0;
    this.volume += (target - this.volume) * (1 - Math.exp(-Math.max(0, dt) / 0.065));
    if (this.playing) {
      this.playing.volume = this.volume;
      if (!moving && this.volume < 0.002) {
        this.playing.stop();
        this.playing = null;
      }
    }
    if (this.director.phase === "waiting") this.source = null;
  }

  stop(): void {
    this.stopped = true;
    this.abort.abort();
    this.director.update(0.1, false, false);
    this.director.silence = 0;
    for (const sound of this.sounds) sound.stop();
    this.playing = null;
  }
}
