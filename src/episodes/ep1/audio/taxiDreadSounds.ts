import {
  biquad,
  formant,
  modal,
  mudSuction,
  noise,
  normalise,
  stickSlip,
  sweep,
  wetStep,
  wrapLoop,
} from "@/audio/synth";

/**
 * Synthesised stand-ins for the ride's dread (Audio Design Document, section 9)
 * until recordings exist: the dash radio hissing between stations, something
 * running past faster than a person can, a hand on the glass, the driver's
 * breath catching and the tyres slithering as he brakes. Wordless and original;
 * no chant or bell, so nothing sacred becomes a scare. Stereo is [left, right].
 */

export type Stereo = [Float32Array, Float32Array];

/** Random impulses at `perSecond`, sizes skewed small, signs random. */
function crackles(n: number, rate: number, random: () => number, perSecond: number) {
  const out = new Float32Array(n);
  for (let i = 0; i < n; i++)
    if (random() < perSecond / rate) out[i] = (random() < 0.5 ? -1 : 1) * random() ** 3;
  return out;
}

/**
 * The dash radio left on between stations, an 8 s loop: band-limited hiss, the
 * storm's static crackling in it, a heterodyne whistle drifting, and under it all
 * something like a far voice that never makes a word. The soundscape rides it up
 * when something is near.
 */
export function radioStatic(rate: number, random: () => number): Float32Array {
  const n = Math.round(rate * 8.4),
    out = new Float32Array(n);
  const hiss = biquad(noise(n, random), rate, "bandpass", Math.min(2400, rate * 0.4), 0.6);
  const crackle = modal(crackles(n, rate, random, 26), rate, [
    [Math.min(1900, rate * 0.4), 0.0015, 1],
    [Math.min(3100, rate * 0.4), 0.0008, 0.6],
  ]);
  // Breath through vowel-like bands, swelling and falling: a voice too far to hear.
  const voice = formant(noise(n, random), rate, [
    [620, 90, 1],
    [1180, 140, 0.7],
    [2450, 220, 0.3],
  ]);
  let phase = 0;
  for (let i = 0; i < n; i++) {
    const t = i / rate;
    phase += (880 + 260 * Math.sin((2 * Math.PI * t) / 8.4)) / rate;
    const whistle = Math.sin(2 * Math.PI * phase) * (0.5 + 0.5 * Math.sin((2 * Math.PI * t) / 4.2));
    const murmur = Math.max(0, Math.sin((2 * Math.PI * t) / 2.8 + 1)) ** 2;
    out[i] = hiss[i] * 0.5 + crackle[i] * 0.9 + whistle * 0.025 + voice[i] * 0.22 * murmur;
  }
  // A 1930s valve set: nothing much under 300 Hz or above 3.2 kHz gets through.
  biquad(out, rate, "highpass", 300, 0.7);
  biquad(out, rate, "lowpass", Math.min(3200, rate * 0.4), 0.7);
  return normalise(wrapLoop(out, rate, 0.4), 0.6);
}

/** Equal-power gains for a pan position from -1 (left) to 1 (right). */
function pan(position: number): [number, number] {
  const a = ((Math.max(-1, Math.min(1, position)) + 1) * Math.PI) / 4;
  return [Math.cos(a), Math.sin(a)];
}

/**
 * Something running past at impossible speed, 1.6 s with its nearest point at
 * 0.6 s: a torn whoosh whose band climbs as it closes and drops as it goes, a
 * breathy howl bending down past it (Doppler), and bare feet slapping the
 * flooded mud nine times a second. Panned from `from` to `to`.
 */
export function ghostRush(rate: number, random: () => number, from = -1, to = 1): Stereo {
  const n = Math.round(rate * 1.6),
    closest = 0.6;
  const air = sweep(
    noise(n, random),
    rate,
    "bandpass",
    (t) => 380 + 2600 * Math.exp(-(((t - closest) / 0.16) ** 2)),
    1.4,
  );
  const mono = new Float32Array(n);
  let phase = 0;
  for (let i = 0; i < n; i++) {
    const t = i / rate,
      near = Math.exp(-(((t - closest) / 0.21) ** 2));
    phase += (430 * (1 + 0.22 * Math.tanh((closest - t) / 0.07))) / rate;
    const howl = Math.sin(2 * Math.PI * phase) * (0.6 + 0.4 * random());
    mono[i] = air[i] * near * 1.3 + howl * near * 0.08;
  }
  for (let t = 0.2; t < 1.1; t += 0.11 + random() * 0.02) {
    const step = wetStep(rate, random),
      at = Math.round(t * rate),
      gain = 0.5 * Math.exp(-(((t - closest) / 0.3) ** 2));
    for (let j = 0; j < step.length && at + j < n; j++) mono[at + j] += step[j] * gain;
  }
  const left = new Float32Array(n),
    right = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const t = i / rate,
      p = Math.max(0, Math.min(1, (t - 0.25) / 0.7)),
      [l, r] = pan(from + (to - from) * p * p * (3 - 2 * p));
    left[i] = mono[i] * l;
    right[i] = mono[i] * r;
  }
  const peak = Math.max(
    ...[left, right].map((c) => c.reduce((m, v) => Math.max(m, Math.abs(v)), 0)),
  );
  for (const c of [left, right]) for (let i = 0; i < n; i++) c[i] *= 0.9 / (peak || 1);
  return [left, right];
}

/**
 * Bare feet sprinting through the flooded ruts, 1.6 s for the soundscape to
 * carry along beside the car: a stride every ~0.11 s, each a wet slap and the
 * mud sucking after it, with a ragged breath riding over them.
 */
export function mudSprint(rate: number, random: () => number): Float32Array {
  const n = Math.round(rate * 1.7),
    out = new Float32Array(n);
  for (let t = 0.02; t < 1.45; t += 0.1 + random() * 0.03) {
    const at = Math.round(t * rate),
      slap = wetStep(rate, random),
      suck = mudSuction(rate, random);
    for (let j = 0; j < slap.length && at + j < n; j++) out[at + j] += slap[j] * 0.8;
    const later = at + Math.round(0.04 * rate);
    for (let j = 0; j < suck.length && later + j < n; j++) out[later + j] += suck[j] * 0.25;
  }
  const breath = formant(noise(n, random), rate, [
    [520, 160, 1],
    [1500, 260, 0.5],
  ]);
  for (let i = 0; i < n; i++) {
    const t = i / rate;
    out[i] += breath[i] * 0.35 * Math.max(0, Math.sin(t * Math.PI * 2 * 2.6)) ** 3;
  }
  return normalise(out, 0.85);
}

/**
 * A palm slapping the side glass from outside: the pane's dull thud and its ring,
 * the glass buzzing in a loose frame, then a wet squeak as the hand drags off.
 */
export function windowSlap(rate: number, random: () => number): Float32Array {
  const n = Math.round(rate * 1.1),
    hit = new Float32Array(n);
  hit[Math.round(0.01 * rate)] = 1;
  const thud = modal(hit, rate, [
    [92, 0.07, 1],
    [176, 0.04, 0.6],
    [310, 0.02, 0.35],
  ]);
  const ring = modal(hit, rate, [
    [Math.min(1170, rate * 0.4), 0.09, 0.22],
    [Math.min(2390, rate * 0.4), 0.05, 0.12],
    [Math.min(3510, rate * 0.4), 0.03, 0.07],
  ]);
  const buzz = modal(
    stickSlip(
      n,
      rate,
      random,
      () => 34,
      (t) => (t < 0.32 ? Math.exp(-t * 9) : 0),
      0.3,
    ),
    rate,
    [[Math.min(640, rate * 0.4), 0.006, 1]],
  );
  const squeak = modal(
    stickSlip(
      n,
      rate,
      random,
      (t) => 260 + 520 * Math.max(0, t - 0.3),
      (t) => (t > 0.3 && t < 0.75 ? Math.sin(((t - 0.3) / 0.45) * Math.PI) : 0),
      0.15,
    ),
    rate,
    [[Math.min(1850, rate * 0.4), 0.003, 1]],
  );
  const out = new Float32Array(n);
  for (let i = 0; i < n; i++) out[i] = thud[i] * 1.2 + ring[i] + buzz[i] * 0.18 + squeak[i] * 0.1;
  return normalise(out, 0.9);
}

/**
 * The driver's breath caught short: a sharp inhale through the teeth, held, then
 * let out unsteadily, shaking.
 */
export function driverGasp(rate: number, random: () => number): Float32Array {
  const n = Math.round(rate * 1.9),
    out = new Float32Array(n);
  const inhale = formant(noise(n, random), rate, [
    [380, 180, 0.6],
    [2100, 380, 1],
    [3000, 520, 0.6],
  ]);
  const exhale = formant(noise(n, random), rate, [
    [560, 200, 1],
    [1250, 260, 0.6],
  ]);
  for (let i = 0; i < n; i++) {
    const t = i / rate;
    const drawIn = t < 0.32 ? (1 - Math.exp(-t / 0.02)) * Math.exp(-(((t - 0.18) / 0.14) ** 2)) : 0;
    const letGo =
      t > 0.95
        ? Math.sin(Math.min(1, (t - 0.95) / 0.85) * Math.PI) *
          (0.65 + 0.35 * Math.sin(t * 2 * Math.PI * 8.5))
        : 0;
    out[i] = inhale[i] * drawIn * 1.4 + exhale[i] * letGo * 0.6;
  }
  return normalise(out, 0.8);
}

/**
 * Tyres locking on wet laterite: mud and spray slithering under the arches, a
 * scrub that dies as the car slows, and the body dipping on its springs.
 */
export function brakeSlither(rate: number, random: () => number): Float32Array {
  const n = Math.round(rate * 1.2),
    out = new Float32Array(n);
  const mud = sweep(
    noise(n, random),
    rate,
    "bandpass",
    (t) => 1100 - 600 * Math.min(1, t / 0.8),
    1.2,
  );
  const spray = biquad(noise(n, random), rate, "highpass", Math.min(3200, rate * 0.4), 0.7);
  const dip = new Float32Array(n);
  dip[Math.round(0.05 * rate)] = 1;
  const body = modal(dip, rate, [
    [58, 0.12, 1],
    [116, 0.06, 0.4],
  ]);
  for (let i = 0; i < n; i++) {
    const t = i / rate,
      env = (1 - Math.exp(-t / 0.03)) * Math.exp(-t / 0.42);
    out[i] = mud[i] * env * 1.1 + spray[i] * env * 0.35 + body[i] * 0.8;
  }
  return normalise(out, 0.8);
}
