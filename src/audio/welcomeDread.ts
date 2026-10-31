/**
 * Original dread for the title screen, synthesised so nothing is downloaded:
 * a funeral chant that has gone wrong, a bed of whispers, creaks and knocks, and
 * stingers that land on the Neak Ta's coming and going. Pure functions over
 * Float32Array (stereo as [left, right]) so they can be tested without audio.
 */
import { biquad, noise, seededRandom } from "./synth";
import { creak, hall, knock, loopify, place, sweepBand, whisper, type Stereo } from "./dread";

function normalise(data: Float32Array, peak: number): Float32Array {
  let max = 0;
  for (const v of data) max = Math.max(max, Math.abs(v));
  if (max > 0) for (let i = 0; i < data.length; i++) data[i] *= peak / max;
  return data;
}

/** Seconds from the start of a stinger to its hit; the screen swaps the figure on it. */
export const STINGER_HIT = 0.9;

export type Stinger = "appear" | "near" | "vanish";

/** Male vowel formants (Hz): the chant never says words, only their colour. */
const VOWELS: Record<string, [number, number, number]> = {
  a: [730, 1090, 2440],
  o: [570, 840, 2410],
  u: [300, 870, 2240],
  e: [530, 1840, 2480],
  m: [250, 950, 2200],
};

/** One-pole smoothing in place, so vowels and loudness glide like a voice. */
function glide(track: Float32Array, rate: number, seconds: number): Float32Array {
  const k = 1 - Math.exp(-1 / (seconds * rate));
  let y = track[0];
  for (let i = 0; i < track.length; i++) track[i] = y += (track[i] - y) * k;
  return track;
}

/** Band-pass with a per-sample coefficient track (2 sin(pi f / rate)), read `delay` samples late. */
function formantBand(
  input: Float32Array,
  coef: Float32Array,
  delay: number,
  q: number,
): Float32Array {
  const out = new Float32Array(input.length);
  const damp = 1 / q;
  let low = 0,
    band = 0;
  for (let i = 0; i < input.length; i++) {
    const f = coef[Math.max(0, i - delay)];
    low += f * band;
    band += f * (input[i] - low - damp * band);
    out[i] = band;
  }
  return out;
}

/**
 * A funeral chant gone wrong, 32 s loop: low men reciting in unison, phrase
 * after phrase, each ending on a long falling hum. One voice sings a semitone
 * flat, one an octave below, and the hall smears it all together.
 */
export function funeralChant(rate: number): Stereo {
  const length = rate * 34;
  const rand = seededRandom(1932);
  const tracks = [0, 1, 2].map(() => new Float32Array(length));
  const amp = new Float32Array(length);
  const pitch = new Float32Array(length).fill(1);
  const onset = new Float32Array(length);
  const fill = (a: Float32Array, from: number, to: number, value: number) =>
    a.fill(value, Math.round(from * rate), Math.min(length, Math.round(to * rate)));
  let at = 0.4;
  let vowel = VOWELS.o;
  while (at < 33) {
    const syllables = 10 + Math.floor(rand() * 7);
    for (let n = 0; n < syllables && at < 33; n++) {
      const last = n === syllables - 1;
      const seconds = last ? 1.7 + rand() * 0.8 : 0.28 + rand() * 0.06;
      vowel = last ? VOWELS.o : VOWELS["aoueoa"[Math.floor(rand() * 6)]];
      tracks.forEach((track, k) => fill(track, at, at + seconds, vowel[k]));
      if (last) {
        // The held syllable closes into a hum and sags flat.
        tracks.forEach((track, k) => fill(track, at + 0.5, at + seconds, VOWELS.m[k]));
        fill(pitch, at + 0.3, at + seconds, 0.944);
      }
      fill(amp, at, at + seconds - 0.05, last ? 1 : 0.82);
      fill(amp, at + seconds - 0.05, at + seconds, 0.35);
      if (!last && rand() < 0.6) fill(onset, at, at + 0.022, 1);
      at += seconds;
    }
    fill(amp, at, at + 1.1, 0);
    at += 0.9 + rand() * 0.5;
  }
  tracks.forEach((track) => glide(track, rate, 0.03));
  glide(amp, rate, 0.025);
  glide(pitch, rate, 0.35);
  const coefs = tracks.map((track) =>
    track.map((f) => 2 * Math.sin((Math.PI * Math.min(f, rate / 6)) / rate)),
  );
  const consonant = biquad(noise(length, rand), rate, "bandpass", Math.min(2600, rate * 0.4), 1.2);

  // Semitones from G2, level, lag (s), pan (-1 left .. 1 right).
  const voices: [number, number, number, number][] = [
    [0, 1, 0, 0],
    [0.08, 0.8, 0.023, -0.6],
    [-0.1, 0.8, 0.041, 0.6],
    [-12, 0.6, 0.012, 0],
    [-1, 0.45, 0.067, 0.35],
    [7, 0.22, 0.03, -0.35],
  ];
  const sides: Stereo = [new Float32Array(length), new Float32Array(length)];
  voices.forEach(([semitones, level, lag, pan], v) => {
    const base = 98 * 2 ** (semitones / 12);
    const delay = Math.round(lag * rate);
    const source = new Float32Array(length);
    let phase = 0,
      drift = 0;
    for (let i = 0; i < length; i++) {
      drift += (rand() - 0.5) * 0.0004 - drift * 0.0005;
      const vibrato = 1 + 0.003 * Math.sin((i / rate) * 2 * Math.PI * (4.8 + v * 0.37));
      phase = (phase + (base * pitch[Math.max(0, i - delay)] * vibrato * (1 + drift)) / rate) % 1;
      source[i] = phase * 2 - 1;
    }
    const [f1, f2, f3] = coefs.map((coef, k) => formantBand(source, coef, delay, [6, 9, 12][k]));
    const left = Math.cos(((pan + 1) * Math.PI) / 4);
    const right = Math.sin(((pan + 1) * Math.PI) / 4);
    for (let i = 0; i < length; i++) {
      const j = Math.max(0, i - delay);
      let sample = (f1[i] + f2[i] * 0.55 + f3[i] * 0.2) * amp[j] * level;
      if (v < 2) sample += consonant[i] * onset[j] * 0.35;
      sides[0][i] += sample * left;
      sides[1][i] += sample * right;
    }
  });
  return sides.map((side) =>
    normalise(
      loopify(
        hall(biquad(side, rate, "lowpass", Math.min(4200, rate * 0.45), 0.7), rate, 0.42),
        rate,
        2,
      ),
      0.3,
    ),
  ) as Stereo;
}

/** Sparse whispers, creaks and three slow knocks over a 41 s loop. */
export function whisperBed(rate: number): Stereo {
  const length = rate * 43;
  const sides: Stereo = [new Float32Array(length), new Float32Array(length)];
  const rand = seededRandom(1931);
  for (const [at, seconds, side] of [
    [3.2, 1.8, 0],
    [9.6, 2.4, 1],
    [10.9, 1.2, 0],
    [19.5, 2.8, 1],
    [27.8, 1.6, 0],
    [33.4, 2.2, 1],
    [35.1, 1.4, 1],
  ] as const) {
    const w = whisper(rate, rand, seconds);
    place(sides[side], w, rate, at, 0.7);
    place(sides[1 - side], w, rate, at + 0.012, 0.18);
  }
  for (const [at, side] of [
    [6.4, 1],
    [15.2, 0],
    [24.6, 1],
    [38.0, 0],
  ] as const) {
    const c = creak(rate, rand, 0.7 + rand() * 0.6);
    place(sides[side], c, rate, at, 1);
    place(sides[1 - side], c, rate, at + 0.02, 0.4);
  }
  const k = knock(rate);
  for (const at of [29.5, 30.6, 31.7]) {
    place(sides[0], k, rate, at, 0.8);
    place(sides[1], k, rate, at, 0.8);
  }
  return [normalise(loopify(sides[0], rate, 2), 0.2), normalise(loopify(sides[1], rate, 2), 0.2)];
}

/**
 * A swell that lands on STINGER_HIT. `appear`: sub drop and a cracked bell;
 * `near`: the same with a shrieking string cluster; `vanish`: an inhale and a thud.
 */
export function stinger(rate: number, kind: Stinger): Stereo {
  const seconds = kind === "near" ? 4.5 : kind === "appear" ? 3.6 : 2.2;
  const length = Math.round(rate * seconds);
  const rand = seededRandom(kind === "near" ? 13 : kind === "appear" ? 7 : 3);
  const mono = new Float32Array(length);
  const hit = Math.round(STINGER_HIT * rate);
  const air = noise(length, rand);
  if (kind === "vanish") {
    // A sharp breath in, through the teeth.
    const breath = sweepBand(air, rate, (t) => 900 + 2600 * Math.min(1, t / STINGER_HIT), 3);
    for (let i = 0; i < hit; i++) mono[i] += breath[i] * (i / hit) ** 2 * 0.6;
  } else {
    // Rising air and a cluster bending upward into the hit.
    const rise = biquad(air.slice(), rate, "highpass", 1200, 0.7);
    for (let i = 0; i < hit; i++) {
      const t = i / rate;
      const k = (i / hit) ** 3;
      mono[i] += rise[i] * k * 0.5;
      for (const f of [220, 233.1, 311.1])
        mono[i] += Math.sin(2 * Math.PI * f * t * (1 + 0.25 * k)) * k * 0.12;
    }
  }
  for (let i = hit; i < length; i++) {
    const t = (i - hit) / rate;
    // Sub drop.
    mono[i] +=
      Math.sin(2 * Math.PI * (52 - 16 * Math.min(1, t)) * t) *
      Math.exp(-t * (kind === "vanish" ? 9 : 2.2)) *
      0.9;
    if (kind !== "vanish") {
      // Cracked bell: inharmonic partials beating against each other.
      for (const [f, d] of [
        [311.3, 1.3],
        [467.9, 0.9],
        [733.6, 0.7],
        [1187.4, 0.45],
        [1661.9, 0.3],
      ])
        mono[i] += Math.sin(2 * Math.PI * f * t) * Math.exp(-t / d) * 0.14;
      mono[i] += air[i] * Math.exp(-t * 14) * 0.5;
    }
  }
  const left = mono.slice();
  const right = mono.slice();
  if (kind === "near") {
    // Shrieking strings: detuned saws a semitone apart with a fast, nervous vibrato.
    const strings: Stereo = [new Float32Array(length), new Float32Array(length)];
    [880, 932.3, 987.8, 1046.5, 1108.7].forEach((f, n) => {
      let phase = 0;
      for (let i = hit; i < length; i++) {
        const t = (i - hit) / rate;
        phase = (phase + (f * (1 + 0.012 * Math.sin(t * 2 * Math.PI * (7 + n)))) / rate) % 1;
        const env = Math.min(1, t / 0.03) * Math.exp(-t / 1.4);
        strings[n % 2][i] += (phase * 2 - 1) * env * 0.16;
      }
    });
    biquad(strings[0], rate, "highpass", 600, 0.7);
    biquad(strings[1], rate, "highpass", 600, 0.7);
    const shriek = whisper(rate, rand, 1.6);
    for (let i = 0; i < length; i++) {
      left[i] += strings[0][i] + (i >= hit && i - hit < shriek.length ? shriek[i - hit] * 0.9 : 0);
      right[i] += strings[1][i];
    }
  }
  // Fade the tail so a stinger never ends on a click.
  const tail = Math.round(rate * 0.25);
  for (let i = 0; i < tail; i++) {
    const g = i / tail;
    left[length - 1 - i] *= g;
    right[length - 1 - i] *= g;
  }
  const peak = kind === "near" ? 0.95 : kind === "appear" ? 0.7 : 0.5;
  let max = 0;
  for (let i = 0; i < length; i++) max = Math.max(max, Math.abs(left[i]), Math.abs(right[i]));
  for (let i = 0; i < length; i++) {
    left[i] *= peak / max;
    right[i] *= peak / max;
  }
  return [left, right];
}

/** Everything the title screen plays, synthesised in one pass. */
export interface DreadBank {
  rate: number;
  chant: Stereo;
  bed: Stereo;
  stingers: Record<Stinger, Stereo>;
}

export function synthesizeDread(rate: number): DreadBank {
  return {
    rate,
    chant: funeralChant(rate),
    bed: whisperBed(rate),
    stingers: {
      appear: stinger(rate, "appear"),
      near: stinger(rate, "near"),
      vanish: stinger(rate, "vanish"),
    },
  };
}

/**
 * Synthesis takes a couple of seconds of CPU, so it runs in a worker and the
 * menu never stalls on the first click; without workers it runs inline.
 */
export function loadDread(rate: number): Promise<DreadBank> {
  if (typeof Worker === "undefined") return Promise.resolve(synthesizeDread(rate));
  return new Promise<DreadBank>((resolve) => {
    const worker = new Worker(new URL("./welcomeDread.worker.ts", import.meta.url), {
      type: "module",
    });
    worker.onmessage = (event: MessageEvent<DreadBank>) => {
      worker.terminate();
      resolve(event.data);
    };
    worker.onerror = () => {
      worker.terminate();
      resolve(synthesizeDread(rate));
    };
    worker.postMessage(rate);
  });
}
