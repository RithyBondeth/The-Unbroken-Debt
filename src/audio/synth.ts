/**
 * Synthesised stand-in sounds for Spike S4, until the recordings in the Audio
 * Design Document (section 9) exist. Each is mono, at `sampleRate`, peak 0.9.
 * They keep what localisation needs: sharp, broadband transients (the ear
 * places a sound by its onset, and by the high frequencies the head shadows).
 * Pure functions over Float32Array, so they can be tested without audio.
 */

/** Two-pole resonant filter (RBJ biquad), band-pass or high-pass, applied in place. */
export function biquad(
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

export function noise(length: number, rand: () => number): Float32Array {
  const out = new Float32Array(length);
  for (let i = 0; i < length; i++) out[i] = rand() * 2 - 1;
  return out;
}

/** Adds `part` into `out` at `start` (seconds), shaped by an envelope. */
export function mix(
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

export function normalise(samples: Float32Array, peak = 0.9): Float32Array {
  let max = 0;
  for (const s of samples) max = Math.max(max, Math.abs(s));
  if (max > 0) for (let i = 0; i < samples.length; i++) samples[i] *= peak / max;
  return samples;
}

export const decay = (seconds: number) => (t: number) => Math.exp(-t / seconds);

/**
 * A bank of decaying resonant modes driven by `input`: what makes a knock sound
 * like teak, brass or glass rather than filtered noise. Each mode is
 * [frequency Hz, decay to 1/e in seconds, gain]; a one-sample impulse of 1
 * rings each mode at about its gain.
 */
export function modal(
  input: Float32Array,
  sampleRate: number,
  modes: readonly (readonly [number, number, number])[],
): Float32Array {
  const out = new Float32Array(input.length);
  for (const [f, d, g] of modes) {
    if (f >= sampleRate * 0.45) continue;
    const r = Math.exp(-1 / (d * sampleRate));
    const w = (2 * Math.PI * f) / sampleRate;
    const a1 = 2 * r * Math.cos(w),
      a2 = -r * r,
      b = g * Math.sin(w);
    let y1 = 0,
      y2 = 0;
    for (let i = 0; i < input.length; i++) {
      const y = b * input[i] + a1 * y1 + a2 * y2;
      y2 = y1;
      y1 = y;
      out[i] += y;
    }
  }
  return out;
}

/**
 * State-variable filter (topology-preserving, stable at any setting) whose
 * centre moves over time: wind rising, a squelch closing, a vowel changing.
 */
export function sweep(
  input: Float32Array,
  sampleRate: number,
  type: "lowpass" | "bandpass" | "highpass",
  frequency: (t: number) => number,
  q: number,
): Float32Array {
  const out = new Float32Array(input.length);
  const k = 1 / q;
  let s1 = 0,
    s2 = 0,
    a1 = 0,
    a2 = 0,
    a3 = 0;
  for (let i = 0; i < input.length; i++) {
    if ((i & 15) === 0) {
      const f = Math.min(sampleRate * 0.45, Math.max(10, frequency(i / sampleRate)));
      const g = Math.tan((Math.PI * f) / sampleRate);
      a1 = 1 / (1 + g * (g + k));
      a2 = g * a1;
      a3 = g * a2;
    }
    const v3 = input[i] - s2;
    const v1 = a1 * s1 + a2 * v3;
    const v2 = s2 + a2 * s1 + a3 * v3;
    s1 = 2 * v1 - s1;
    s2 = 2 * v2 - s2;
    out[i] = type === "lowpass" ? v2 : type === "bandpass" ? v1 : input[i] - k * v1 - v2;
  }
  return out;
}

/** Noise through parallel band-passes [frequency, bandwidth Hz, gain]: a vowel, a cavity. */
export function formant(
  input: Float32Array,
  sampleRate: number,
  formants: readonly (readonly [number, number, number])[],
): Float32Array {
  const out = new Float32Array(input.length);
  for (const [f, bandwidth, g] of formants) {
    const band = biquad(input.slice(), sampleRate, "bandpass", f, f / bandwidth);
    for (let i = 0; i < out.length; i++) out[i] += band[i] * g;
  }
  return out;
}

/**
 * Friction: something dragged that sticks and slips, a pulse each time it
 * lets go. `rate(t)` pulses a second, `pressure(t)` 0–1 scales each pulse;
 * `jitter` (0–1) roughens the spacing. Feed it through `modal` for a creak.
 */
export function stickSlip(
  length: number,
  sampleRate: number,
  rand: () => number,
  rate: (t: number) => number,
  pressure: (t: number) => number,
  jitter = 0.2,
): Float32Array {
  const out = new Float32Array(length);
  let phase = rand();
  for (let i = 0; i < length; i++) {
    const t = i / sampleRate;
    phase += rate(t) / sampleRate;
    if (phase >= 1) {
      phase = (rand() - 0.5) * jitter;
      out[i] = pressure(t) * (0.55 + 0.45 * rand());
    }
  }
  return out;
}

/** A small air bubble ringing as it forms (Minnaert): rain in a puddle, a drip in a jar, a glug. */
export function bubble(
  sampleRate: number,
  frequency: number,
  seconds: number,
  rise = 0.6,
): Float32Array {
  const n = Math.round(seconds * 2.5 * sampleRate);
  const out = new Float32Array(n);
  let phase = 0;
  for (let i = 0; i < n; i++) {
    const t = i / sampleRate;
    phase += (frequency * (1 + rise * (1 - Math.exp(-t / seconds)))) / sampleRate;
    out[i] = Math.sin(2 * Math.PI * phase) * (1 - Math.exp(-t / 0.0007)) * Math.exp(-t / seconds);
  }
  return out;
}

/** Brown (red) noise, leaky-integrated: the deep rumble under thunder, a train, a crowd of rain. */
export function brown(length: number, rand: () => number, leak = 0.995): Float32Array {
  const out = new Float32Array(length);
  let y = 0;
  for (let i = 0; i < length; i++) {
    y = y * leak + (rand() * 2 - 1) * 0.1;
    out[i] = y;
  }
  return out;
}

/** Saturation, as a carbon telephone microphone or an overdriven throat does. */
export function softClip(samples: Float32Array, drive: number): Float32Array {
  for (let i = 0; i < samples.length; i++) samples[i] = Math.tanh(samples[i] * drive);
  return samples;
}

/**
 * Wraps a loop: the last `fade` seconds are crossfaded into the first, and cut
 * off, so it repeats with no click and no dip in level.
 */
export function wrapLoop(out: Float32Array, sampleRate: number, fade: number): Float32Array {
  const n = Math.round(fade * sampleRate);
  const length = out.length - n;
  const loop = out.slice(0, length);
  for (let i = 0; i < n; i++) {
    const k = i / n;
    loop[i] = loop[i] * Math.sqrt(k) + out[length + i] * Math.sqrt(1 - k);
  }
  return loop;
}

/** Old teak floorboards: the modes a heavy step or a dragged weight sets ringing. */
function teakModes(rand: () => number, scale = 1): [number, number, number][] {
  return (
    [
      [96, 0.11, 1],
      [171, 0.08, 0.8],
      [287, 0.055, 0.7],
      [452, 0.04, 0.55],
      [706, 0.028, 0.45],
      [1130, 0.018, 0.34],
      [1810, 0.011, 0.24],
      [2870, 0.007, 0.16],
    ] as const
  ).map(([f, d, g]) => [f * scale * (0.93 + rand() * 0.14), d, g] as [number, number, number]);
}

/**
 * A wet, heavy, bare footstep on old teak with a drag: the Neak Ta shadow form
 * in the house (Audio Design Document, section 5). The heel lands soft and
 * heavy, the board rings and the joist under it groans, wet skin slaps, water
 * spatters off the cloth, and the foot drags before it lifts.
 */
export function wetStep(sampleRate: number, rand: () => number): Float32Array {
  const length = Math.round(0.5 * sampleRate);
  const out = new Float32Array(length);
  const at = (s: number) => Math.round(s * sampleRate);
  // The heel: flesh, not a shoe, so a soft low body whose pitch sags as the board gives.
  const pitch = 62 + rand() * 18;
  let phase = 0;
  for (let i = 0; i < at(0.16); i++) {
    const t = i / sampleRate;
    phase += (pitch * (1 + 0.7 * Math.exp(-t / 0.01))) / sampleRate;
    out[i] +=
      Math.sin(2 * Math.PI * phase) * (1 - Math.exp(-t / 0.002)) * Math.exp(-t / 0.055) * 0.9;
  }
  // The board rings where it was struck.
  const strike = new Float32Array(length);
  for (let i = 0; i < at(0.004); i++) strike[i] = (rand() * 2 - 1) * Math.exp(-i / at(0.0012));
  const ring = modal(strike, sampleRate, teakModes(rand));
  for (let i = 0; i < length; i++) out[i] += ring[i] * 2.4;
  // Wet skin on wood: a bright, very short slap (the onset the ear places it by).
  const slap = biquad(noise(at(0.05), rand), sampleRate, "highpass", 1900, 0.7);
  mix(out, slap, sampleRate, 0.002, 1.3, decay(0.016));
  const smack = biquad(noise(at(0.03), rand), sampleRate, "bandpass", 4200 + rand() * 1500, 1.2);
  mix(out, smack, sampleRate, 0.004, 0.9, decay(0.007));
  // Water squeezed out of the cloth, spattering a moment after.
  for (let k = 3 + Math.floor(rand() * 4); k > 0; k--) {
    const drop = bubble(sampleRate, 1400 + rand() * 2400, 0.004 + rand() * 0.004, 0.9);
    mix(out, drop, sampleRate, 0.025 + rand() * 0.14, 0.05 + rand() * 0.09, () => 1);
  }
  // The drag: wet cloth sliding on the boards, sticking and slipping.
  const dragAt = 0.08 + rand() * 0.03,
    dragFor = 0.24 + rand() * 0.07;
  const grip = stickSlip(
    at(dragFor),
    sampleRate,
    rand,
    (t) => 180 + 260 * (t / dragFor),
    (t) => Math.sin((Math.PI * t) / dragFor),
    0.6,
  );
  const scrape = modal(grip, sampleRate, teakModes(rand, 2.1));
  const cloth = biquad(noise(at(dragFor), rand), sampleRate, "bandpass", 720, 0.8);
  for (let i = 0; i < cloth.length; i++) {
    const t = i / sampleRate;
    cloth[i] = cloth[i] * 0.35 * Math.sin((Math.PI * t) / dragFor) ** 1.5 + scrape[i] * 0.9;
  }
  mix(out, cloth, sampleRate, dragAt, 0.5, () => 1);
  // The joist below takes the weight: a slow, low groan.
  const groanFor = 0.26;
  const groan = modal(
    stickSlip(
      at(groanFor),
      sampleRate,
      rand,
      (t) => 38 + 30 * (t / groanFor),
      (t) => Math.sin((Math.PI * t) / groanFor) ** 2,
      0.3,
    ),
    sampleRate,
    [
      [340 + rand() * 60, 0.03, 1],
      [610 + rand() * 80, 0.022, 0.6],
      [1020 + rand() * 120, 0.015, 0.35],
    ],
  );
  mix(out, groan, sampleRate, 0.06, 0.55, () => 1);
  return normalise(out);
}

/**
 * A slow, wet breath with a rattle on the exhale, about 1.6 s: the shadow
 * form's signature (Audio Design Document, section 5). Air drawn in through a
 * slack mouth, then let out through a throat full of water: the tract's
 * formants, wet crackles bursting in the airway, and a low fry under it.
 */
export function rattlingBreath(sampleRate: number, rand: () => number): Float32Array {
  const length = Math.round(1.6 * sampleRate);
  const out = new Float32Array(length);
  // A big tract: formants lower than a person's.
  const inhale = formant(noise(length, rand), sampleRate, [
    [640, 260, 0.8],
    [1500, 360, 0.6],
    [2700, 500, 0.4],
    [5200, 1800, 0.25],
  ]);
  const exhale = formant(noise(length, rand), sampleRate, [
    [430, 160, 1],
    [930, 220, 0.7],
    [2150, 380, 0.35],
  ]);
  const flutter = biquad(noise(length, rand), sampleRate, "lowpass", 30, 0.7);
  let flutterPeak = 1e-6;
  for (const f of flutter) flutterPeak = Math.max(flutterPeak, Math.abs(f));
  for (let i = 0; i < length; i++) {
    const t = i / sampleRate;
    const draw = t < 0.62 ? Math.sin((t / 0.62) * Math.PI) ** 1.3 * 0.45 : 0;
    const out_ = t >= 0.68 ? Math.sin(((t - 0.68) / 0.92) * Math.PI) ** 0.8 : 0;
    // The airway flaps irregularly as the wet air pushes past.
    const flap = 0.7 + 0.3 * (flutter[i] / flutterPeak);
    out[i] = inhale[i] * draw + exhale[i] * out_ * flap;
  }
  // Crackles: bubbles of fluid bursting, clustered through the exhale.
  const crackles = new Float32Array(length);
  for (let i = Math.round(0.72 * sampleRate); i < Math.round(1.55 * sampleRate); i++) {
    const t = i / sampleRate;
    const density = 55 * Math.sin(((t - 0.68) / 0.92) * Math.PI);
    if (rand() < density / sampleRate) crackles[i] = (rand() < 0.5 ? -1 : 1) * (0.4 + rand() * 0.6);
  }
  const wet = modal(crackles, sampleRate, [
    [290 + rand() * 60, 0.009, 1],
    [540 + rand() * 90, 0.007, 0.8],
    [910 + rand() * 120, 0.005, 0.6],
    [1500, 0.003, 0.4],
  ]);
  for (let i = 0; i < length; i++) out[i] += wet[i] * 0.55;
  // A low fry under the exhale: the throat almost voicing, never words.
  const fry = stickSlip(
    length,
    sampleRate,
    rand,
    () => 34 + rand() * 6,
    (t) => (t >= 0.75 && t < 1.5 ? Math.sin(((t - 0.75) / 0.75) * Math.PI) : 0),
    0.5,
  );
  const fryVoice = formant(fry, sampleRate, [
    [430, 120, 1],
    [930, 180, 0.5],
  ]);
  for (let i = 0; i < length; i++) out[i] += fryVoice[i] * 1.6;
  return normalise(out, 0.6);
}

/**
 * A teak board groaning under weight, about 0.7 s: stick-slip friction where
 * the board rubs its nail and its neighbour, rising in pitch as the weight
 * comes on and sagging as it eases, through the plank's own resonances.
 */
export function boardCreak(sampleRate: number, rand: () => number): Float32Array {
  const length = Math.round(0.7 * sampleRate);
  const base = 48 + rand() * 40;
  const lift = 1.8 + rand() * 1.6;
  const peakAt = 0.35 + rand() * 0.3;
  const grip = stickSlip(
    length,
    sampleRate,
    rand,
    (t) => {
      const u = t / 0.7;
      const bend = u < peakAt ? u / peakAt : 1 - (u - peakAt) / (1 - peakAt);
      return base * (1 + (lift - 1) * Math.sin((bend * Math.PI) / 2));
    },
    (t) => Math.sin((Math.PI * t) / 0.7) ** 0.8,
    0.25,
  );
  // The grain catches now and then: a louder pop.
  for (let k = 0; k < 3; k++) grip[Math.floor((0.1 + rand() * 0.5) * sampleRate)] = 1.6;
  const s = 0.9 + rand() * 0.2;
  const out = modal(grip, sampleRate, [
    [430 * s, 0.03, 1],
    [690 * s, 0.026, 0.85],
    [1120 * s, 0.02, 0.65],
    [1640 * s, 0.014, 0.5],
    [2480 * s, 0.009, 0.32],
    [3600 * s, 0.005, 0.18],
  ]);
  const rub = biquad(noise(length, rand), sampleRate, "bandpass", 1400, 1);
  for (let i = 0; i < length; i++) out[i] += rub[i] * 0.025 * Math.sin((Math.PI * i) / length);
  return normalise(out, 0.45);
}

/**
 * The suck and release of a foot lifting out of wet mud, about 0.32 s: laid
 * over a damped step on the mud surface (Audio Design Document 4.1, "suction").
 * A squelch whose resonance falls as the mud closes, then small bubbles popping.
 */
export function mudSuction(sampleRate: number, rand: () => number): Float32Array {
  const length = Math.round(0.32 * sampleRate);
  const out = new Float32Array(length);
  const source = noise(length, rand);
  const start = 0.02 + rand() * 0.03;
  // State-variable band-pass, its centre falling from about 1.2 kHz to 300 Hz.
  let low = 0,
    band = 0;
  for (let i = 0; i < length; i++) {
    const u = i / sampleRate - start;
    if (u < 0) continue;
    const f = 300 + 900 * Math.exp(-u / 0.05);
    const fc = 2 * Math.sin((Math.PI * f) / sampleRate);
    low += fc * band;
    const high = source[i] - low - 0.25 * band;
    band += fc * high;
    out[i] = band * (1 - Math.exp(-u / 0.008)) * Math.exp(-u / 0.07);
  }
  // The release: two or three bubbles, each a short tone rising as it bursts.
  const pops = 2 + Math.floor(rand() * 2);
  for (let k = 0; k < pops; k++) {
    const at = Math.round((0.12 + rand() * 0.13) * sampleRate);
    const f0 = 450 + rand() * 500;
    const gain = 0.2 + rand() * 0.2;
    const n = Math.round(0.03 * sampleRate);
    let phase = 0;
    for (let j = 0; j < n && at + j < length; j++) {
      const t = j / sampleRate;
      phase += (f0 * (1 + (t / 0.03) * 0.8)) / sampleRate;
      // A soft onset: a hard one clicks.
      const envelope = (1 - Math.exp(-t / 0.002)) * Math.exp(-t / 0.008);
      out[at + j] += Math.sin(2 * Math.PI * phase) * gain * envelope;
    }
  }
  biquad(out, sampleRate, "lowpass", 2800, 0.7);
  return normalise(out, 0.8);
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
