/**
 * Synthesised stand-in sounds for Spike S4, until the recordings in the Audio
 * Design Document (section 9) exist. Each is mono, at `sampleRate`, peak 0.9.
 * They keep what localisation needs: sharp, broadband transients (the ear
 * places a sound by its onset, and by the high frequencies the head shadows).
 * Pure functions over Float32Array, so they can be tested without audio.
 */

/** Two-pole resonant filter (RBJ biquad), band-pass or high-pass, applied in place. */
function biquad(
  samples: Float32Array,
  sampleRate: number,
  type: "bandpass" | "highpass" | "lowpass",
  frequency: number,
  q: number,
): Float32Array {
  const w = (2 * Math.PI * frequency) / sampleRate;
  const alpha = Math.sin(w) / (2 * q);
  const cos = Math.cos(w);
  let b0: number, b1: number, b2: number;
  if (type === "bandpass") [b0, b1, b2] = [alpha, 0, -alpha];
  else if (type === "highpass") [b0, b1, b2] = [(1 + cos) / 2, -(1 + cos), (1 + cos) / 2];
  else [b0, b1, b2] = [(1 - cos) / 2, 1 - cos, (1 - cos) / 2];
  const a0 = 1 + alpha;
  const a1 = -2 * cos;
  const a2 = 1 - alpha;
  let x1 = 0,
    x2 = 0,
    y1 = 0,
    y2 = 0;
  for (let i = 0; i < samples.length; i++) {
    const x = samples[i];
    const y = (b0 * x + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2) / a0;
    x2 = x1;
    x1 = x;
    y2 = y1;
    y1 = y;
    samples[i] = y;
  }
  return samples;
}

function noise(length: number, rand: () => number): Float32Array {
  const out = new Float32Array(length);
  for (let i = 0; i < length; i++) out[i] = rand() * 2 - 1;
  return out;
}

/** Adds `part` into `out` at `start` (seconds), shaped by an envelope. */
function mix(
  out: Float32Array,
  part: Float32Array,
  sampleRate: number,
  start: number,
  gain: number,
  envelope: (t: number) => number,
): void {
  const offset = Math.round(start * sampleRate);
  for (let i = 0; i < part.length && offset + i < out.length; i++) {
    out[offset + i] += part[i] * gain * envelope(i / sampleRate);
  }
}

function normalise(samples: Float32Array, peak = 0.9): Float32Array {
  let max = 0;
  for (const s of samples) max = Math.max(max, Math.abs(s));
  if (max > 0) for (let i = 0; i < samples.length; i++) samples[i] *= peak / max;
  return samples;
}

const decay = (seconds: number) => (t: number) => Math.exp(-t / seconds);

/**
 * A wet, heavy footstep on old teak with a short drag: the Neak Ta shadow
 * form in the house (Audio Design Document, section 5). Heel thump, board
 * knock, wet slap, then cloth dragged over wood.
 */
export function wetStep(sampleRate: number, rand: () => number): Float32Array {
  const length = Math.round(0.5 * sampleRate);
  const out = new Float32Array(length);
  const thump = new Float32Array(length);
  const pitch = 65 + rand() * 20;
  for (let i = 0; i < length; i++) thump[i] = Math.sin((2 * Math.PI * pitch * i) / sampleRate);
  mix(out, thump, sampleRate, 0, 0.9, decay(0.06));
  const knock = biquad(noise(length, rand), sampleRate, "bandpass", 380 + rand() * 120, 6);
  mix(out, knock, sampleRate, 0.002, 2.2, decay(0.07));
  const board = biquad(noise(length, rand), sampleRate, "bandpass", 1100 + rand() * 300, 9);
  mix(out, board, sampleRate, 0.004, 1.6, decay(0.05));
  const slap = biquad(noise(length, rand), sampleRate, "highpass", 2500, 0.7);
  mix(out, slap, sampleRate, 0.008, 0.7, decay(0.02));
  const drag = biquad(noise(length, rand), sampleRate, "bandpass", 700, 0.8);
  mix(out, drag, sampleRate, 0.09, 0.35, (t) => Math.sin(Math.min(1, t / 0.28) * Math.PI));
  return normalise(out);
}

/** A slow, wet breath with a rattle on the exhale, about 1.6 s. */
export function rattlingBreath(sampleRate: number, rand: () => number): Float32Array {
  const length = Math.round(1.6 * sampleRate);
  const air = biquad(noise(length, rand), sampleRate, "bandpass", 900, 0.6);
  const out = new Float32Array(length);
  for (let i = 0; i < length; i++) {
    const t = i / sampleRate;
    const inhale = t < 0.6 ? Math.sin((t / 0.6) * Math.PI) * 0.6 : 0;
    const exhale = t >= 0.7 ? Math.sin(((t - 0.7) / 0.9) * Math.PI) : 0;
    const rattle = 0.65 + 0.35 * Math.sign(Math.sin(2 * Math.PI * 28 * t));
    out[i] = air[i] * (inhale + exhale * rattle);
  }
  return normalise(out, 0.6);
}

/** A teak board groaning under weight, about 0.7 s. */
export function boardCreak(sampleRate: number, rand: () => number): Float32Array {
  const length = Math.round(0.7 * sampleRate);
  const out = new Float32Array(length);
  let phase = 0;
  for (let i = 0; i < length; i++) {
    const t = i / sampleRate;
    const f = 38 + 25 * Math.sin(t * 5) + (rand() - 0.5) * 12;
    phase += f / sampleRate;
    if (phase >= 1) {
      phase -= 1;
      out[i] = 1; // a stick-slip impulse
    }
  }
  biquad(out, sampleRate, "bandpass", 820, 5);
  biquad(out, sampleRate, "bandpass", 1650, 3);
  for (let i = 0; i < length; i++) out[i] *= Math.sin((i / length) * Math.PI);
  return normalise(out, 0.7);
}

/** Small deterministic random generator (mulberry32). */
export function seededRandom(seed: number): () => number {
  let h = seed >>> 0;
  return () => {
    h = (h + 0x6d2b79f5) | 0;
    let t = Math.imul(h ^ (h >>> 15), 1 | h);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Root-mean-square level of a range of samples. */
export function rms(samples: Float32Array, start = 0, end = samples.length): number {
  let sum = 0;
  for (let i = start; i < end; i++) sum += samples[i] * samples[i];
  return Math.sqrt(sum / Math.max(1, end - start));
}
