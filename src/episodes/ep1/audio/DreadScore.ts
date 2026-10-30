import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import type { AudioSystem } from "../../../audio/AudioSystem";
import { STING_HIT, pressureBed, ringingEars, sting, type Sting } from "./dreadSounds";

/** The pressure bed at full dread: under the voices and the threats, never over them. */
const BED_MAX = 0.42;

/**
 * The title screen's dread carried into the game: a pressure bed whose level
 * the story raises and lowers, stingers that land on real scares, and the
 * ringing left in the ears after a shock. The bed sits on the music bus and the
 * stings on the threat bus, which is never ducked. Silence stays a sound: the
 * bed swells only where the story asks, and fades back out.
 */
export class DreadScore {
  private bed: StaticSound | null = null;
  private ringing: StaticSound | null = null;
  private readonly stings = new Map<Sting, StaticSound>();
  private level = 0;
  private target = 0;
  private playing = false;
  private stopped = false;

  constructor(private readonly audio: AudioSystem | null) {}

  async load(): Promise<void> {
    const audio = this.audio;
    if (!audio) return;
    const rate = audio.context.sampleRate;
    this.bed = await audio.sound(
      "dread_pressure",
      audio.buffer(pressureBed(rate), rate),
      "music",
      0,
    );
    this.bed.loop = true;
    this.ringing = await audio.sound(
      "dread_ringing",
      audio.buffer(ringingEars(rate), rate),
      "threat",
      1,
    );
    for (const kind of ["rise", "shock", "drop", "swell"] as const)
      this.stings.set(
        kind,
        await audio.sound(`dread_${kind}`, audio.buffer(sting(rate, kind), rate), "threat", 1),
      );
  }

  /** 0–1: how close the dark has come. The bed eases towards it over a few seconds. */
  pressure(level: number): void {
    this.target = Math.max(0, Math.min(1, level));
  }

  /** Plays a sting now; its hit lands `lead(kind)` seconds later. */
  sting(kind: Sting, volume = 1): void {
    const sound = this.stings.get(kind);
    if (!sound || this.stopped) return;
    sound.volume = volume;
    sound.play();
  }

  /** Seconds before a beat to start `kind`, so its hit lands on the beat. */
  lead(kind: Sting): number {
    return STING_HIT[kind];
  }

  /** The ears ringing after a shock. */
  ring(): void {
    if (!this.stopped) this.ringing?.play();
  }

  update(dt: number): void {
    if (this.stopped || !this.bed) return;
    // Rises over about four seconds, falls away over about six.
    const tau = this.target > this.level ? 4 : 6;
    this.level += (this.target - this.level) * Math.min(1, dt / tau);
    if (!this.playing && this.level > 0.005) {
      this.playing = true;
      this.bed.play();
    }
    this.bed.volume = this.level * BED_MAX;
  }

  stop(): void {
    this.stopped = true;
    this.bed?.stop();
    this.ringing?.stop();
    for (const sound of this.stings.values()) sound.stop();
  }
}
