import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import type { Game } from "@/core/Game";
import { noise, seededRandom } from "@/audio/synth";
import { sweepBand, type Stereo } from "@/audio/dread";
import { sting } from "@/audio/sounds/dreadSounds";

/** Seconds into a pass when she is nearest: the whoosh peaks and the sting lands here. */
export const PASS_NEAREST = 0.5;

/**
 * Something gliding past at impossible speed, 1.3 s, panned `from` → `to` (-1 left, +1
 * right): torn air whose band climbs as it closes and falls as it goes, under it a breathy
 * cry bending down as it passes (Doppler). No feet: she does not run, she is carried.
 */
export function ghostPass(rate: number, random: () => number, from = -1, to = 1): Stereo {
  const n = Math.round(rate * 1.3);
  const air = noise(n, random);
  const band = sweepBand(
    air,
    rate,
    (t) => 280 + 1500 * Math.exp(-(((t - PASS_NEAREST) / 0.22) ** 2)) + 120 * t,
    1.6,
  );
  const left = new Float32Array(n),
    right = new Float32Array(n);
  let phase = 0;
  for (let i = 0; i < n; i++) {
    const t = i / rate;
    // Rises fast as she closes, falls more slowly as she goes.
    const near = t < PASS_NEAREST ? (t / PASS_NEAREST) ** 2.2 : Math.exp(-(t - PASS_NEAREST) * 4.5);
    const fade = Math.min(1, (1.3 - t) / 0.12);
    // The cry: a breathy, falling tone, loudest just past the nearest point.
    const pitch = 520 - 260 / (1 + Math.exp(-(t - PASS_NEAREST) * 14));
    phase += (2 * Math.PI * pitch) / rate;
    const cry =
      (Math.sin(phase) * 0.5 + Math.sin(phase * 2.01) * 0.2) *
      Math.exp(-(((t - PASS_NEAREST - 0.05) / 0.2) ** 2)) *
      (0.6 + 0.4 * random());
    const s = (band[i] * 1.6 + cry * 0.18) * near * fade;
    // Equal-power pan along the pass.
    const pan = from + (to - from) * Math.min(1, Math.max(0, (t - 0.1) / (2 * PASS_NEAREST - 0.2)));
    const a = ((pan + 1) * Math.PI) / 4;
    left[i] = s * Math.cos(a);
    right[i] = s * Math.sin(a);
  }
  let peak = 0;
  for (let i = 0; i < n; i++) peak = Math.max(peak, Math.abs(left[i]), Math.abs(right[i]));
  const k = peak > 0 ? 0.85 / peak : 1;
  for (let i = 0; i < n; i++) {
    left[i] *= k;
    right[i] *= k;
  }
  return [left, right];
}

/**
 * The ghosts' own sounds that the soundscape doesn't carry: the woman in red passing,
 * either way, and the sting that lands with her or with a corpse's grab. Silent without audio.
 */
export class GhostAudio {
  private passes: StaticSound[] = [];
  private shock: StaticSound | null = null;

  constructor(private readonly game: Game) {}

  async load(): Promise<void> {
    const audio = this.game.audio;
    if (!audio) return;
    const rate = audio.context.sampleRate;
    this.passes = await Promise.all(
      [
        [-1, 1],
        [1, -1],
      ].map(([from, to], i) =>
        audio.sound(
          "ep2_ghost_pass_" + i,
          audio.buffer(ghostPass(rate, seededRandom(9101 + i), from, to), rate),
          "threat",
          0.55,
        ),
      ),
    );
    this.shock = await audio.sound(
      "ep2_ghost_shock",
      audio.buffer(sting(rate, "shock"), rate),
      "threat",
      0.42,
    );
  }

  /** She passes left to right (`rightward`) or right to left. */
  pass(rightward: boolean): void {
    const sound = this.passes[rightward ? 0 : 1];
    if (!sound) return;
    sound.playbackRate = 0.96 + Math.random() * 0.08;
    sound.play();
  }

  /** A sharp sting, `delay` seconds from now (its hit lands almost at once). */
  hit(delay = 0, volume = 1): void {
    if (!this.shock) return;
    const shock = this.shock;
    window.setTimeout(() => {
      shock.volume = 0.42 * volume;
      shock.play();
    }, delay * 1000);
  }
}
