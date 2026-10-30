/**
 * The title screen's horror toolkit, shared with the episodes: a moving
 * band-pass, seamless loops, a Schroeder hall, wordless whispers, boards
 * taking weight and knocks. Pure functions over Float32Array; stereo is
 * [left, right].
 */
import { biquad, noise } from "./synth";

export type Stereo = [Float32Array, Float32Array];

/** Chamberlin state-variable band-pass whose centre can move every sample. */
export function sweepBand(
  input: Float32Array,
  rate: number,
  centre: (t: number) => number,
  q: number,
) {
  const out = new Float32Array(input.length);
  let low = 0,
    band = 0;
  const damp = 1 / q;
  for (let i = 0; i < input.length; i++) {
    const f = 2 * Math.sin((Math.PI * Math.min(centre(i / rate), rate / 6)) / rate);
    low += f * band;
    const high = input[i] - low - damp * band;
    band += f * high;
    out[i] = band;
  }
  return out;
}

/** Folds the last `fade` seconds over the start so a loop never clicks. */
export function loopify(data: Float32Array, rate: number, fade: number): Float32Array {
  const n = Math.round(fade * rate);
  const out = data.slice(0, data.length - n);
  for (let i = 0; i < n; i++) {
    const t = i / n;
    out[i] =
      out[i] * Math.sin((t * Math.PI) / 2) + data[out.length + i] * Math.cos((t * Math.PI) / 2);
  }
  return out;
}

/** Schroeder hall: four damped combs into two all-passes, mixed with the dry signal. */
export function hall(dry: Float32Array, rate: number, wet: number): Float32Array {
  const out = new Float32Array(dry.length);
  for (const [ms, feedback] of [
    [29.7, 0.84],
    [37.1, 0.83],
    [41.1, 0.82],
    [43.7, 0.81],
  ]) {
    const size = Math.round((ms / 1000) * rate);
    const line = new Float32Array(size);
    let p = 0,
      lp = 0;
    for (let i = 0; i < dry.length; i++) {
      const y = line[p];
      lp = y * 0.6 + lp * 0.4;
      line[p] = dry[i] + lp * feedback;
      out[i] += y * 0.25;
      p = (p + 1) % size;
    }
  }
  for (const ms of [5, 1.7]) {
    const size = Math.round((ms / 1000) * rate);
    const line = new Float32Array(size);
    let p = 0;
    for (let i = 0; i < out.length; i++) {
      const delayed = line[p];
      const x = out[i];
      line[p] = x + delayed * 0.7;
      out[i] = delayed - x * 0.7;
      p = (p + 1) % size;
    }
  }
  for (let i = 0; i < out.length; i++) out[i] = dry[i] * (1 - wet) + out[i] * wet;
  return out;
}

/** Breathy syllables, hard left or right, never quite words. */
export function whisper(rate: number, rand: () => number, seconds: number): Float32Array {
  const raw = noise(Math.round(rate * seconds), rand);
  const hiss = biquad(
    raw.slice(),
    rate,
    "bandpass",
    Math.min(3800 + rand() * 1800, rate * 0.42),
    1.4,
  );
  const vowelBase = 700 + rand() * 600;
  const vowel = sweepBand(raw, rate, (t) => vowelBase + 400 * Math.sin(t * 9), 5);
  const syllable = 5.5 + rand() * 3;
  const out = new Float32Array(raw.length);
  for (let i = 0; i < out.length; i++) {
    const t = i / rate;
    const env =
      Math.max(0, Math.sin(t * Math.PI * syllable)) ** 2 * Math.sin((t / seconds) * Math.PI);
    out[i] = (hiss[i] * 0.8 + vowel[i] * 0.5) * env;
  }
  return out;
}

/** Old boards taking weight: a slipping run of tiny impulses through a moving resonance. */
export function creak(rate: number, rand: () => number, seconds: number): Float32Array {
  const out = new Float32Array(Math.round(rate * seconds));
  const start = 35 + rand() * 40;
  let next = 0;
  for (let i = 0; i < out.length; i++) {
    const t = i / out.length;
    if (i >= next) {
      out[i] = (rand() * 0.6 + 0.4) * Math.sin(t * Math.PI);
      next = i + Math.round(rate / (start + 60 * t + rand() * 12));
    }
  }
  const body = 380 + rand() * 300;
  return sweepBand(out, rate, (t) => body + 160 * t, 22);
}

export function knock(rate: number): Float32Array {
  const out = new Float32Array(Math.round(rate * 0.35));
  for (let i = 0; i < out.length; i++) {
    const t = i / rate;
    out[i] = Math.sin(t * 2 * Math.PI * (95 - 60 * t)) * Math.exp(-t * 28);
  }
  return out;
}

export function place(
  side: Float32Array,
  part: Float32Array,
  rate: number,
  at: number,
  gain: number,
) {
  const offset = Math.round(at * rate);
  for (let i = 0; i < part.length && offset + i < side.length; i++)
    side[offset + i] += part[i] * gain;
}
