import { biquad, noise, normalise } from "../../../audio/synth";

/** Wordless pressure: close beating partials, an uneven pulse and bowed air.
 * Whole-number carrier cycles and a periodic envelope keep the 12 s loop clean.
 * Remains audible on laptop speakers; it does not rely on sub-bass or loudness.
 */
export function dreadBed(rate: number, rand: () => number): Float32Array {
  const length = Math.round(rate * 12);
  const air = biquad(noise(length, rand), rate, "bandpass", 480, 0.8);
  const out = new Float32Array(length);
  for (let i = 0; i < length; i++) {
    const t = i / rate;
    const phase = (2 * Math.PI * i) / length;
    const pulse = (0.5 + 0.5 * Math.sin(phase * 13 + 0.4 * Math.sin(phase * 3))) ** 5;
    const swell = 0.55 + 0.22 * Math.sin(phase) + 0.13 * Math.sin(phase * 3);
    const seam = Math.min(1, i / (rate * 0.08), (length - 1 - i) / (rate * 0.08));
    out[i] =
      seam *
      (swell *
        (Math.sin(2 * Math.PI * 73 * t) * 0.18 +
          Math.sin(2 * Math.PI * (73 + 7 / 12) * t) * 0.13 +
          Math.sin(2 * Math.PI * (147 + 1 / 12) * t) * 0.06) +
        pulse * 0.1 * Math.sin(2 * Math.PI * 109 * t) +
        air[i] * 0.17);
  }
  return normalise(out, 0.55);
}

/** A breath-driven, corroded brass strain with an irregular creaking tail. */
export function spiritRattle(rate: number, rand: () => number): Float32Array {
  const out = biquad(noise(Math.round(rate * 3.8), rand), rate, "bandpass", 920, 1.8);
  const phases = [rand(), rand(), rand()].map((p) => p * Math.PI * 2);
  for (let i = 0; i < out.length; i++) {
    const t = i / rate;
    const envelope = Math.min(1, t / 0.65) * Math.exp(-t * 1.05) * Math.min(1, (3.8 - t) / 0.25);
    let ring = 0;
    [187, 283, 431].forEach((f, k) => {
      ring += Math.sin(t * Math.PI * 2 * f + phases[k] + 0.7 * Math.sin(t * 9.1)) * 0.11;
    });
    out[i] = (out[i] * 0.7 + ring) * envelope;
  }
  return normalise(out, 0.65);
}
