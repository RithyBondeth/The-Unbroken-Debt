import {
  biquad,
  bubble,
  formant,
  mix,
  modal,
  noise,
  normalise,
  stickSlip,
} from "../../../audio/synth";

/**
 * Synthesised stand-ins for the vigil's sounds (Audio Design Document,
 * section 9) until the recordings exist: the match, the lamp, kerosene poured,
 * incense whispers. Mono, peak 0.9 or less, pure functions.
 */

const seconds = (s: number, sampleRate: number) => Math.round(s * sampleRate);

/**
 * A safety match struck on the box: the head rasping over the grit, the
 * spark crackling, the flare catching with a soft "whumph", then the flame's
 * hiss, sputtering once.
 */
export function matchStrike(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(1.2, sampleRate);
  const out = new Float32Array(length);
  // The rasp: the head catching on each grain of the striker.
  const grit = stickSlip(
    seconds(0.13, sampleRate),
    sampleRate,
    rand,
    (t) => 900 + 2400 * (t / 0.13),
    (t) => Math.sin((Math.PI * t) / 0.13) ** 0.6,
    1,
  );
  const rasp = modal(grit, sampleRate, [
    [3600, 0.0015, 1],
    [5900, 0.001, 0.8],
    [2300, 0.002, 0.5],
  ]);
  const scrape = biquad(noise(grit.length, rand), sampleRate, "bandpass", 4200, 1.2);
  for (let i = 0; i < grit.length; i++)
    rasp[i] = rasp[i] * 1.4 + scrape[i] * 0.35 * Math.sin((Math.PI * i) / grit.length);
  mix(out, rasp, sampleRate, 0.02, 1, () => 1);
  // The spark: a few sharp crackles as the chemicals go.
  for (let k = 0; k < 9; k++)
    mix(
      out,
      biquad(noise(seconds(0.004, sampleRate), rand), sampleRate, "highpass", 2500, 0.7),
      sampleRate,
      0.13 + rand() * 0.06,
      0.5 + rand() * 0.5,
      (t) => Math.exp(-t / 0.0012),
    );
  // The flare: a soft rush of air, swelling and settling.
  const flare = biquad(noise(seconds(0.5, sampleRate), rand), sampleRate, "lowpass", 1300, 0.6);
  mix(out, flare, sampleRate, 0.14, 1.3, (t) => Math.min(1, t / 0.025) * Math.exp(-t / 0.13));
  const whumph = biquad(noise(seconds(0.2, sampleRate), rand), sampleRate, "lowpass", 220, 0.8);
  mix(out, whumph, sampleRate, 0.15, 1.6, (t) => Math.min(1, t / 0.01) * Math.exp(-t / 0.05));
  // The flame burning: a soft hiss with a sputter.
  const hiss = biquad(noise(length, rand), sampleRate, "bandpass", 2400, 0.8);
  for (let i = seconds(0.22, sampleRate); i < length; i++) {
    const t = i / sampleRate - 0.22;
    out[i] += hiss[i] * 0.1 * Math.min(1, t / 0.1) * Math.min(1, (0.98 - t) / 0.3);
  }
  mix(
    out,
    biquad(noise(seconds(0.03, sampleRate), rand), sampleRate, "bandpass", 900, 1),
    sampleRate,
    0.5 + rand() * 0.2,
    0.35,
    (t) => Math.exp(-t / 0.008),
  );
  return normalise(out, 0.8);
}

/**
 * The wick turned up and caught, or turned down and out: the brass wheel's
 * ratchet clicking against the wick, then the flame's soft puff.
 */
export function lampWick(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(0.45, sampleRate);
  const ratchet = new Float32Array(length);
  for (let k = 0; k < 4; k++)
    ratchet[seconds(0.008 + k * (0.028 + rand() * 0.01), sampleRate)] = 1 - k * 0.15;
  const out = modal(ratchet, sampleRate, [
    [4100, 0.004, 1],
    [6300, 0.003, 0.7],
    [2700, 0.006, 0.45],
  ]);
  for (let i = 0; i < length; i++) out[i] *= 3;
  const puff = biquad(noise(seconds(0.35, sampleRate), rand), sampleRate, "lowpass", 500, 0.7);
  mix(out, puff, sampleRate, 0.12, 0.8, (t) => Math.min(1, t / 0.05) * Math.exp(-t / 0.1));
  return normalise(out, 0.9);
}

/**
 * Kerosene poured from a bottle into the lamp's tank: the stream trickling,
 * a glug each time air bubbles back up the neck, and the tank's note rising
 * as it fills.
 */
export function pourOil(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(1.8, sampleRate);
  const stream = biquad(noise(length, rand), sampleRate, "bandpass", 1500, 1.1);
  const out = new Float32Array(length);
  for (let i = 0; i < length; i++) {
    const t = i / sampleRate;
    const flow = Math.min(1, t / 0.1) * Math.min(1, (1.8 - t) / 0.25);
    const flutter = 0.7 + 0.3 * Math.sin(t * 2 * Math.PI * 23 + Math.sin(t * 7));
    out[i] = stream[i] * 0.3 * flow * flutter;
  }
  // The glugs: air bubbling back into the bottle, about five a second.
  for (let at = 0.12; at < 1.55; at += 0.15 + rand() * 0.08)
    mix(out, bubble(sampleRate, 230 + rand() * 120, 0.018, 0.5), sampleRate, at, 0.55, () => 1);
  // The tank filling: its air column shortening, so its note rises.
  const tank = new Float32Array(length);
  let phase = 0;
  for (let i = 0; i < length; i++) {
    const t = i / sampleRate;
    phase += (480 + 380 * (t / 1.8)) / sampleRate;
    tank[i] = Math.sin(2 * Math.PI * phase);
  }
  const fill = formant(stream, sampleRate, [[600, 200, 1]]);
  for (let i = 0; i < length; i++) out[i] += tank[i] * Math.abs(fill[i]) * 0.6;
  return normalise(out, 0.6);
}

/** [F1, F2, F3] of the vowels the whispers move through: none of them make a word. */
const VOWELS: [number, number, number][] = [
  [780, 1250, 2500],
  [310, 2250, 2950],
  [360, 820, 2350],
  [520, 1850, 2600],
  [520, 900, 2450],
  [650, 1100, 2400],
];

/**
 * Whispering with no words in it, for the dying incense (A1-10): several
 * voices at different distances, each a run of syllables, a hiss or a stop
 * then a breathy vowel shaped by a mouth, rising and falling like speech you
 * cannot quite catch. Loops without a click.
 */
export function whispers(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(6, sampleRate);
  const out = new Float32Array(length);
  for (let speaker = 0; speaker < 4; speaker++) {
    // A smaller or larger mouth; nearer or further away.
    const tract = 0.88 + rand() * 0.3;
    const near = speaker === 0 ? 1 : 0.35 + rand() * 0.4;
    const voice = new Float32Array(length);
    let at = 0.3 + rand() * 1.2;
    while (at < 5.4) {
      const words = 2 + Math.floor(rand() * 4);
      for (let w = 0; w < words && at < 5.4; w++) {
        const syllables = 1 + Math.floor(rand() * 3);
        for (let s = 0; s < syllables && at < 5.4; s++) {
          const accent = s === 0 ? 1 : 0.7;
          // The consonant: s, sh, h, or a stop's burst.
          const kind = rand();
          const cLength = kind < 0.6 ? 0.05 + rand() * 0.06 : 0.012;
          const consonant = noise(seconds(cLength, sampleRate), rand);
          if (kind < 0.3) biquad(consonant, sampleRate, "highpass", 4800, 0.8);
          else if (kind < 0.5) biquad(consonant, sampleRate, "bandpass", 2800 * tract, 1.6);
          else if (kind < 0.6) biquad(consonant, sampleRate, "bandpass", 1500 * tract, 0.6);
          else biquad(consonant, sampleRate, "bandpass", 1800 + rand() * 2000, 1.2);
          mix(
            voice,
            consonant,
            sampleRate,
            at,
            (kind < 0.5 ? 0.5 : 0.8) * accent,
            (t) => Math.sin((Math.PI * t) / cLength) ** 0.8,
          );
          at += cLength * 0.8;
          // The vowel: breath through the formants of a mouth.
          const [f1, f2, f3] = VOWELS[Math.floor(rand() * VOWELS.length)];
          const d = 0.08 + rand() * 0.14;
          const vowel = formant(noise(seconds(d, sampleRate), rand), sampleRate, [
            [f1 * tract, 110, 1],
            [f2 * tract, 160, 0.7],
            [f3 * tract, 260, 0.35],
          ]);
          mix(
            voice,
            vowel,
            sampleRate,
            at,
            1.6 * accent,
            (t) => Math.min(1, t / 0.02) * Math.max(0, 1 - t / d) ** 0.7,
          );
          at += d + 0.01;
        }
        at += 0.04 + rand() * 0.12;
      }
      at += 0.3 + rand() * 0.9;
    }
    // Further voices lose their top.
    if (near < 1) biquad(voice, sampleRate, "lowpass", 2600 + near * 3000, 0.7);
    for (let i = 0; i < length; i++) out[i] += voice[i] * near;
  }
  const n = seconds(0.3, sampleRate);
  for (let i = 0; i < n; i++) {
    out[i] *= i / n;
    out[length - 1 - i] *= i / n;
  }
  return normalise(out, 0.7);
}
