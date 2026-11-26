import {
  biquad,
  boardCreak,
  decay,
  formant,
  mix,
  modal,
  noise,
  normalise,
  sweep,
} from "@/audio/synth";
import { POWER_RETURN } from "../data/powerCut";

/**
 * The house in sound between and under the studio's scares (November 2026; the dancer
 * ghost these were made for is gone, StudioScares.ts has the scares). Synthesised, mono,
 * pure functions like the rest of the prologue's stand-ins.
 *
 * - `heartbeat`: Sora's own heart after the altar falls, until she answers the telephone.
 * - `whisper`, `knock`, `creak`: the house between: someone breathing words just
 *   behind her, three slow knocks in the back room, a board taking a weight.
 * - `powerDown`, `powerUp`: every light dying after the altar falls, and catching again.
 */

const n = (s: number, rate: number) => Math.round(s * rate);

/** 1.2 s loop of a frightened heart: lub-dub, about 100 a minute, felt more than heard. */
export function heartbeat(rate: number): Float32Array {
  const length = n(0.6, rate);
  const out = new Float32Array(length);
  const beat = (at: number, gain: number, f: number) => {
    let ph = 0;
    for (let i = n(at, rate); i < length; i++) {
      const t = i / rate - at;
      ph += (2 * Math.PI * f * (1 + 0.6 * Math.exp(-t / 0.02))) / rate;
      out[i] += Math.sin(ph) * gain * Math.exp(-t / 0.06) * Math.min(1, t / 0.004);
    }
  };
  beat(0.0, 1, 52);
  beat(0.17, 0.7, 64);
  return normalise(out, 0.85);
}

/** About 1.6 s: someone breathing words behind her, too low to make out. */
export function whisper(rate: number, rand: () => number): Float32Array {
  const length = n(1.6, rate);
  const syllables = formant(noise(length, rand), rate, [
    [520 + rand() * 200, 160, 0.6],
    [1500 + rand() * 300, 260, 1],
    [2900, 400, 0.6],
    [5200, 900, 0.3],
  ]);
  const rateS = 4.2 + rand() * 1.5;
  const out = new Float32Array(length);
  for (let i = 0; i < length; i++) {
    const t = i / rate;
    const syl = Math.max(0, Math.sin(2 * Math.PI * rateS * t + rand() * 0.3)) ** 1.6;
    const shape = Math.sin((Math.PI * t) / 1.6) ** 0.7;
    out[i] = syllables[i] * syl * shape;
  }
  biquad(out, rate, "highpass", 700, 0.7);
  return normalise(out, 0.7);
}

/** Three slow knocks on a teak board in the dark, about 2.2 s. */
export function knock(rate: number, rand: () => number): Float32Array {
  const length = n(2.2, rate);
  const out = new Float32Array(length);
  [0, 0.62, 1.38].forEach((at, k) => {
    const hit = new Float32Array(n(0.4, rate));
    for (let i = 0; i < n(0.003, rate); i++) hit[i] = 1 - i / n(0.003, rate);
    const s = 0.95 + rand() * 0.1;
    const wood = modal(hit, rate, [
      [118 * s, 0.09, 1],
      [242 * s, 0.05, 0.6],
      [410 * s, 0.03, 0.4],
      [690 * s, 0.015, 0.25],
    ]);
    mix(out, wood, rate, at, k === 2 ? 1 : 0.8, () => 1);
  });
  return normalise(out, 0.85);
}

/** A board taking a weight somewhere in the dark (synth's teak creak). */
export function creak(rate: number, rand: () => number): Float32Array {
  return boardCreak(rate, rand);
}

/**
 * Every light in the house dies at once (the altar has just fallen): a relay's
 * metal clunk and a sub blow, the air sucked out of the rooms, then in the dark breath at
 * the ear and the boards groaning slow and low.
 */
export function powerDown(rate: number, rand: () => number): Float32Array {
  const out = new Float32Array(n(2.2, rate));
  const impulse = new Float32Array(n(0.4, rate));
  impulse[0] = 1;
  mix(
    out,
    modal(impulse, rate, [
      [182, 0.07, 1],
      [1250, 0.025, 0.8],
      [2310, 0.016, 0.55],
      [3870, 0.01, 0.4],
    ]),
    rate,
    0,
    0.9,
    () => 1,
  );
  const sub = new Float32Array(n(1.1, rate));
  let ph = 0;
  for (let i = 0; i < sub.length; i++) {
    const t = i / rate;
    ph += (2 * Math.PI * (32 + 40 * Math.exp(-t / 0.06))) / rate;
    sub[i] = Math.sin(ph);
  }
  mix(out, sub, rate, 0, 1.2, decay(0.5));
  const air = sweep(
    noise(n(0.7, rate), rand),
    rate,
    "lowpass",
    (t) => 3200 * Math.exp(-t / 0.18) + 150,
    0.9,
  );
  mix(out, air, rate, 0.01, 0.5, decay(0.25));
  mix(out, whisper(rate, rand), rate, 0.35, 0.5, () => 1);
  const groan = creak(rate, rand);
  const slow = new Float32Array(groan.length * 2);
  for (let i = 0; i < slow.length; i++) slow[i] = groan[Math.floor(i / 2)];
  mix(out, biquad(slow, rate, "lowpass", 900, 0.7), rate, 0.9, 0.7, () => 1);
  return normalise(out, 0.92);
}

/**
 * The lights catching again (the end of POWER_CUT, played from POWER_RETURN): a hiss
 * rising out of nothing, then an electric crack and a burst of mains buzz each time they
 * catch.
 */
export function powerUp(rate: number, rand: () => number): Float32Array {
  const out = new Float32Array(n(0.9, rate));
  const swell = biquad(noise(n(0.08, rate), rand), rate, "bandpass", 3800, 0.6);
  mix(out, swell, rate, 0, 0.4, (t) => (t / 0.08) ** 3);
  for (const at of [1.28, 1.47, 1.72]) {
    const when = at - POWER_RETURN;
    const snap = biquad(noise(n(0.05, rate), rand), rate, "highpass", 2200, 0.7);
    mix(out, snap, rate, when, 0.8, decay(0.012));
    const buzz = new Float32Array(n(0.08, rate));
    for (let i = 0; i < buzz.length; i++) {
      const t = i / rate;
      buzz[i] = ((t * 100) % 1) * 2 - 1;
    }
    mix(out, biquad(buzz, rate, "lowpass", 1800, 0.7), rate, when, 0.35, decay(0.03));
  }
  return normalise(out, 0.85);
}

// ------------------------------------------------- the scares' stand-ins
// Played only while the real recordings (sfx_ep1_studio_*, made from CC0 Freesound files)
// are missing: StudioScares.ts loads those first.

/** A single struck impulse `seconds` long, for modal(). */
function impulse(rate: number, seconds: number): Float32Array {
  const out = new Float32Array(n(seconds, rate));
  out[0] = 1;
  return out;
}

/**
 * About 1.4 s: something brittle smashing on the tiles, a thump and a spray of pieces
 * skittering away. `bright` raises the pieces' ring (1 pottery, 1.8 glass).
 */
export function smash(rate: number, rand: () => number, bright = 1): Float32Array {
  const out = new Float32Array(n(1.4, rate));
  mix(
    out,
    modal(impulse(rate, 0.3), rate, [
      [150, 0.05, 1],
      [410, 0.03, 0.6],
    ]),
    rate,
    0,
    0.8,
    () => 1,
  );
  mix(
    out,
    biquad(noise(n(0.25, rate), rand), rate, "highpass", 1500 * bright, 0.7),
    rate,
    0,
    1,
    decay(0.04),
  );
  for (let i = 0; i < 70; i++) {
    const at = 0.004 + rand() ** 2 * 0.9;
    const f = (2200 + rand() * 5000) * bright;
    const ping = modal(impulse(rate, 0.12), rate, [
      [f, 0.012 + rand() * 0.03, 1],
      [f * (1.6 + rand() * 0.4), 0.008, 0.5],
    ]);
    mix(out, ping, rate, at, (1 - at / 1.1) * (0.2 + rand() * 0.6), () => 1);
  }
  return normalise(out, 0.95);
}

/** About 1.6 s: brass on tiles, a clang and two smaller bounces, then a rattle settling. */
export function clang(rate: number, rand: () => number): Float32Array {
  const out = new Float32Array(n(1.6, rate));
  const s = 0.95 + rand() * 0.1;
  const ring = (gain: number) =>
    modal(impulse(rate, 1.2), rate, [
      [820 * s, 0.35, 1],
      [1935 * s, 0.22, 0.7],
      [3120 * s, 0.14, 0.45],
      [4660 * s, 0.08, 0.3],
    ]).map((v) => v * gain);
  [0, 0.21, 0.34, 0.41, 0.45].forEach((at, k) =>
    mix(out, ring(1 / (1 + k * 1.3)), rate, at, 1, () => 1),
  );
  return normalise(out, 0.9);
}

/** About 0.8 s: a bracket's screws tearing out of the plaster and the wood splitting. */
export function tear(rate: number, rand: () => number): Float32Array {
  const out = new Float32Array(n(0.8, rate));
  for (let i = 0; i < 26; i++) {
    const at = rand() ** 1.5 * 0.35;
    const burst = biquad(noise(n(0.03, rate), rand), rate, "bandpass", 700 + rand() * 2200, 1.5);
    mix(out, burst, rate, at, 0.4 + rand() * 0.6, decay(0.006));
  }
  mix(
    out,
    modal(impulse(rate, 0.5), rate, [
      [95, 0.09, 1],
      [230, 0.05, 0.6],
    ]),
    rate,
    0.36,
    1,
    () => 1,
  );
  mix(
    out,
    biquad(noise(n(0.5, rate), rand), rate, "lowpass", 1200, 0.7),
    rate,
    0.36,
    0.5,
    decay(0.12),
  );
  return normalise(out, 0.95);
}

/** About 2.5 s: a bowl dropped on its rim, spinning down faster and faster to rest. */
export function bowlSpin(rate: number, rand: () => number): Float32Array {
  const out = new Float32Array(n(2.5, rate));
  mix(
    out,
    modal(impulse(rate, 0.4), rate, [
      [340, 0.06, 1],
      [780, 0.04, 0.5],
    ]),
    rate,
    0,
    1,
    () => 1,
  );
  let t = 0.25,
    gap = 0.16;
  while (t < 2.4 && gap > 0.012) {
    const tick = modal(impulse(rate, 0.05), rate, [[1100 + rand() * 200, 0.01, 1]]);
    mix(out, tick, rate, t, 0.35 * (1 - t / 2.6), () => 1);
    t += gap;
    gap *= 0.9;
  }
  return normalise(out, 0.85);
}

/** About 0.5 s: a small piece of wood dropped on tiles. */
export function thud(rate: number, rand: () => number): Float32Array {
  const out = new Float32Array(n(0.5, rate));
  const s = 0.9 + rand() * 0.2;
  mix(
    out,
    modal(impulse(rate, 0.5), rate, [
      [210 * s, 0.05, 1],
      [520 * s, 0.03, 0.6],
      [1300 * s, 0.015, 0.3],
    ]),
    rate,
    0,
    1,
    () => 1,
  );
  return normalise(out, 0.8);
}
