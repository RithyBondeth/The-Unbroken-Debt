import { creak, hall, knock, loopify, place, sweepBand, whisper, type Stereo } from "../dread";
import { biquad, brown, modal, noise, normalise, seededRandom } from "../synth";
import { dogBarks } from "./nightSounds";

/**
 * The in-game half of the title screen's dread (Audio Design Document,
 * sections 1 and 5): stingers that land on a real scare, a pressure bed that
 * swells as the night closes in, the ringing left in the ears after a shock,
 * and the studio's own room tone with the city beyond the rain. Original and
 * synthesised; no chant, bell or Pinpeat is used, so nothing sacred is turned
 * into a scare (section 6.3). Stereo is [left, right].
 */

export type Sting = "rise" | "shock" | "drop" | "swell";

/** Seconds from the start of each sting to its hit: start it this early to land on a beat. */
export const STING_HIT: Record<Sting, number> = { rise: 1.6, shock: 0.06, drop: 0, swell: 3.2 };

const SECONDS: Record<Sting, number> = { rise: 5.5, shock: 4.8, drop: 3.2, swell: 7.5 };

/** Peak of each sting: the close shock is the loudest thing in the act. */
const PEAK: Record<Sting, number> = { rise: 0.75, shock: 0.95, drop: 0.6, swell: 0.45 };

const SEED: Record<Sting, number> = { rise: 4101, shock: 4102, drop: 4103, swell: 4104 };

/** Fades the last `seconds` so nothing ends on a click. */
function fadeTail(side: Float32Array, rate: number, seconds: number): void {
  const n = Math.min(side.length, Math.round(rate * seconds));
  for (let i = 0; i < n; i++) side[side.length - 1 - i] *= i / n;
}

function normaliseStereo([left, right]: Stereo, peak: number): Stereo {
  let max = 0;
  for (let i = 0; i < left.length; i++) max = Math.max(max, Math.abs(left[i]), Math.abs(right[i]));
  if (max > 0)
    for (let i = 0; i < left.length; i++) {
      left[i] *= peak / max;
      right[i] *= peak / max;
    }
  return [left, right];
}

/**
 * A deep blow felt as much as heard: a falling sine with harmonics, so laptop
 * speakers that cannot play 40 Hz still carry its weight.
 */
function subDrop(side: Float32Array, rate: number, at: number, gain: number, decay: number) {
  const start = Math.round(at * rate);
  let phase = 0;
  for (let i = start; i < side.length; i++) {
    const t = (i - start) / rate;
    phase += (58 - 22 * Math.min(1, t / 0.8)) / rate;
    const s = Math.sin(2 * Math.PI * phase);
    const body = s + 0.35 * Math.sin(4 * Math.PI * phase) + 0.18 * Math.sin(6 * Math.PI * phase);
    side[i] += body * Math.min(1, t / 0.004) * Math.exp(-t / decay) * gain;
  }
}

/** A house beam cracking under weight: the timber modes of a struck post, low and dry. */
function beamCrack(rate: number, rand: () => number): Float32Array {
  const hit = new Float32Array(Math.round(rate * 1.4));
  for (let i = 0; i < 90; i++) hit[Math.round(i * rate * 0.0009)] = (rand() - 0.4) * (1 - i / 90);
  return modal(hit, rate, [
    [71, 0.32, 1],
    [118, 0.22, 0.7],
    [203, 0.14, 0.5],
    [347, 0.08, 0.35],
    [611, 0.05, 0.25],
    [1190, 0.025, 0.15],
  ]);
}

/**
 * Bowed contrabass and hollow iron scrape: low dark minor-second and tritone
 * intervals built from smooth damped harmonics and bow-rosin air, kept well
 * under 1.4 kHz so it feels heavy and dread-filled rather than harsh or buzzy.
 */
function darkBowScrape(
  rate: number,
  length: number,
  start: number,
  gain: number,
  rand: () => number,
): Stereo {
  const sides: Stereo = [new Float32Array(length), new Float32Array(length)];
  const rosinL = biquad(noise(length, rand), rate, "bandpass", 420, 1.4);
  const rosinR = biquad(noise(length, rand), rate, "bandpass", 490, 1.4);
  [110, 116.5, 164.8, 220, 233.1, 311.1].forEach((f, n) => {
    let phase = 0;
    for (let i = start; i < length; i++) {
      const t = (i - start) / rate;
      const slide =
        1 - 0.045 * Math.min(1, t / 1.4) + 0.008 * Math.sin(t * 2 * Math.PI * (3.1 + n * 0.45));
      phase += (f * slide) / rate;
      const w = 2 * Math.PI * phase;
      const bow = Math.sin(w) + 0.42 * Math.sin(2 * w) + 0.18 * Math.sin(3 * w);
      const env = Math.min(1, t / 0.035) * Math.exp(-t / (1.05 + n * 0.14));
      sides[n % 2][i] += bow * env * gain * 0.48;
    }
  });
  for (let i = start; i < length; i++) {
    const t = (i - start) / rate;
    const env = Math.min(1, t / 0.025) * Math.exp(-t / 0.85) * gain * 1.1;
    sides[0][i] += rosinL[i] * env;
    sides[1][i] += rosinR[i] * env;
  }
  for (const side of sides) {
    biquad(side, rate, "highpass", Math.min(90, rate * 0.2), 0.7);
    biquad(side, rate, "lowpass", Math.min(1350, rate * 0.4), 0.7);
  }
  return sides;
}

/**
 * A sting that lands on a real scare, its hit at STING_HIT[kind]:
 * - `rise`: air and a low cluster bending upward, then a sub drop and a beam cracking.
 * - `shock`: almost no warning: a blow, bowed metal shrieking and a whisper torn short.
 * - `drop`: a vanishing: pressure released, a hollow knock and the air settling.
 * - `swell`: a slow crescendo of beating low notes and breath that never hits.
 */
export function sting(rate: number, kind: Sting): Stereo {
  const length = Math.round(rate * SECONDS[kind]);
  const rand = seededRandom(SEED[kind]);
  const hitAt = STING_HIT[kind];
  const hit = Math.round(hitAt * rate);
  const left = new Float32Array(length);
  const right = new Float32Array(length);
  const airL = noise(length, rand);
  const airR = noise(length, rand);

  if (kind === "rise" || kind === "swell") {
    // Air rushing in and a close cluster bending upward into the hit.
    const top = Math.min(2400, rate * 0.4);
    const riseL = sweepBand(airL, rate, (t) => 300 + top * Math.min(1, t / hitAt) ** 2, 2.5);
    const riseR = sweepBand(airR, rate, (t) => 340 + top * Math.min(1, t / hitAt) ** 2, 2.5);
    const end = kind === "swell" ? length : hit;
    for (let i = 0; i < end; i++) {
      const t = i / rate;
      const k =
        kind === "swell"
          ? Math.sin(Math.PI * Math.min(1, t / (SECONDS.swell - 0.3)))
          : (i / hit) ** 3;
      left[i] += riseL[i] * k * 0.45;
      right[i] += riseR[i] * k * 0.45;
      const bend = kind === "rise" ? 1 + 0.18 * k : 1 + 0.01 * Math.sin(t * 0.7);
      for (const [f, side] of [
        [110, 0],
        [116.5, 1],
        [155.6, 0],
        [164.8, 1],
      ] as const) {
        const s = Math.sin(2 * Math.PI * f * t * bend) * k * 0.11;
        (side ? right : left)[i] += s;
        (side ? left : right)[i] += s * 0.4;
      }
    }
  }
  if (kind === "rise") {
    subDrop(left, rate, hitAt, 0.9, 1.1);
    subDrop(right, rate, hitAt, 0.9, 1.1);
    const beam = beamCrack(rate, rand);
    place(left, beam, rate, hitAt, 0.7);
    place(right, beam, rate, hitAt + 0.011, 0.6);
  }
  if (kind === "shock") {
    subDrop(left, rate, hitAt, 1.1, 0.85);
    subDrop(right, rate, hitAt, 1.1, 0.85);
    const beam = beamCrack(rate, rand);
    place(left, beam, rate, hitAt, 0.65);
    place(right, beam, rate, hitAt + 0.009, 0.6);
    const [sl, sr] = darkBowScrape(rate, length, hit, 0.32, rand);
    const bodyAirL = biquad(airL.slice(), rate, "lowpass", Math.min(1100, rate * 0.35), 0.7);
    const bodyAirR = biquad(airR.slice(), rate, "lowpass", Math.min(1100, rate * 0.35), 0.7);
    const torn = biquad(
      whisper(rate, rand, 0.95),
      rate,
      "lowpass",
      Math.min(2400, rate * 0.4),
      0.7,
    );
    for (let i = 0; i < length; i++) {
      const t = (i - hit) / rate;
      const crack = i >= hit ? Math.exp(-t * 22) : 0;
      left[i] += sl[i] + bodyAirL[i] * crack * 0.55;
      right[i] += sr[i] + bodyAirR[i] * crack * 0.55;
    }
    place(left, torn, rate, hitAt + 0.07, 0.55);
    place(right, torn, rate, hitAt + 0.09, 0.28);
  }
  if (kind === "drop") {
    subDrop(left, rate, 0, 0.8, 0.45);
    subDrop(right, rate, 0, 0.8, 0.45);
    const k = knock(rate);
    place(left, k, rate, 0.02, 0.6);
    place(right, k, rate, 0.02, 0.6);
    // The air settling back where something stood.
    const settleL = biquad(airL.slice(), rate, "lowpass", Math.min(900, rate * 0.4), 0.7);
    const settleR = biquad(airR.slice(), rate, "lowpass", Math.min(900, rate * 0.4), 0.7);
    for (let i = 0; i < length; i++) {
      const t = i / rate;
      const env = Math.min(1, t / 0.3) * Math.exp(-t / 0.9) * 0.5;
      left[i] += settleL[i] * env;
      right[i] += settleR[i] * env;
    }
  }
  const out: Stereo = [hall(left, rate, 0.35), hall(right, rate, 0.35)];
  for (const side of out) fadeTail(side, rate, 0.4);
  return normaliseStereo(out, PEAK[kind]);
}

/**
 * Pressure under the silence, 30 s loop: two low notes beating against each
 * other, their upper harmonics breathing in and out (so small speakers carry
 * it), a slow inhale of air through the dark, and timbers groaning far off.
 */
export function pressureBed(rate: number): Stereo {
  const length = rate * 34;
  const rand = seededRandom(4111);
  const sides: Stereo = [new Float32Array(length), new Float32Array(length)];
  const breathL = biquad(brown(length, rand, 0.9985), rate, "lowpass", 190, 0.7);
  const breathR = biquad(brown(length, rand, 0.9985), rate, "lowpass", 210, 0.7);
  for (let i = 0; i < length; i++) {
    const t = i / rate;
    // Slow organic swells aligned to the 32 s loop seam so it never pulses mechanically.
    const swell =
      0.65 + 0.35 * Math.sin((2 * Math.PI * t) / 16 + Math.sin((2 * Math.PI * t) / 32) * 1.4);
    const upper = 0.35 + 0.3 * Math.sin((2 * Math.PI * t) / 16 + 0.8);
    const tone = (f: number) =>
      Math.sin(2 * Math.PI * f * t) +
      0.32 * upper * Math.sin(4 * Math.PI * f * t) +
      0.14 * upper * Math.sin(6 * Math.PI * f * t);
    const inhale = Math.max(0, Math.sin((2 * Math.PI * t) / 10.6667)) ** 2.5;
    sides[0][i] +=
      (tone(41.2) * 0.35 + tone(61.7) * 0.08) * swell + breathL[i] * (0.9 + inhale * 1.4);
    sides[1][i] +=
      (tone(41.7) * 0.35 + tone(61.7) * 0.08) * swell + breathR[i] * (0.9 + inhale * 1.4);
  }
  for (const [at, side] of [
    [5.5, 0],
    [17.2, 1],
    [26.4, 0],
  ] as const) {
    // Far-off timbers, deeper than the house's own creaks.
    const groan = biquad(creak(rate, rand, 1.6 + rand()), rate, "lowpass", 420, 0.7);
    place(sides[side], groan, rate, at, 0.2);
    place(sides[1 - side], groan, rate, at + 0.03, 0.09);
  }
  return [
    normalise(loopify(hall(sides[0], rate, 0.45), rate, 2), 0.46),
    normalise(loopify(hall(sides[1], rate, 0.45), rate, 2), 0.46),
  ];
}

/**
 * The stunned pressure left in the ears after a shock down the line: a warm,
 * muffled underwater air-pressure hush and hollow dark resonance that clears
 * over ~6 seconds, without any harsh high-pitched tinnitus whine.
 */
export function ringingEars(rate: number): Stereo {
  const length = Math.round(rate * 6.5);
  const rand = seededRandom(4121);
  const pressureL = biquad(brown(length, rand, 0.996), rate, "lowpass", 240, 0.7);
  const pressureR = biquad(brown(length, rand, 0.996), rate, "lowpass", 260, 0.7);
  const airL = biquad(noise(length, rand), rate, "bandpass", 580, 1.8);
  const airR = biquad(noise(length, rand), rate, "bandpass", 640, 1.8);
  const f = Math.min(1850, rate * 0.35);
  const left = new Float32Array(length);
  const right = new Float32Array(length);
  for (let i = 0; i < length; i++) {
    const t = i / rate;
    const env = Math.min(1, t / 0.12) * Math.exp(-t / 1.85);
    const hush = Math.min(1, t / 0.08) * Math.exp(-t / 0.95) * 0.045;
    left[i] = (pressureL[i] * 2.2 + airL[i] * 0.35) * env + Math.sin(2 * Math.PI * f * t) * hush;
    right[i] =
      (pressureR[i] * 2.2 + airR[i] * 0.35) * env + Math.sin(2 * Math.PI * f * 1.003 * t) * hush;
  }
  fadeTail(left, rate, 0.8);
  fadeTail(right, rate, 0.8);
  return normaliseStereo([left, right], 0.18);
}

/** Hooves on a wet street, far off: a horse cart passing slowly, two-beat walk. */
function cartPassing(rate: number, rand: () => number, seconds: number): Float32Array {
  const out = new Float32Array(Math.round(rate * seconds));
  for (let t = 0.2; t < seconds - 0.5; t += 0.52 + (rand() - 0.5) * 0.06) {
    for (const lag of [0, 0.13]) {
      const at = Math.round((t + lag) * rate);
      const size = 0.6 + rand() * 0.4;
      const fall = Math.sin((Math.PI * t) / seconds);
      for (let i = 0; i < rate * 0.05 && at + i < out.length; i++)
        out[at + i] += (rand() * 2 - 1) * Math.exp(-i / (rate * 0.008)) * size * fall;
    }
  }
  // Wheels grinding on stones under it.
  const wheel = biquad(brown(out.length, rand), rate, "bandpass", 180, 0.9);
  for (let i = 0; i < out.length; i++)
    out[i] += wheel[i] * Math.sin((Math.PI * i) / out.length) * 0.6;
  return biquad(biquad(out, rate, "bandpass", 900, 0.8), rate, "lowpass", 1400, 0.7);
}

/**
 * The studio's room tone and Phnom Penh beyond the rain, 40 s loop: the dead
 * air of a small plastered room, the city's low murmur through the shutters,
 * a horse cart passing slowly in the street below and a dog somewhere across
 * the rooftops. All of it far and muffled; the rain stays in front.
 */
export function studioRoom(rate: number): Stereo {
  const length = rate * 42;
  const rand = seededRandom(4131);
  const sides: Stereo = [new Float32Array(length), new Float32Array(length)];
  const roomL = biquad(brown(length, rand, 0.997), rate, "lowpass", 160, 0.7);
  const roomR = biquad(brown(length, rand, 0.997), rate, "lowpass", 170, 0.7);
  const cityL = biquad(noise(length, rand), rate, "bandpass", 320, 0.6);
  const cityR = biquad(noise(length, rand), rate, "bandpass", 300, 0.6);
  for (let i = 0; i < length; i++) {
    const t = i / rate;
    const murmur = 0.6 + 0.4 * Math.sin((2 * Math.PI * t) / 21 + 1.3);
    sides[0][i] = roomL[i] * 0.6 + cityL[i] * 0.05 * murmur;
    sides[1][i] = roomR[i] * 0.6 + cityR[i] * 0.05 * murmur;
  }
  const cart = cartPassing(rate, rand, 14);
  for (let i = 0; i < cart.length; i++) {
    // It crosses from left to right below the window.
    const pan = i / cart.length;
    const at = Math.round(rate * 9) + i;
    sides[0][at] += cart[i] * 0.05 * (1 - pan);
    sides[1][at] += cart[i] * 0.05 * pan;
  }
  const dog = biquad(dogBarks(rate, rand), rate, "lowpass", 1100, 0.7);
  place(sides[1], dog, rate, 31, 0.03);
  place(sides[0], dog, rate, 31.02, 0.015);
  return [normalise(loopify(sides[0], rate, 2), 0.25), normalise(loopify(sides[1], rate, 2), 0.25)];
}
