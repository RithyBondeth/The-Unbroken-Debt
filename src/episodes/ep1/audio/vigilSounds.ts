import { biquad, mix, noise, normalise } from "../../../audio/synth";

/**
 * Synthesised stand-ins for the vigil's sounds (Audio Design Document,
 * section 9) until the recordings exist: the match, the lamp, kerosene poured,
 * incense whispers. Mono, peak 0.9 or less, pure functions.
 */

const seconds = (s: number, sampleRate: number) => Math.round(s * sampleRate);

/** A safety match struck on the box: a rasp, the flare catching, then its hiss. */
export function matchStrike(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(1.2, sampleRate);
  const out = new Float32Array(length);
  const rasp = biquad(noise(seconds(0.12, sampleRate), rand), sampleRate, "bandpass", 3800, 1.4);
  mix(out, rasp, sampleRate, 0.02, 1, (t) => Math.sin((Math.PI * t) / 0.12));
  const flare = biquad(noise(seconds(0.5, sampleRate), rand), sampleRate, "lowpass", 1600, 0.6);
  mix(out, flare, sampleRate, 0.13, 1.4, (t) => Math.min(1, t / 0.02) * Math.exp(-t / 0.12));
  const hiss = biquad(noise(length, rand), sampleRate, "bandpass", 2600, 0.8);
  for (let i = seconds(0.2, sampleRate); i < length; i++) {
    const t = i / sampleRate - 0.2;
    out[i] += hiss[i] * 0.12 * Math.min(1, t / 0.1) * Math.min(1, (1.0 - t) / 0.3);
  }
  return normalise(out, 0.8);
}

/** The wick turned up and caught, or turned down and out: a small metal click and a puff. */
export function lampWick(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(0.45, sampleRate);
  const out = new Float32Array(length);
  const click = biquad(noise(seconds(0.02, sampleRate), rand), sampleRate, "bandpass", 4200, 5);
  mix(out, click, sampleRate, 0.01, 1, (t) => Math.exp(-t / 0.004));
  const puff = biquad(noise(seconds(0.35, sampleRate), rand), sampleRate, "lowpass", 500, 0.7);
  mix(out, puff, sampleRate, 0.05, 0.8, (t) => Math.min(1, t / 0.05) * Math.exp(-t / 0.1));
  return normalise(out, 0.6);
}

/** Kerosene poured from a bottle into the tank: glugs over a trickle. */
export function pourOil(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(1.8, sampleRate);
  const out = biquad(noise(length, rand), sampleRate, "bandpass", 1100, 1.2);
  for (let i = 0; i < length; i++) {
    const t = i / sampleRate;
    const glug = 0.4 + 0.6 * Math.max(0, Math.sin(t * 2 * Math.PI * 5.5)) ** 4;
    out[i] *= glug * Math.min(1, t / 0.1) * Math.min(1, (1.8 - t) / 0.25);
  }
  return normalise(out, 0.6);
}

/**
 * Whispering with no words in it, for the dying incense (A1-10): breathy
 * syllables that rise and fall. Loops without a click.
 */
export function whispers(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(6, sampleRate);
  const out = new Float32Array(length);
  for (let k = 0; k < 26; k++) {
    const d = 0.12 + rand() * 0.3;
    const syllable = biquad(
      noise(seconds(d, sampleRate), rand),
      sampleRate,
      "bandpass",
      1800 + rand() * 2600,
      2 + rand() * 4,
    );
    mix(
      out,
      syllable,
      sampleRate,
      0.3 + rand() * 5.2,
      0.3 + rand() * 0.7,
      (t) => Math.sin((Math.PI * t) / d) ** 2,
    );
  }
  const n = seconds(0.3, sampleRate);
  for (let i = 0; i < n; i++) {
    out[i] *= i / n;
    out[length - 1 - i] *= i / n;
  }
  return normalise(out, 0.7);
}
