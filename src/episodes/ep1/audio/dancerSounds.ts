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
  wrapLoop,
} from "@/audio/synth";
import { POWER_RETURN } from "../data/powerCut";

/**
 * The studio's ghost in sound (November 2026): the dancer ghost in Sora's back
 * room (DancerGhost.ts). Synthesised, mono, pure functions like the rest of the
 * prologue's stand-ins.
 *
 * - `pinpeatLure`: a robam's melody on a roneat ek, faint and warped, as if a
 *   gramophone played behind the back room's wall. It is there from the start,
 *   placed in the back room, and stops dead when she appears.
 * - `robamSong`: the same music played close while she dances, cut off when she goes.
 * - `heartbeat`: Sora's own heart after it, until she answers the telephone.
 * - `whisper`, `knock`, `creak`: the house between: someone breathing words just
 *   behind her, three slow knocks in the back room, a board taking a weight.
 */

const n = (s: number, rate: number) => Math.round(s * rate);

/** A struck tuned bar (roneat key, bamboo or hardwood): the bar's inharmonic modes. */
function roneatKey(rate: number, rand: () => number, f: number): Float32Array {
  const length = n(0.9, rate);
  const strike = new Float32Array(length);
  // The padded beater: a short soft pulse, not a click.
  for (let i = 0; i < n(0.004, rate); i++) strike[i] = Math.sin((Math.PI * i) / n(0.004, rate));
  const wood = 0.97 + rand() * 0.06;
  return modal(strike, rate, [
    [f, 0.32, 1],
    [f * 3.93 * wood, 0.08, 0.38],
    [f * 9.3 * wood, 0.025, 0.16],
    [f * 0.5, 0.12, 0.05],
  ]);
}

/** Khmer pentatonic degrees as semitones above the tonic (approximately; the real tuning is its own). */
const SCALE = [0, 2, 4, 7, 9, 12, 14, 16];

/**
 * About 14 s, looping: a slow robam phrase, each note struck twice in the roneat's
 * tremolo, played through a wall and a worn record: band-limited, wavering in pitch,
 * with surface crackle and the room's hiss under it.
 */
export function pinpeatLure(rate: number, rand: () => number): Float32Array {
  const total = 14;
  const out = new Float32Array(n(total, rate));
  const tonic = 392;
  // Notes as scale degrees; the phrase climbs, hangs, and falls back.
  const phrase = [4, 3, 4, 5, 4, 3, 1, 2, 3, 2, 1, 0, 1, 3, 2, 1, 0, 0];
  const step = (total - 1.6) / phrase.length;
  phrase.forEach((degree, k) => {
    const f = tonic * 2 ** (SCALE[degree] / 12);
    const start = 0.3 + k * step + (rand() - 0.5) * 0.04;
    // Tremolo: the note repeated fast, softer after the first.
    for (let r = 0; r < 3; r++)
      mix(out, roneatKey(rate, rand, f), rate, start + r * 0.11, r ? 0.45 : 0.8, () => 1);
    // The lower roneat doubling every other note an octave down.
    if (k % 2 === 0) mix(out, roneatKey(rate, rand, f / 2), rate, start, 0.35, () => 1);
  });
  // A worn record: the pitch wavers (read back at a slowly drifting speed).
  const warped = new Float32Array(out.length);
  let pos = 0;
  for (let i = 0; i < out.length; i++) {
    const t = i / rate;
    const speed =
      1 + 0.012 * Math.sin(2 * Math.PI * 0.55 * t) + 0.006 * Math.sin(2 * Math.PI * 1.7 * t + 1);
    pos = Math.min(out.length - 2, pos + speed);
    const a = Math.floor(pos);
    warped[i] = out[a] + (out[a + 1] - out[a]) * (pos - a);
  }
  // Through a wall and an old horn: no lows, no highs.
  biquad(warped, rate, "highpass", 380, 0.7);
  biquad(warped, rate, "lowpass", 2600, 0.7);
  // Surface crackle and hiss.
  const hiss = biquad(noise(out.length, rand), rate, "bandpass", 2400, 0.6);
  for (let i = 0; i < warped.length; i++) {
    warped[i] += hiss[i] * 0.012;
    if (rand() < 0.0004) warped[i] += (rand() - 0.5) * 0.5;
  }
  return wrapLoop(normalise(warped, 0.6), rate, 0.3);
}

/** Chhing, the pair of small bronze cymbals that keeps a robam's time: open (ringing) or closed. */
function chhing(rate: number, rand: () => number, open: boolean): Float32Array {
  const length = n(open ? 0.9 : 0.12, rate);
  const strike = noise(n(0.003, rate), rand);
  const input = new Float32Array(length);
  input.set(strike);
  const ring = modal(input, rate, [
    [3150, open ? 0.5 : 0.03, 1],
    [4420, open ? 0.38 : 0.025, 0.8],
    [5870, open ? 0.3 : 0.02, 0.6],
    [7310, open ? 0.22 : 0.015, 0.4],
    [9020, open ? 0.15 : 0.01, 0.25],
  ]);
  if (!open) {
    const clap = biquad(noise(length, rand), rate, "bandpass", 3600, 1.2);
    for (let i = 0; i < length; i++) ring[i] += clap[i] * 0.4 * Math.exp(-i / rate / 0.02);
  }
  return ring;
}

/** Sampho, the two-headed barrel drum: a low round stroke. */
function sampho(rate: number, rand: () => number): Float32Array {
  const length = n(0.5, rate);
  const out = new Float32Array(length);
  let ph = 0;
  for (let i = 0; i < length; i++) {
    const t = i / rate;
    ph += (2 * Math.PI * (88 + 30 * Math.exp(-t / 0.03))) / rate;
    out[i] = Math.sin(ph) * Math.exp(-t / 0.18);
  }
  const skin = biquad(noise(length, rand), rate, "bandpass", 900, 1);
  for (let i = 0; i < length; i++) out[i] += skin[i] * 0.15 * Math.exp(-i / rate / 0.015);
  return out;
}

/**
 * About 3.4 s of a robam played close, while the dancer is there: the roneat ek's
 * melody in its tremolo, the low roneat under it, the sralai's reed line holding and
 * bending its notes, the chhing on every beat (open, then closed) and the sampho on
 * the strong ones. Slightly slow and out of true, like a record running down.
 */
export function robamSong(rate: number, rand: () => number): Float32Array {
  const total = 3.4;
  const out = new Float32Array(n(total, rate));
  const beat = 0.42;
  const tonic = 392 * 2 ** (-0.4 / 12);
  const melody = [4, 5, 4, 3, 1, 2, 3, 4];
  melody.forEach((degree, k) => {
    const f = tonic * 2 ** (SCALE[degree] / 12);
    const start = 0.04 + k * beat;
    for (let r = 0; r < 4; r++)
      mix(out, roneatKey(rate, rand, f), rate, start + r * 0.095, r ? 0.5 : 0.9, () => 1);
    if (k % 2 === 0) mix(out, roneatKey(rate, rand, f / 2), rate, start, 0.45, () => 1);
  });
  // The sralai: a quadruple reed, nasal, with a wide slow vibrato and slides.
  const reedLine = [7, 7, 9, 7, 4, 4, 2, 4];
  const reed = new Float32Array(out.length);
  let ph = 0;
  for (let i = 0; i < reed.length; i++) {
    const t = i / rate;
    const k = Math.min(reedLine.length - 1, Math.floor(t / beat));
    const next = reedLine[Math.min(reedLine.length - 1, k + 1)];
    const into = Math.max(0, (t - k * beat) / beat - 0.75) / 0.25;
    const degree = reedLine[k] + (next - reedLine[k]) * into * into;
    const f = (tonic / 2) * 2 ** (degree / 12) * (1 + 0.012 * Math.sin(2 * Math.PI * 5.2 * t));
    ph += (2 * Math.PI * f) / rate;
    // A buzzing reed: a band-limited pulse-like wave.
    reed[i] = Math.tanh(3 * Math.sin(ph)) * 0.6 + Math.sin(2 * ph) * 0.25 + Math.sin(3 * ph) * 0.2;
  }
  const nasal = formant(reed, rate, [
    [1100, 220, 1],
    [2500, 400, 0.6],
    [3400, 500, 0.3],
  ]);
  mix(out, normalise(nasal, 1), rate, 0, 0.22, (t) => Math.min(1, t / 0.15));
  // Chhing on every beat (open, closed), sampho on the first and third of each four.
  for (let b = 0; b * beat < total - 0.2; b++) {
    mix(
      out,
      chhing(rate, rand, b % 2 === 0),
      rate,
      0.04 + b * beat,
      b % 2 === 0 ? 0.35 : 0.28,
      () => 1,
    );
    if (b % 4 === 0 || b % 4 === 2)
      mix(out, sampho(rate, rand), rate, 0.04 + b * beat, 0.7, () => 1);
  }
  // A small room and an old horn: a short echo, the very top and bottom rolled off.
  const echo = n(0.07, rate);
  for (let i = echo; i < out.length; i++) out[i] += out[i - echo] * 0.28;
  biquad(out, rate, "highpass", 90, 0.7);
  biquad(out, rate, "lowpass", 6000, 0.7);
  return normalise(out, 0.8);
}

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
 * Every light in the house dies at once (Sora has stepped into the back room): a relay's
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
 * The lights catching again after the dancer (StudioLights.lightsBack): a hiss rising out
 * of nothing, then an electric crack and a burst of mains buzz each time they catch, timed
 * to the end of POWER_CUT.
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

/**
 * Under her music while she is there (4 s): a sub cluster beating slow and rising, a thin
 * high whine fighting it, whispers at the ear from all sides, all swelling to the end and
 * cut off dead as the lights come back. No hit when she appears (the user disliked one).
 */
export function hauntDrone(rate: number, rand: () => number): Float32Array {
  const seconds = 4;
  const out = new Float32Array(n(seconds, rate));
  const swell = (t: number) => Math.min(1, t / 0.6) * (0.35 + 0.65 * (t / seconds) ** 1.5);
  let a = 0,
    b = 0,
    c = 0;
  for (let i = 0; i < out.length; i++) {
    const t = i / rate;
    a += (2 * Math.PI * 41) / rate;
    b += (2 * Math.PI * 43.7) / rate;
    c += (2 * Math.PI * (55 - 3 * (t / seconds))) / rate;
    out[i] = (0.5 * Math.sin(a) + 0.45 * Math.sin(b) + 0.3 * Math.sin(c)) * swell(t);
  }
  const whine = biquad(noise(n(seconds, rate), rand), rate, "bandpass", 2900, 18);
  mix(out, whine, rate, 0, 0.5, (t) => swell(t) * (0.6 + 0.4 * Math.sin(t * 5.3)));
  for (const at of [0.3, 1.2, 1.9, 2.6, 3.2])
    mix(out, whisper(rate, rand), rate, at, 0.55, () => 1);
  // Cut off dead at the end, no tail.
  const fade = n(0.02, rate);
  for (let i = 0; i < fade; i++) out[out.length - 1 - i] *= i / fade;
  return normalise(out, 0.9);
}
