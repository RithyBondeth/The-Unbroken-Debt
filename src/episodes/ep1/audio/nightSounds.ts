import {
  biquad,
  bubble,
  formant,
  mix,
  modal,
  noise,
  normalise,
  stickSlip,
  wrapLoop,
} from "../../../audio/synth";

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
    for (let h = 0; h < harmonics.length; h++) v += harmonics[h] * Math.sin(phase * (h + 1));
    out[i] = v;
  }
  return out;
}

/**
 * An animal's voice: a pulse train at `pitch(t)` (a glottis, a syrinx, a vocal
 * sac) with jitter, through the formants of its mouth or throat, plus breath.
 */
function call(
  length: number,
  sampleRate: number,
  rand: () => number,
  pitch: (t: number) => number,
  formants: [number, number, number][],
  breathiness = 0.15,
  jitter = 0.01,
): Float32Array {
  // The source: each cycle the folds open slowly and snap shut, a ramp then a
  // drop, so the harmonics fall away about as a real voice's do.
  const pulses = new Float32Array(length);
  let phase = 0;
  for (let i = 0; i < length; i++) {
    phase += (pitch(i / sampleRate) * (1 + (rand() - 0.5) * jitter)) / sampleRate;
    if (phase >= 1) phase -= 1;
    pulses[i] = phase < 0.7 ? phase / 0.7 - 0.5 : 0.5 - (phase - 0.7) / 0.3;
  }
  biquad(pulses, sampleRate, "lowpass", 4500, 0.6);
  const breath = noise(length, rand);
  for (let i = 0; i < length; i++) pulses[i] += breath[i] * breathiness * 0.1;
  return formant(pulses, sampleRate, formants);
}

/** Distance in air: the far-off highs go first. */
function far(samples: Float32Array, sampleRate: number, cutoff: number): Float32Array {
  biquad(samples, sampleRate, "lowpass", cutoff, 0.6);
  return biquad(samples, sampleRate, "lowpass", cutoff * 1.4, 0.6);
}

/**
 * Rice frogs and toads in the paddies: many voices, each a few nasal pulses
 * dropping in pitch, some answering others; a bed under everything.
 */
export function frogsLoop(sampleRate: number, rand: () => number): Float32Array {
  const fade = 0.6;
  const length = seconds(8 + fade, sampleRate);
  const out = new Float32Array(length);
  for (let k = 0; k < 100; k++) {
    const f = 280 + rand() * 650;
    const pulses = 3 + Math.floor(rand() * 7);
    const rate = 16 + rand() * 26;
    const d = pulses / rate;
    const croak = voice(
      seconds(d, sampleRate),
      sampleRate,
      (t) => f * (1 - 0.08 * ((t * rate) % 1)),
      [1, 0.7, 0.4],
    );
    const rasp = noise(croak.length, rand);
    for (let i = 0; i < croak.length; i++) {
      const t = i / sampleRate;
      croak[i] = (croak[i] + rasp[i] * 0.25) * Math.max(0, Math.sin(Math.PI * t * rate)) ** 3;
    }
    mix(
      out,
      biquad(croak, sampleRate, "bandpass", f * 1.6, 1.1),
      sampleRate,
      0.1 + rand() * (8 + fade - d - 0.2),
      0.25 + rand() * 0.75,
      () => 1,
    );
  }
  return normalise(wrapLoop(far(out, sampleRate, 2400), sampleRate, fade), 0.8);
}

/**
 * Night insects: field crickets each chirping on their own steady beat (three
 * or four pulses of a pure high tone), a tree cricket's continuous trill, and
 * the faint shimmer of many more beyond.
 */
export function cricketsLoop(sampleRate: number, rand: () => number): Float32Array {
  const loop = 4;
  const length = seconds(loop, sampleRate);
  const out = new Float32Array(length);
  // Each cricket's beat divides the loop, so the pattern repeats seamlessly.
  for (let k = 0; k < 9; k++) {
    const f = 3900 + rand() * 1500;
    const beats = 6 + Math.floor(rand() * 6);
    const period = loop / beats;
    const syllables = 3 + Math.floor(rand() * 2);
    const offset = rand() * period;
    const gain = 0.25 + rand() * 0.75;
    for (let b = 0; b < beats; b++)
      for (let s = 0; s < syllables; s++) {
        const at = (offset + b * period + s * 0.034) % loop;
        const n = seconds(0.022, sampleRate);
        const start = seconds(at, sampleRate);
        for (let i = 0; i < n; i++) {
          const t = i / sampleRate;
          out[(start + i) % length] +=
            Math.sin(2 * Math.PI * f * (1 - 0.02 * (t / 0.022)) * t) *
            Math.sin((Math.PI * t) / 0.022) ** 2 *
            gain;
        }
      }
  }
  // A tree cricket's trill: pulses at about 55 a second, swelling slowly.
  for (let i = 0; i < length; i++) {
    const t = i / sampleRate;
    const pulse = Math.max(0, Math.sin(2 * Math.PI * 55 * t)) ** 4;
    const swell = 0.6 + 0.4 * Math.sin((2 * Math.PI * t) / loop);
    out[i] += Math.sin(2 * Math.PI * 2950 * t) * pulse * swell * 0.25;
  }
  // The shimmer of thousands further off.
  const shimmer = biquad(noise(length, rand), sampleRate, "bandpass", 4700, 4);
  for (let i = 0; i < length; i++) out[i] += shimmer[i] * 0.12;
  return normalise(out, 0.6);
}

/**
 * A tokay gecko under the eaves: a dry throaty rattle, then "to-kay" five
 * times, loud and nasal, each one a little weaker and slower.
 */
export function geckoCall(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(5, sampleRate);
  const out = new Float32Array(length);
  const rattle = modal(
    stickSlip(
      seconds(0.5, sampleRate),
      sampleRate,
      rand,
      () => 28,
      (t) => Math.min(1, (0.5 - t) / 0.2),
      0.3,
    ),
    sampleRate,
    [
      [620, 0.012, 1],
      [1150, 0.008, 0.6],
    ],
  );
  mix(out, rattle, sampleRate, 0.05, 0.05, () => 1);
  let at = 0.8;
  for (let k = 0; k < 5; k++) {
    const to = call(seconds(0.16, sampleRate), sampleRate, rand, (t) => 210 + t * 300, [
      [560 + k * 8, 140, 1],
      [1300, 220, 0.6],
      [2400, 350, 0.25],
    ]);
    const kay = call(seconds(0.27, sampleRate), sampleRate, rand, (t) => 260 - t * 180, [
      [720, 160, 1],
      [1650, 260, 0.6],
      [2600, 380, 0.25],
    ]);
    mix(out, to, sampleRate, at, 0.9 - k * 0.1, (t) => Math.sin((Math.PI * t) / 0.16) ** 0.7);
    mix(out, kay, sampleRate, at + 0.2, 1 - k * 0.1, (t) => Math.sin((Math.PI * t) / 0.27) ** 0.7);
    at += 0.75 + k * 0.08;
  }
  return normalise(out, 0.7);
}

/**
 * A village dog howling far off: a rich, breathy voice rising, holding with a
 * waver and falling away, a second dog joining under it, the highs lost to distance.
 */
export function dogHowl(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(3.6, sampleRate);
  const wobble = 5 + rand() * 2;
  const mouth: [number, number, number][] = [
    [620, 120, 1],
    [1180, 200, 0.45],
    [2400, 320, 0.15],
  ];
  const howl = call(
    length,
    sampleRate,
    rand,
    (t) =>
      430 +
      240 * Math.sin(Math.min(1, t / 1.2) * Math.PI * 0.5) -
      130 * Math.max(0, t - 2.3) +
      10 * Math.sin(t * wobble * 2 * Math.PI),
    mouth,
    0.35,
    0.006,
  );
  const second = call(
    length,
    sampleRate,
    rand,
    (t) => 380 + 170 * Math.sin(Math.min(1, Math.max(0, t - 0.6) / 1.1) * Math.PI * 0.5),
    mouth,
    0.4,
    0.008,
  );
  for (let i = 0; i < length; i++) {
    const t = i / sampleRate;
    const one = Math.min(1, t / 0.4) * Math.min(1, (3.6 - t) / 0.8);
    const two =
      t > 0.6 ? Math.min(1, (t - 0.6) / 0.5) * Math.min(1, Math.max(0, 3.1 - t) / 0.7) : 0;
    howl[i] = howl[i] * one + second[i] * two * 0.5;
  }
  return normalise(far(howl, sampleRate, 1500), 0.6);
}

/** Dogs barking in another compound: a few rough, falling barks, one answering. */
export function dogBarks(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(2.4, sampleRate);
  const out = new Float32Array(length);
  for (let k = 0; k < 4; k++) {
    const d = 0.13 + rand() * 0.07;
    const f0 = 340 + rand() * 120;
    const bark = call(
      seconds(d, sampleRate),
      sampleRate,
      rand,
      (t) => f0 * (1.25 - (t / d) * 0.55),
      [
        [700 + rand() * 120, 200, 1],
        [1500, 280, 0.6],
        [2600, 400, 0.3],
      ],
      1.6,
      0.05,
    );
    mix(
      out,
      bark,
      sampleRate,
      0.1 + k * (0.38 + rand() * 0.25),
      k === 3 ? 0.55 : 1,
      (t) => (1 - Math.exp(-t / 0.006)) * Math.max(0, 1 - t / d) ** 0.6,
    );
  }
  return normalise(far(out, sampleRate, 2200), 0.6);
}

/**
 * An owl: two soft, breathy hoots, the second longer and falling, as a
 * brown wood owl calls across the fields.
 */
export function owlHoot(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(2.2, sampleRate);
  const out = new Float32Array(length);
  for (const [at, d, f] of [
    [0.1, 0.32, 345],
    [0.72, 0.72, 322 + rand() * 20],
  ]) {
    const hoot = voice(
      seconds(d, sampleRate),
      sampleRate,
      (t) => f * (1 + 0.03 * Math.sin((Math.PI * t) / d)) - t * 28,
      [1, 0.12, 0.04],
    );
    const air = biquad(noise(hoot.length, rand), sampleRate, "bandpass", f * 2, 2);
    for (let i = 0; i < hoot.length; i++) hoot[i] += air[i] * 0.35;
    mix(
      out,
      hoot,
      sampleRate,
      at,
      1,
      (t) => Math.min(1, t / 0.04) * Math.sin((Math.PI * t) / d) ** 1.2,
    );
  }
  return normalise(far(out, sampleRate, 2000), 0.6);
}

/** Crows startled in a dead tree: harsh, rasping "kaaa"s, wings beating between. */
export function crowCaws(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(2, sampleRate);
  const out = new Float32Array(length);
  for (let k = 0; k < 3; k++) {
    const d = 0.26 + rand() * 0.12;
    const caw = call(
      seconds(d, sampleRate),
      sampleRate,
      rand,
      (t) => 560 - t * 260,
      [
        [1250 + rand() * 150, 260, 1],
        [1900, 320, 0.7],
        [3100, 500, 0.35],
      ],
      2.2,
      0.12,
    );
    mix(
      out,
      caw,
      sampleRate,
      0.05 + k * 0.55,
      1,
      (t) => Math.min(1, t / 0.02) * Math.sin((Math.PI * t) / d) ** 0.5,
    );
  }
  // Wing beats: soft thumps of air.
  for (let k = 0; k < 6; k++) {
    const beat = biquad(noise(seconds(0.06, sampleRate), rand), sampleRate, "lowpass", 600, 0.7);
    mix(out, beat, sampleRate, 0.4 + k * 0.17 + rand() * 0.03, 0.5, (t) =>
      Math.sin((Math.PI * t) / 0.06),
    );
  }
  return normalise(far(out, sampleRate, 3500), 0.6);
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
 * Steady rain in the village at night, heard out of doors: a soft hiss, a fine
 * patter on the forest's leaves, heavier drops on banana leaves and thatch
 * close by, and drops ringing in the puddles of the courtyard. Gentle in
 * level; it should sit under everything else.
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
  // Puddles: a drop that traps a bubble rings, rising, for a few milliseconds.
  for (let k = 0; k < 420; k++)
    mix(
      out,
      bubble(sampleRate, 900 + rand() * 2600, 0.004 + rand() * 0.008),
      sampleRate,
      rand() * (length / sampleRate - 0.05),
      0.04 + rand() ** 2 * 0.2,
      () => 1,
    );
  return normalise(wrapLoop(out, sampleRate, fade), 0.7);
}

/**
 * The Neak Ta's shadow gone in an instant: a breath of air drawn in hard over
 * the grind of stone, cut dead, a dull blow of pressure where it stood, the
 * brass ring the Audio Design Document gives the Neak Ta (section 5), and the
 * leaves settling after. About 1.6 s. For the figure by the shrine (Apparitions).
 */
export function shadowVanish(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(1.6, sampleRate);
  const out = new Float32Array(length);
  const cut = 0.32;
  // The intake, swelling until it stops dead (a few milliseconds, so it doesn't click).
  const air = formant(noise(seconds(cut + 0.01, sampleRate), rand), sampleRate, [
    [520, 200, 1],
    [1250, 300, 0.8],
    [2600, 600, 0.4],
  ]);
  mix(out, air, sampleRate, 0, 1.4, (t) =>
    t < cut ? (t / cut) ** 3 : Math.max(0, 1 - (t - cut) / 0.006),
  );
  // Stone ground against stone under it, slowed and heavy.
  const grind = modal(
    stickSlip(
      seconds(cut + 0.01, sampleRate),
      sampleRate,
      rand,
      (t) => 22 + 40 * (t / cut),
      (t) => (t < cut ? (t / cut) ** 1.5 : 0),
      0.9,
    ),
    sampleRate,
    [
      [180, 0.02, 1],
      [410, 0.012, 0.7],
      [870, 0.008, 0.45],
      [1600, 0.004, 0.3],
    ],
  );
  mix(out, grind, sampleRate, 0, 2.2, (t) => Math.max(0, 1 - Math.max(0, t - cut) / 0.006));
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
  // Brass: a struck bowl's inharmonic partials, two of each a few hertz apart so they beat.
  const strike = new Float32Array(seconds(1.25, sampleRate));
  strike[0] = 1;
  const base = 196 + rand() * 20;
  const ring = modal(strike, sampleRate, [
    [base, 0.7, 1],
    [base * 1.006, 0.7, 0.8],
    [base * 2.76, 0.4, 0.5],
    [base * 2.77, 0.4, 0.35],
    [base * 5.4, 0.22, 0.25],
    [base * 8.9, 0.12, 0.12],
  ]);
  mix(out, ring, sampleRate, cut, 0.2, () => 1);
  // The leaves settling where it stood.
  const tick = noise(seconds(0.02, sampleRate), rand);
  for (let k = 0; k < 40; k++) {
    const leaf = biquad(tick, sampleRate, "bandpass", 1500 + rand() * 3000, 2.5);
    const at = cut + 0.05 + rand() ** 1.8 * 0.9;
    mix(out, leaf, sampleRate, at, 0.12 + rand() * 0.18, (t) => Math.exp(-t / 0.004));
  }
  return normalise(out, 0.85);
}

/**
 * A long, low breath let out close by: air through a slack, wet mouth, its
 * vowel closing as the lungs empty, and the throat catching at the end.
 */
export function breathOut(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(2.2, sampleRate);
  const source = noise(length, rand);
  const open = formant(source, sampleRate, [
    [560, 180, 1],
    [1050, 240, 0.6],
    [2350, 400, 0.3],
  ]);
  const closed = formant(source, sampleRate, [
    [380, 140, 1],
    [800, 200, 0.5],
    [2200, 400, 0.2],
  ]);
  const out = new Float32Array(length);
  for (let i = 0; i < length; i++) {
    const t = i / sampleRate;
    const env = Math.min(1, t / 0.25) * Math.max(0, 1 - t / 1.9) ** 1.5;
    const k = Math.min(1, t / 1.6);
    const rasp = 1 + 0.3 * Math.sin(t * 2 * Math.PI * (38 + 10 * t));
    out[i] = (open[i] * (1 - k) + closed[i] * k) * env * rasp;
  }
  // The catch: the glottis clicking shut a few times, almost a word.
  const fry = stickSlip(
    seconds(0.22, sampleRate),
    sampleRate,
    rand,
    () => 42,
    (t) => Math.sin((Math.PI * t) / 0.22),
    0.5,
  );
  const hitch = formant(fry, sampleRate, [
    [420, 120, 1],
    [880, 180, 0.4],
  ]);
  mix(out, hitch, sampleRate, 1.8, 3, () => 1);
  return normalise(out, 0.7);
}

/**
 * A dead branch snapping underfoot somewhere off in the trees: the first
 * crack, the fibres tearing, the second crack as it gives, then the wet
 * leaves crushed under the weight.
 */
export function branchSnap(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(0.6, sampleRate);
  const out = new Float32Array(length);
  const wood: [number, number, number][] = [
    [1650 + rand() * 300, 0.006, 1],
    [2700 + rand() * 400, 0.004, 0.8],
    [4100, 0.003, 0.5],
    [880, 0.009, 0.6],
  ];
  const fibres = new Float32Array(length);
  fibres[seconds(0.02, sampleRate)] = 1;
  for (let k = 0; k < 28; k++)
    fibres[seconds(0.025 + rand() ** 1.5 * 0.06, sampleRate)] += (rand() - 0.5) * 0.7;
  fibres[seconds(0.09 + rand() * 0.03, sampleRate)] = 0.8;
  const crack = modal(fibres, sampleRate, wood);
  for (let i = 0; i < length; i++) out[i] += crack[i] * 1.2;
  mix(
    out,
    biquad(noise(seconds(0.02, sampleRate), rand), sampleRate, "highpass", 2500, 0.7),
    sampleRate,
    0.02,
    0.6,
    (t) => Math.exp(-t / 0.003),
  );
  const thud = biquad(noise(seconds(0.2, sampleRate), rand), sampleRate, "lowpass", 300, 0.8);
  mix(out, thud, sampleRate, 0.05, 0.5, (t) => Math.exp(-t / 0.05));
  const leaves = biquad(noise(seconds(0.35, sampleRate), rand), sampleRate, "bandpass", 2400, 0.8);
  mix(
    out,
    leaves,
    sampleRate,
    0.1,
    0.18,
    (t) => (0.5 + 0.5 * Math.sin(t * 90 + rand())) * Math.sin((Math.PI * t) / 0.35) ** 2,
  );
  return normalise(out, 0.75);
}

/**
 * Dawn (R01): the rain over, water still dripping off the eaves, a bulbul's
 * bubbling phrases, a magpie-robin's clear whistles, and a spotted dove
 * cooing further off. Loops without a click.
 */
export function dawnBirds(sampleRate: number, rand: () => number): Float32Array {
  const fade = 0.5;
  const length = seconds(12 + fade, sampleRate);
  const out = new Float32Array(length);
  const whistle = (at: number, d: number, pitch: (u: number) => number, gain: number) => {
    const n = seconds(d, sampleRate);
    const note = new Float32Array(n);
    let phase = 0;
    for (let i = 0; i < n; i++) {
      const u = i / n;
      phase += pitch(u) / sampleRate;
      note[i] =
        (Math.sin(2 * Math.PI * phase) + 0.12 * Math.sin(4 * Math.PI * phase)) *
        Math.sin(Math.PI * u) ** 1.5;
    }
    mix(out, note, sampleRate, at, gain, () => 1);
  };
  // Bulbul: quick, liquid notes in a tumbling phrase.
  for (let phrase = 0; phrase < 5; phrase++) {
    let at = 0.3 + phrase * 2.4 + rand() * 0.5;
    for (let k = 0; k < 5 + rand() * 3; k++) {
      const f = 1500 + rand() * 1300,
        g = f + (rand() - 0.5) * 900;
      const d = 0.05 + rand() * 0.07;
      whistle(at, d, (u) => f + (g - f) * u + 160 * Math.sin(u * Math.PI * 3), 0.14);
      at += d + 0.02 + rand() * 0.04;
    }
  }
  // Magpie-robin: long, clear whistles, sliding.
  for (let k = 0; k < 7; k++) {
    const f = 2200 + rand() * 1400;
    whistle(
      1 + rand() * 10.5,
      0.18 + rand() * 0.2,
      (u) => f * (1 + (rand() < 0.5 ? 0.3 : -0.25) * u),
      0.09,
    );
  }
  // Spotted dove, far off: soft, low coos.
  for (const at of [2.1, 2.55, 2.85, 7.3, 7.75, 8.05]) {
    whistle(at, 0.24, (u) => 520 - 60 * u, 0.06);
  }
  // Drips off the eaves into puddles.
  for (let k = 0; k < 40; k++)
    mix(
      out,
      bubble(sampleRate, 700 + rand() * 1600, 0.008 + rand() * 0.01),
      sampleRate,
      rand() * 12.3,
      0.08 + rand() * 0.08,
      () => 1,
    );
  // The morning air: a soft wash of distant life.
  const air = biquad(noise(length, rand), sampleRate, "bandpass", 900, 0.6);
  for (let i = 0; i < length; i++) out[i] += air[i] * 0.012;
  return normalise(wrapLoop(out, sampleRate, fade), 0.6);
}
