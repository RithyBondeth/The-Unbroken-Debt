/**
 * The listening screen's sound, synthesised: a held-breath bed of drone and far rain,
 * and the sharp breath and thud that cut it off when the player presses Enter. The
 * whispers, knocks and creaks come from ./dread. Pure functions over Float32Array.
 */
import { biquad, brown, noise, seededRandom } from "./synth";
import { loopify, type Stereo } from "./dread";

/** Seconds in the bed's loop. */
export const BED_SECONDS = 12;

/** A low drone, two tones beating against each other and rain far off; loops seamlessly. */
export function entryBed(rate: number): Stereo {
  const length = Math.round(rate * (BED_SECONDS + 1));
  const rand = seededRandom(66);
  const drone = biquad(brown(length, rand), rate, "lowpass", 90, 0.7);
  const rain = biquad(noise(length, rand), rate, "lowpass", Math.min(1700, rate * 0.4), 0.5);
  let peak = 0;
  for (const v of drone) peak = Math.max(peak, Math.abs(v));
  const left = new Float32Array(length);
  const right = new Float32Array(length);
  for (let i = 0; i < length; i++) {
    const t = i / rate;
    const tone = Math.sin(2 * Math.PI * 55 * t) * 0.054 + Math.sin(2 * Math.PI * 55.31 * t) * 0.045;
    const bed = (drone[i] / peak) * 0.22 + tone;
    left[i] = bed + rain[i] * 0.06;
    right[i] = bed * 0.97 + rain[(i + 731) % length] * 0.06;
  }
  return [loopify(left, rate, 1), loopify(right, rate, 1)];
}

/** A sharp breath right at the ear, as if something leaned in. */
export function entryBreath(rate: number): Float32Array {
  const length = Math.round(rate * 0.42);
  const air = biquad(noise(length, seededRandom(67)), rate, "bandpass", 2600, 0.9);
  for (let i = 0; i < length; i++) {
    const t = i / length;
    air[i] *= Math.min(1, t / 0.12) * (1 - t) ** 0.6 * 1.6;
  }
  return air;
}

/** A heavy, falling thud under the breath. */
export function entryThud(rate: number): Float32Array {
  const out = new Float32Array(Math.round(rate * 1.4));
  for (let i = 0; i < out.length; i++) {
    const t = i / rate;
    out[i] = Math.sin(2 * Math.PI * (48 - 14 * t) * t) * Math.exp(-t * 4.5) * 0.95;
  }
  return out;
}
