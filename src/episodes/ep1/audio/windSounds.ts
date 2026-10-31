import {
  biquad,
  brown,
  modal,
  noise,
  normalise,
  rms,
  stickSlip,
  sweep,
  wrapLoop,
} from "../../../audio/synth";
import { gustEnvelope } from "../../../render/wind";

/**
 * The monsoon wind, synthesised until recordings exist (Audio Design Document,
 * section 9): beds WindAudio rides with the wind's strength, one gust heard
 * as its front passes, and the forest answering it, tree by tree. Mono, at
 * `rate`; beds are seamless loops, the rest one-shots.
 */

/** A smooth random control signal, 0–1, changing about `hz` times a second. */
function wander(length: number, rate: number, random: () => number, hz: number): Float32Array {
  const step = Math.max(1, Math.round(rate / hz));
  const knots = Array.from({ length: Math.ceil(length / step) + 2 }, () => random());
  const out = new Float32Array(length);
  for (let i = 0; i < length; i++) {
    const k = Math.floor(i / step);
    const f = (i % step) / step;
    const s = f * f * (3 - 2 * f);
    out[i] = knots[k] * (1 - s) + knots[k + 1] * s;
  }
  return out;
}

/** Scales a layer to an RMS level, so layers of very different bandwidths mix as intended. */
function level(samples: Float32Array, target: number): Float32Array {
  const r = rms(samples);
  if (r > 0) for (let i = 0; i < samples.length; i++) samples[i] *= target / r;
  return samples;
}

/** The air moving through the forest: a deep, breathing roar under everything (loop, ~13 s). */
export function windRoar(rate: number, random: () => number): Float32Array {
  const n = Math.round(rate * 14);
  const deep = level(biquad(brown(n, random, 0.997), rate, "lowpass", 150, 0.7), 1);
  const phase = random() * Math.PI * 2;
  const body = level(
    sweep(noise(n, random), rate, "bandpass", (t) => 320 + 110 * Math.sin(t * 0.45 + phase), 0.9),
    0.45,
  );
  const breath = wander(n, rate, random, 0.4);
  const out = new Float32Array(n);
  for (let i = 0; i < n; i++) out[i] = (deep[i] + body[i]) * (0.78 + 0.22 * breath[i]);
  return normalise(wrapLoop(out, rate, 1.2), 0.5);
}

/** Wet leaves by the thousand, catching and letting go: the canopy's hiss (loop, ~10 s). */
export function leafHiss(rate: number, random: () => number): Float32Array {
  const n = Math.round(rate * 11);
  const hiss = biquad(
    biquad(noise(n, random), rate, "highpass", 1700, 0.7),
    rate,
    "bandpass",
    4200,
    0.55,
  );
  const flicker = wander(n, rate, random, 9);
  const slow = wander(n, rate, random, 0.7);
  for (let i = 0; i < n; i++) hiss[i] *= 0.35 + 0.65 * flicker[i] ** 2 * (0.6 + 0.4 * slow[i]);
  return normalise(wrapLoop(hiss, rate, 1), 0.45);
}

/** Seconds of a gust swell, and where its height falls (it follows `gustEnvelope`). */
export const GUST_SECONDS = 6.5;

/**
 * One gust as its front passes: the air's band climbs and falls back, the
 * leaves answer a beat behind, and a thin howl rides the top of it.
 */
export function gustSwell(rate: number, random: () => number): Float32Array {
  const n = Math.round(rate * GUST_SECONDS);
  const env = (t: number) => gustEnvelope(t / GUST_SECONDS);
  const air = level(
    sweep(noise(n, random), rate, "bandpass", (t) => 240 + 620 * env(t), 0.8),
    1,
  );
  const leaves = level(biquad(noise(n, random), rate, "highpass", 2400, 0.7), 0.5);
  const flicker = wander(n, rate, random, 11);
  const pitch = 470 + random() * 140;
  const howl = level(
    sweep(
      noise(n, random),
      rate,
      "bandpass",
      (t) => pitch + 240 * env(t) + 22 * Math.sin(t * 3.1),
      16,
    ),
    0.32,
  );
  const out = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const t = i / rate,
      e = env(t);
    out[i] = air[i] * e + leaves[i] * env(t - 0.3) * (0.4 + 0.6 * flicker[i]) + howl[i] * e * e;
  }
  return normalise(out, 0.8);
}

/** A trunk taking the gust's weight: a slow, low groan of wood fibre (~2.8 s). */
export function trunkGroan(rate: number, random: () => number): Float32Array {
  const seconds = 2.4 + random() * 0.8;
  const n = Math.round(rate * seconds);
  const start = 14 + random() * 8;
  const pulses = stickSlip(
    n,
    rate,
    random,
    (t) => start + 26 * (t / seconds),
    (t) => Math.sin((Math.PI * t) / seconds) ** 0.7,
    0.35,
  );
  const scale = 0.85 + random() * 0.3;
  const wood = modal(pulses, rate, [
    [88 * scale, 0.07, 1],
    [151 * scale, 0.05, 0.8],
    [247 * scale, 0.035, 0.55],
    [395 * scale, 0.022, 0.35],
    [640 * scale, 0.014, 0.2],
  ]);
  return normalise(wood, 0.7);
}

/** Bamboo culms knocking together, and the squeal of two rubbing in the grove (~3 s). */
export function bambooKnock(rate: number, random: () => number): Float32Array {
  const n = Math.round(rate * 3);
  const hits = new Float32Array(n);
  let at = 0.1 + random() * 0.2;
  const count = 3 + Math.floor(random() * 4);
  for (let k = 0; k < count && at < 2.6; k++) {
    hits[Math.round(at * rate)] = 0.5 + 0.5 * random();
    // Culms swing back together: knocks come in quick doubles.
    if (random() < 0.6) hits[Math.round((at + 0.05 + random() * 0.07) * rate)] = 0.3 * random();
    at += 0.25 + random() * 0.55;
  }
  const culm = 0.8 + random() * 0.45;
  const knocks = modal(hits, rate, [
    [420 * culm, 0.06, 1],
    [1030 * culm, 0.035, 0.6],
    [1710 * culm, 0.02, 0.4],
    [2650 * culm, 0.012, 0.25],
  ]);
  const rubFrom = 0.4 + random() * 1.4,
    rubLength = 0.5 + random() * 0.5;
  const rub = biquad(
    stickSlip(
      n,
      rate,
      random,
      (t) => 170 + 90 * Math.sin((t - rubFrom) * 4),
      (t) =>
        t < rubFrom || t > rubFrom + rubLength
          ? 0
          : Math.sin((Math.PI * (t - rubFrom)) / rubLength),
      0.3,
    ),
    rate,
    "bandpass",
    950 * culm,
    5,
  );
  level(rub, rms(knocks) * 0.8);
  for (let i = 0; i < n; i++) knocks[i] += rub[i];
  return normalise(knocks, 0.75);
}

/** Palm fronds and banana leaves: a dry clatter and the heavy flap of big leaves (~3.2 s). */
export function frondClatter(rate: number, random: () => number): Float32Array {
  const seconds = 3.2;
  const n = Math.round(rate * seconds);
  const env = (t: number) => Math.sin((Math.PI * t) / seconds) ** 1.5;
  const ticks = new Float32Array(n);
  for (let t = random() * 0.01; t < seconds; t += 0.002 + random() * 0.006)
    ticks[Math.round(t * rate)] = (random() - 0.5) * env(t);
  const clatter = level(biquad(ticks, rate, "bandpass", 3600, 0.8), 1);
  const flaps = new Float32Array(n);
  for (let k = 0, at = 0.2 + random() * 0.3; k < 5 && at < seconds - 0.4; k++) {
    const len = Math.round((0.18 + random() * 0.2) * rate);
    const part = biquad(noise(len, random), rate, "bandpass", 260 + random() * 160, 1.4);
    const start = Math.round(at * rate);
    for (let i = 0; i < len && start + i < n; i++)
      flaps[start + i] += part[i] * Math.sin((Math.PI * i) / len) ** 2;
    at += 0.35 + random() * 0.5;
  }
  level(flaps, 0.8);
  for (let i = 0; i < n; i++) clatter[i] += flaps[i];
  return normalise(clatter, 0.7);
}

/** One crown thrashing as the gust reaches it (~3.5 s). */
export function crownRustle(rate: number, random: () => number): Float32Array {
  const seconds = 3 + random();
  const n = Math.round(rate * seconds);
  const leaves = biquad(noise(n, random), rate, "bandpass", 2300 + random() * 900, 0.6);
  const flicker = wander(n, rate, random, 14);
  for (let i = 0; i < n; i++) {
    const t = i / rate;
    leaves[i] *= Math.sin((Math.PI * t) / seconds) ** 1.5 * (0.3 + 0.7 * flicker[i]);
  }
  return normalise(leaves, 0.65);
}

/** A gust striking the taxi: the body thumps, the door seals whistle, the glass buzzes (~5 s). */
export function carBuffet(rate: number, random: () => number): Float32Array {
  const seconds = 5;
  const n = Math.round(rate * seconds);
  const env = (t: number) => gustEnvelope(t / seconds);
  const body = level(biquad(brown(n, random, 0.996), rate, "lowpass", 70, 0.8), 1);
  const seal = level(
    sweep(noise(n, random), rate, "bandpass", (t) => 1150 + 380 * env(t), 18),
    0.22,
  );
  const ticks = new Float32Array(n);
  for (let t = 0; t < seconds; t += 0.012 + random() * 0.05)
    if (random() < env(t)) ticks[Math.round(t * rate)] = random() - 0.5;
  const glass = level(
    modal(ticks, rate, [
      [2300, 0.012, 1],
      [3150, 0.009, 0.6],
    ]),
    0.18,
  );
  const out = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const e = env(i / rate);
    out[i] = body[i] * e + seal[i] * e * e + glass[i];
  }
  return normalise(out, 0.8);
}
