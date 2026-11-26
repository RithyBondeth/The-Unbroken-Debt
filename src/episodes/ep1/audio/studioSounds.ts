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

/** About 1.6 s: soft organic breath close behind her, without choppy static. */
export function whisper(rate: number, rand: () => number): Float32Array {
  const length = n(1.6, rate);
  const air = formant(noise(length, rand), rate, [
    [480 + rand() * 120, 190, 0.75],
    [1280 + rand() * 220, 280, 1],
    [2350, 420, 0.45],
  ]);
  const out = new Float32Array(length);
  const phrases: [number, number, number][] = [
    [0.12, 0.42, 0.8],
    [0.58, 0.48, 1.0],
    [1.12, 0.36, 0.65],
  ];
  for (let i = 0; i < length; i++) {
    const t = i / rate;
    let env = 0;
    for (const [start, dur, amp] of phrases) {
      if (t >= start && t <= start + dur) {
        env += amp * Math.sin(((t - start) / dur) * Math.PI) ** 1.4;
      }
    }
    out[i] = air[i] * env;
  }
  biquad(out, rate, "highpass", 380, 0.7);
  biquad(out, rate, "lowpass", 3200, 0.7);
  return normalise(out, 0.62);
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
    const snap = biquad(noise(n(0.04, rate), rand), rate, "bandpass", 1800, 1.2);
    mix(out, snap, rate, when, 0.7, decay(0.01));
    const relay = modal(impulse(rate, 0.09), rate, [
      [260, 0.03, 1],
      [920, 0.018, 0.65],
      [1840, 0.012, 0.35],
    ]);
    mix(out, relay, rate, when, 0.75, () => 1);
    const hum = new Float32Array(n(0.1, rate));
    for (let i = 0; i < hum.length; i++) {
      const t = i / rate;
      hum[i] = Math.sin(2 * Math.PI * 50 * t) * 0.7 + Math.sin(2 * Math.PI * 100 * t) * 0.3;
    }
    mix(out, hum, rate, when, 0.22, decay(0.045));
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

/** About 0.28 s: crisp brass doorknob & mortise latch release click. */
export function doorLatch(rate: number, rand: () => number): Float32Array {
  const out = new Float32Array(n(0.28, rate));
  const s = 0.96 + rand() * 0.08;
  for (const [at, g, pitch] of [
    [0.0, 0.85, 1.0],
    [0.055, 0.65, 1.18],
  ] as const) {
    mix(
      out,
      modal(impulse(rate, 0.12), rate, [
        [680 * s * pitch, 0.016, 0.7],
        [1640 * s * pitch, 0.014, 1.0],
        [3120 * s * pitch, 0.009, 0.55],
      ]),
      rate,
      at,
      g,
      () => 1,
    );
  }
  return normalise(out, 0.72);
}

/** About 0.55 s: solid teak door shutting into its jamb with a latched brass catch. */
export function doorClose(rate: number, rand: () => number): Float32Array {
  const out = new Float32Array(n(0.55, rate));
  const s = 0.94 + rand() * 0.12;
  mix(
    out,
    modal(impulse(rate, 0.4), rate, [
      [92 * s, 0.085, 1.0],
      [185 * s, 0.05, 0.72],
      [390 * s, 0.025, 0.4],
    ]),
    rate,
    0,
    1.0,
    () => 1,
  );
  mix(
    out,
    biquad(noise(n(0.14, rate), rand), rate, "lowpass", 820, 0.7),
    rate,
    0,
    0.55,
    decay(0.032),
  );
  mix(out, doorLatch(rate, rand), rate, 0.045, 0.55, () => 1);
  return normalise(out, 0.88);
}
