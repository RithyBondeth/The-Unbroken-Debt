import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { AudioSystem } from "../../../audio/AudioSystem";
import { rattlingBreath, seededRandom, wetStep } from "../../../audio/synth";
import { sniff } from "./houseSounds";

/** Seconds from one breath to the next at rest: slow, heavy, about 17 a minute. */
const BREATH_CYCLE = 3.6;
/** Its head is about this far above its feet. */
const HEAD = 1.7;

/**
 * The shadow form's body as it moves (S1-025, S1-031; Audio Design Document,
 * section 5): wet drags laid under each footstep, its rattling breath
 * following it, faster when it hunts, and a sniff where it searches. Only
 * ever played where the form really is ("sound tells the truth").
 */
export class StalkerVoice {
  private readonly drags: StaticSound[] = [];
  private breath: StaticSound | null = null;
  private sniffSound: StaticSound | null = null;
  private breathing = false;
  private next = 0;

  constructor(private readonly volume = 0.55) {}

  async load(audio: AudioSystem | null, name: string, seed: number): Promise<void> {
    if (!audio) return;
    const rate = audio.context.sampleRate;
    const at = Vector3.Zero();
    for (let k = 0; k < 3; k++) {
      const drag = await audio.spatialSound(
        `${name}_drag_${k}`,
        audio.buffer(wetStep(rate, seededRandom(seed + k)), rate),
        "threat",
        at,
        { minDistance: 2, volume: this.volume * 0.7 },
      );
      drag.playbackRate = 0.82 + k * 0.05;
      this.drags.push(drag);
    }
    // Two different breaths, each followed by the pause before the next.
    const cycle = Math.round(BREATH_CYCLE * rate);
    const loop = new Float32Array(cycle * 2);
    loop.set(rattlingBreath(rate, seededRandom(seed + 10)), Math.round(0.3 * rate));
    loop.set(rattlingBreath(rate, seededRandom(seed + 11)), cycle + Math.round(0.5 * rate));
    this.breath = await audio.spatialSound(
      `${name}_breath`,
      audio.buffer(loop, rate),
      "threat",
      at,
      {
        loop: true,
        minDistance: 1.5,
        volume: 0,
      },
    );
    this.sniffSound = await audio.spatialSound(
      `${name}_sniff`,
      audio.buffer(sniff(rate, seededRandom(seed + 12)), rate),
      "threat",
      at,
      { minDistance: 1.5, volume: this.volume },
    );
  }

  /** A wet drag under the step it has just taken at `feet`. */
  step(feet: Vector3): void {
    const drag = this.drags[this.next++ % Math.max(1, this.drags.length)];
    if (!drag) return;
    drag.spatial.position = feet.add(new Vector3(0, 0.05, 0));
    drag.play();
  }

  /**
   * Keeps its breath on it while it is out (`feet`), quickening and louder as
   * `urgency` goes from 0 (walking) to 1 (chasing); null stops it.
   */
  breathe(feet: Vector3 | null, urgency = 0): void {
    const breath = this.breath;
    if (!breath) return;
    if (!feet) {
      if (this.breathing) breath.stop();
      this.breathing = false;
      return;
    }
    breath.spatial.position = feet.add(new Vector3(0, HEAD, 0));
    breath.volume = this.volume * (0.7 + 0.5 * urgency);
    breath.playbackRate = 1 + 0.35 * urgency;
    if (!this.breathing) breath.play();
    this.breathing = true;
  }

  /** It stops and scents the air where it lost her. */
  sniffAt(feet: Vector3): void {
    if (!this.sniffSound) return;
    this.sniffSound.spatial.position = feet.add(new Vector3(0, HEAD - 0.1, 0));
    this.sniffSound.play();
  }

  stop(): void {
    this.breathe(null);
    for (const drag of this.drags) drag.stop();
    this.sniffSound?.stop();
  }
}
