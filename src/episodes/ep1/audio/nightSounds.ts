import { biquad, mix, noise, normalise } from "../../../audio/synth";

/**
 * Synthesised stand-ins for the village night (Audio Design Document, section 9)
 * until field recordings exist: frogs in the flooded fields, crickets, a tokay
 * gecko, distant dogs, an owl, crows, and a wordless chant-like drone that holds
 * the place of the funeral recitation (smot) until a real recording is supplied.
 * Mono, peak 0.9 or less, pure functions. Loops wrap without a click.
 */

const seconds = (s: number, sampleRate: number) => Math.round(s * sampleRate);

function fadeEnds(out: Float32Array, sampleRate: number, fade: number): Float32Array {
  const n = seconds(fade, sampleRate);
  for (let i = 0; i < n; i++) {
    out[i] *= i / n;
    out[out.length - 1 - i] *= i / n;
  }
  return out;
}

/** A tone gliding through `pitch(t)` Hz, with a few harmonics. */
function voice(
  length: number,
  sampleRate: number,
  pitch: (t: number) => number,
  harmonics: number[],
): Float32Array {
  const out = new Float32Array(length);
  let phase = 0;
  for (let i = 0; i < length; i++) {
    phase += (2 * Math.PI * pitch(i / sampleRate)) / sampleRate;
    let v = 0;
    harmonics.forEach((g, h) => (v += g * Math.sin(phase * (h + 1))));
    out[i] = v;
  }
  return out;
}

/** Rice frogs and toads in the paddies: many voices croaking in overlapping pulses. */
export function frogsLoop(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(8, sampleRate);
  const out = new Float32Array(length);
  for (let k = 0; k < 90; k++) {
    const f = 300 + rand() * 700;
    const pulses = 3 + Math.floor(rand() * 6);
    const rate = 18 + rand() * 25;
    const d = pulses / rate;
    const croak = voice(seconds(d, sampleRate), sampleRate, () => f, [1, 0.6, 0.3]);
    for (let i = 0; i < croak.length; i++) {
      const t = i / sampleRate;
      croak[i] *= Math.max(0, Math.sin(Math.PI * t * rate)) ** 3;
    }
    mix(
      out,
      biquad(croak, sampleRate, "bandpass", f * 1.5, 1.2),
      sampleRate,
      0.2 + rand() * 7.4,
      0.3 + rand() * 0.7,
      () => 1,
    );
  }
  return normalise(fadeEnds(out, sampleRate, 0.3), 0.8);
}

/** Crickets: high chirps in trains, a steady bed under everything. */
export function cricketsLoop(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(4, sampleRate);
  const out = new Float32Array(length);
  for (let k = 0; k < 40; k++) {
    const f = 3800 + rand() * 1600;
    const chirp = voice(seconds(0.12, sampleRate), sampleRate, () => f, [1]);
    for (let i = 0; i < chirp.length; i++)
      chirp[i] *= Math.max(0, Math.sin((i / sampleRate) * Math.PI * 60)) ** 2;
    mix(out, chirp, sampleRate, 0.1 + rand() * 3.75, 0.2 + rand() * 0.5, () => 1);
  }
  return normalise(fadeEnds(out, sampleRate, 0.15), 0.6);
}

/** A tokay gecko under the eaves: a dry rattle, then "to-kay" five times, slowing. */
export function geckoCall(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(5, sampleRate);
  const out = new Float32Array(length);
  const rattle = biquad(noise(seconds(0.5, sampleRate), rand), sampleRate, "bandpass", 700, 3);
  mix(
    out,
    rattle,
    sampleRate,
    0.05,
    0.5,
    (t) => Math.max(0, Math.sin(t * 2 * Math.PI * 28)) * Math.min(1, (0.5 - t) / 0.2),
  );
  let at = 0.8;
  for (let k = 0; k < 5; k++) {
    const to = voice(seconds(0.16, sampleRate), sampleRate, (t) => 520 + t * 400, [1, 0.5, 0.25]);
    const kay = voice(seconds(0.26, sampleRate), sampleRate, (t) => 640 - t * 260, [1, 0.6, 0.3]);
    mix(out, biquad(to, sampleRate, "lowpass", 2000, 0.7), sampleRate, at, 0.9 - k * 0.1, (t) =>
      Math.sin((Math.PI * t) / 0.16),
    );
    mix(
      out,
      biquad(kay, sampleRate, "lowpass", 2000, 0.7),
      sampleRate,
      at + 0.2,
      1 - k * 0.1,
      (t) => Math.sin((Math.PI * t) / 0.26),
    );
    at += 0.75 + k * 0.08;
  }
  return normalise(out, 0.7);
}

/** A village dog howling far off, wavering. */
export function dogHowl(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(3.6, sampleRate);
  const wobble = 5 + rand() * 2;
  const howl = voice(
    length,
    sampleRate,
    (t) =>
      420 +
      260 * Math.sin(Math.min(1, t / 1.2) * Math.PI * 0.5) -
      120 * Math.max(0, t - 2.4) +
      9 * Math.sin(t * wobble * 2 * Math.PI),
    [1, 0.35, 0.2, 0.1],
  );
  for (let i = 0; i < length; i++) {
    const t = i / sampleRate;
    howl[i] *= Math.min(1, t / 0.4) * Math.min(1, (3.6 - t) / 0.8);
  }
  return normalise(biquad(howl, sampleRate, "lowpass", 1400, 0.7), 0.6);
}

/** Dogs barking in another compound: a few rough barks. */
export function dogBarks(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(2.4, sampleRate);
  const out = new Float32Array(length);
  for (let k = 0; k < 4; k++) {
    const d = 0.14 + rand() * 0.06;
    const bark = voice(
      seconds(d, sampleRate),
      sampleRate,
      (t) => 480 - t * 900,
      [1, 0.7, 0.5, 0.3],
    );
    const rough = noise(bark.length, rand);
    for (let i = 0; i < bark.length; i++) bark[i] = bark[i] * 0.7 + rough[i] * 0.4;
    mix(
      out,
      biquad(bark, sampleRate, "bandpass", 900, 0.8),
      sampleRate,
      0.1 + k * (0.4 + rand() * 0.25),
      1,
      (t) => Math.sin((Math.PI * t) / d),
    );
  }
  return normalise(out, 0.6);
}

/** An owl: two soft hoots. */
export function owlHoot(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(2.2, sampleRate);
  const out = new Float32Array(length);
  for (const [at, d, f] of [
    [0.1, 0.35, 340],
    [0.75, 0.7, 320 + rand() * 20],
  ]) {
    const hoot = voice(seconds(d, sampleRate), sampleRate, (t) => f - t * 25, [1, 0.15]);
    mix(out, hoot, sampleRate, at, 1, (t) => Math.sin((Math.PI * t) / d) ** 1.5);
  }
  return normalise(out, 0.6);
}

/** Crows startled in a dead tree: harsh caws. */
export function crowCaws(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(2, sampleRate);
  const out = new Float32Array(length);
  for (let k = 0; k < 3; k++) {
    const d = 0.28 + rand() * 0.1;
    const caw = voice(
      seconds(d, sampleRate),
      sampleRate,
      (t) => 700 - t * 300,
      [1, 0.8, 0.7, 0.6, 0.4],
    );
    const rasp = noise(caw.length, rand);
    for (let i = 0; i < caw.length; i++) caw[i] = caw[i] * (0.6 + 0.4 * rasp[i]);
    mix(out, biquad(caw, sampleRate, "bandpass", 1300, 0.9), sampleRate, 0.05 + k * 0.55, 1, (t) =>
      Math.sin((Math.PI * t) / d),
    );
  }
  return normalise(out, 0.6);
}

/**
 * A placeholder for the funeral recitation: a low wordless voice moving slowly
 * between a few close pitches, with a second voice a fifth below, breathing
 * between phrases. No words, no Pali: the real smot replaces it (Cultural Guide).
 */
export function chantDrone(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(24, sampleRate);
  const out = new Float32Array(length);
  const steps = [0, 2, 3, 2, 0, -2, 0, 3, 5, 3, 2, 0];
  let at = 0.4;
  while (at < 22.5) {
    const phrase = 2.2 + rand() * 1.6;
    const notes = steps.slice(Math.floor(rand() * 6), Math.floor(rand() * 6) + 6);
    const base = 128;
    const line = voice(
      seconds(phrase, sampleRate),
      sampleRate,
      (t) =>
        base *
        2 ** (notes[Math.min(notes.length - 1, Math.floor((t / phrase) * notes.length))] / 12) *
        (1 + 0.006 * Math.sin(t * 2 * Math.PI * 5.5)),
      [1, 0.7, 0.5, 0.35, 0.25, 0.15, 0.1],
    );
    // A vowel between "o" and "a": formants at about 500 and 900 Hz.
    const vowel = biquad(line, sampleRate, "bandpass", 520 + rand() * 150, 1.5);
    const vowel2 = biquad(line, sampleRate, "bandpass", 950, 2.5);
    for (let i = 0; i < vowel.length; i++) vowel[i] = vowel[i] + vowel2[i] * 0.5;
    mix(
      out,
      vowel,
      sampleRate,
      at,
      1,
      (t) => Math.min(1, t / 0.3) * Math.min(1, (phrase - t) / 0.5),
    );
    const drone = voice(
      seconds(phrase, sampleRate),
      sampleRate,
      () => (base * 2) / 3,
      [1, 0.4, 0.2],
    );
    mix(
      out,
      drone,
      sampleRate,
      at,
      0.25,
      (t) => Math.min(1, t / 0.5) * Math.min(1, (phrase - t) / 0.6),
    );
    at += phrase + 0.5 + rand() * 0.6;
  }
  return normalise(fadeEnds(out, sampleRate, 0.5), 0.7);
}

/**
 * Wraps a loop: the last `fade` seconds are crossfaded into the first, and cut
 * off, so it repeats with no click and no dip in level.
 */
function wrapLoop(out: Float32Array, sampleRate: number, fade: number): Float32Array {
  const n = seconds(fade, sampleRate);
  const length = out.length - n;
  const loop = out.slice(0, length);
  for (let i = 0; i < n; i++) {
    const k = i / n;
    loop[i] = loop[i] * Math.sqrt(k) + out[length + i] * Math.sqrt(1 - k);
  }
  return loop;
}

/**
 * Steady rain in the village at night, heard out of doors: a soft hiss, a fine
 * patter on the forest's leaves, and heavier drops pattering on banana leaves and
 * thatch close by. Gentle in level; it should sit under everything else.
 */
export function villageRain(sampleRate: number, rand: () => number): Float32Array {
  const fade = 1;
  const length = seconds(12 + fade, sampleRate);
  const out = new Float32Array(length);
  // The hiss of rain on the whole forest, soft and wide, with a slow swell.
  const hiss = biquad(
    biquad(noise(length, rand), sampleRate, "lowpass", 2600, 0.6),
    sampleRate,
    "highpass",
    300,
    0.6,
  );
  const wash = biquad(noise(length, rand), sampleRate, "lowpass", 220, 0.7);
  for (let i = 0; i < length; i++) {
    const swell = 0.85 + 0.15 * Math.sin((i / sampleRate) * 0.5 + 1.3);
    out[i] = (hiss[i] * 0.5 + wash[i] * 0.6) * swell;
  }
  // Fine patter on leaves: thousands of tiny drops, most of them faint.
  const tick = noise(seconds(0.012, sampleRate), rand);
  for (let k = 0; k < 4200; k++) {
    const drop = biquad(tick, sampleRate, "bandpass", 2200 + rand() * 4500, 3 + rand() * 4);
    mix(
      out,
      drop,
      sampleRate,
      rand() * (length / sampleRate - 0.02),
      0.04 + rand() ** 3 * 0.35,
      (t) => Math.exp(-t / 0.0025),
    );
  }
  // Heavier drops on banana leaves and thatch: a short wet "pat" with a pitch.
  for (let k = 0; k < 260; k++) {
    const f = 450 + rand() * 900;
    const pat = voice(seconds(0.05, sampleRate), sampleRate, (t) => f * (1 - t * 2), [1, 0.4]);
    const splash = biquad(
      noise(pat.length, rand),
      sampleRate,
      "bandpass",
      1600 + rand() * 1500,
      1.5,
    );
    for (let i = 0; i < pat.length; i++) pat[i] = pat[i] * 0.6 + splash[i] * 0.5;
    mix(
      out,
      pat,
      sampleRate,
      rand() * (length / sampleRate - 0.06),
      0.1 + rand() ** 2 * 0.45,
      (t) => Math.exp(-t / 0.012),
    );
  }
  return normalise(wrapLoop(out, sampleRate, fade), 0.7);
}

/**
 * The Neak Ta's shadow gone in an instant: a breath of air drawn in hard and cut
 * dead, a dull blow of pressure where it stood, the brass ring the Audio Design
 * Document gives the Neak Ta (section 5), and the leaves settling after. About
 * 1.6 s. For the figure by the shrine (Apparitions).
 */
export function shadowVanish(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(1.6, sampleRate);
  const out = new Float32Array(length);
  const cut = 0.32;
  // The intake, swelling until it stops dead (a few milliseconds, so it doesn't click).
  const air = biquad(
    biquad(noise(seconds(cut + 0.01, sampleRate), rand), sampleRate, "bandpass", 1300, 0.6),
    sampleRate,
    "lowpass",
    4000,
    0.7,
  );
  mix(out, air, sampleRate, 0, 0.9, (t) =>
    t < cut ? (t / cut) ** 3 : Math.max(0, 1 - (t - cut) / 0.006),
  );
  // The blow: a low thud falling in pitch.
  const n = seconds(0.6, sampleRate);
  const thud = new Float32Array(n);
  let phase = 0;
  for (let i = 0; i < n; i++) {
    const t = i / sampleRate;
    phase += (38 + 30 * Math.exp(-t / 0.06)) / sampleRate;
    thud[i] = Math.sin(2 * Math.PI * phase);
  }
  mix(out, thud, sampleRate, cut, 1.1, (t) => (1 - Math.exp(-t / 0.004)) * Math.exp(-t / 0.18));
  // Brass: a few inharmonic partials of a struck bowl, ringing away.
  const ring = new Float32Array(seconds(1.2, sampleRate));
  const base = 196 + rand() * 20;
  for (const [ratio, gain, decayS] of [
    [1, 1, 0.6],
    [2.76, 0.5, 0.35],
    [5.4, 0.25, 0.2],
  ]) {
    for (let i = 0; i < ring.length; i++) {
      const t = i / sampleRate;
      ring[i] += Math.sin(2 * Math.PI * base * ratio * t) * gain * Math.exp(-t / decayS);
    }
  }
  mix(out, ring, sampleRate, cut, 0.18, (t) => 1 - Math.exp(-t / 0.003));
  // The leaves settling where it stood.
  const tick = noise(seconds(0.02, sampleRate), rand);
  for (let k = 0; k < 40; k++) {
    const leaf = biquad(tick, sampleRate, "bandpass", 1500 + rand() * 3000, 2.5);
    const at = cut + 0.05 + rand() ** 1.8 * 0.9;
    mix(out, leaf, sampleRate, at, 0.12 + rand() * 0.18, (t) => Math.exp(-t / 0.004));
  }
  return normalise(out, 0.85);
}

/** A long, low breath let out close by, with a catch at the end. */
export function breathOut(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(2.2, sampleRate);
  const air = biquad(
    biquad(noise(length, rand), sampleRate, "bandpass", 650, 0.9),
    sampleRate,
    "lowpass",
    1800,
    0.7,
  );
  const out = new Float32Array(length);
  for (let i = 0; i < length; i++) {
    const t = i / sampleRate;
    const env = Math.min(1, t / 0.25) * Math.max(0, 1 - t / 1.9) ** 1.5;
    const rasp = 1 + 0.35 * Math.sin(t * 2 * Math.PI * (38 + 10 * t));
    out[i] = air[i] * env * rasp;
  }
  const hitch = biquad(noise(seconds(0.08, sampleRate), rand), sampleRate, "bandpass", 420, 3);
  mix(out, hitch, sampleRate, 1.85, 0.8, (t) => Math.sin((Math.PI * t) / 0.08));
  return normalise(out, 0.7);
}

/** A dead branch snapping underfoot somewhere off in the trees. */
export function branchSnap(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(0.6, sampleRate);
  const out = new Float32Array(length);
  for (let k = 0; k < 3; k++) {
    const crack = biquad(
      noise(seconds(0.03, sampleRate), rand),
      sampleRate,
      "bandpass",
      1800 + rand() * 1200,
      1.2,
    );
    mix(out, crack, sampleRate, 0.02 + k * (0.03 + rand() * 0.04), 1 - k * 0.25, (t) =>
      Math.exp(-t / 0.006),
    );
  }
  const thud = biquad(noise(seconds(0.2, sampleRate), rand), sampleRate, "lowpass", 300, 0.8);
  mix(out, thud, sampleRate, 0.05, 0.5, (t) => Math.exp(-t / 0.05));
  return normalise(out, 0.75);
}
