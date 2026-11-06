/**
 * Episode 2's horror sound design, synthesised like the rest of the game's audio
 * (pure functions over Float32Array, mono, peak 0.9, testable without audio).
 *
 * The monks' chant is a choir of low male voices reciting on one tone in the
 * rhythm and vowels of the Pali homage "namo tassa bhagavato arahato
 * sammāsambuddhassa", three times, as Khmer monks open a recitation. It is
 * formant synthesis, not intelligible words: a stand-in until a real recorded
 * smot is approved by the cultural advisor (Cultural Guide, section 4).
 */
import { biquad, mix, noise, normalise, softClip, wrapLoop } from "@/audio/synth";

const seconds = (s: number, rate: number) => Math.round(s * rate);

/** Mixes a one-shot hit in at full level, without an envelope of its own. */
const place = (out: Float32Array, src: Float32Array, rate: number, at: number, gain: number) =>
  mix(out, src, rate, at, gain, () => 1);

/** Male vowel formants [F1, F2, F3] in Hz. */
const VOWELS = {
  a: [730, 1090, 2440],
  o: [570, 840, 2410],
  u: [300, 870, 2240],
  e: [530, 1840, 2480],
  i: [270, 2290, 3010],
  m: [250, 1000, 2500],
} as const;
type Vowel = keyof typeof VOWELS;

/** One syllable: vowel, length in beats, onset consonant, closing nasal. */
type Syllable = [Vowel, number, "" | "stop" | "s" | "h" | "n" | "r", boolean];

/** The homage, as chanted: short open syllables, long held vowels at the phrase ends. */
const HOMAGE: Syllable[] = [
  ["a", 1, "n", false],
  ["o", 1.6, "n", false],
  ["a", 1, "stop", false],
  ["a", 1, "s", false],
  ["a", 1, "stop", false],
  ["a", 1, "stop", false],
  ["a", 1, "h", false],
  ["o", 1.6, "stop", false],
  ["a", 1, "", false],
  ["a", 1, "r", false],
  ["a", 1, "h", false],
  ["o", 1.6, "stop", false],
  ["a", 1, "s", true],
  ["a", 1, "n", false],
  ["a", 1, "s", true],
  ["u", 1, "stop", false],
  ["a", 1, "stop", false],
  ["a", 2.6, "s", false],
];

/** A glottal pulse source: a raised-sine pulse a little under half the period. */
function glottal(length: number, rate: number, f0: (t: number) => number, rand: () => number) {
  const out = new Float32Array(length);
  let phase = 0;
  for (let i = 0; i < length; i++) {
    const t = i / rate;
    phase += (f0(t) * (1 + (rand() - 0.5) * 0.012)) / rate;
    phase -= Math.floor(phase);
    out[i] = phase < 0.42 ? Math.sin((Math.PI * phase) / 0.42) ** 2 - 0.3 : -0.3;
  }
  return out;
}

/** Resonates a source through three formants that move to each syllable's vowel. */
function articulate(source: Float32Array, rate: number, vowelAt: (t: number) => readonly number[]) {
  const out = new Float32Array(source.length);
  const state = [0, 0, 0].map(() => ({ x1: 0, x2: 0, y1: 0, y2: 0 }));
  const gains = [1, 0.55, 0.28];
  const block = 64;
  let coeffs: number[][] = [];
  for (let i = 0; i < source.length; i++) {
    if (i % block === 0) {
      const f = vowelAt(i / rate);
      coeffs = f.map((freq, k) => {
        const w = (2 * Math.PI * freq) / rate;
        const alpha = Math.sin(w) / (2 * (freq / (60 + 30 * k)));
        const a0 = 1 + alpha;
        return [alpha / a0, -alpha / a0, (-2 * Math.cos(w)) / a0, (1 - alpha) / a0];
      });
    }
    const x = source[i];
    let y = 0;
    for (let k = 0; k < 3; k++) {
      const [b0, b2, a1, a2] = coeffs[k],
        s = state[k];
      const v = b0 * x + b2 * s.x2 - a1 * s.y1 - a2 * s.y2;
      s.x2 = s.x1;
      s.x1 = x;
      s.y2 = s.y1;
      s.y1 = v;
      y += v * gains[k];
    }
    out[i] = y;
  }
  return out;
}

/** A small hall: a few feedback combs and an all-pass, for teak walls and a tiled roof. */
function hall(input: Float32Array, rate: number, wet: number, size = 1): Float32Array {
  const out = input.slice();
  for (const [ms, g] of [
    [29.7, 0.78],
    [37.1, 0.76],
    [41.1, 0.74],
    [43.7, 0.72],
  ] as const) {
    const d = Math.round((ms * size * rate) / 1000);
    const buf = new Float32Array(input.length);
    for (let i = 0; i < input.length; i++) buf[i] = input[i] + (i >= d ? buf[i - d] * g : 0);
    for (let i = 0; i < input.length; i++) out[i] += buf[i] * wet * 0.25;
  }
  return out;
}

/**
 * The monks' evening chant from inside the hall: four to six low voices on one
 * reciting tone, each slightly out of time and tune with the others, the phrase
 * falling a step at its end, breaths between. Loops seamlessly.
 */
export function monkChant(rate: number, rand: () => number, wrong = false): Float32Array {
  const total = 26;
  const out = new Float32Array(seconds(total + 2, rate));
  const beat = wrong ? 0.42 : 0.3;
  const voices = 5;
  for (let v = 0; v < voices; v++) {
    const base = (wrong ? 78 : 102) * (1 + (rand() - 0.5) * 0.05) * (v === 4 ? 0.5 : 1);
    const lag = rand() * 0.05;
    let at = 0.5 + lag;
    for (let rep = 0; rep < 3; rep++) {
      const syllables = HOMAGE;
      const length = syllables.reduce((s, y) => s + y[1], 0) * beat;
      const onsets: number[] = [];
      let k = 0;
      for (const syl of syllables) {
        onsets.push(k);
        k += syl[1] * beat;
      }
      const vowelAt = (t: number) => {
        let i = onsets.findIndex(
          (o, j) => t >= o && (j === onsets.length - 1 || t < onsets[j + 1]),
        );
        if (i < 0) i = 0;
        const [vowel, beats, , nasal] = syllables[i];
        const into = (t - onsets[i]) / (beats * beat);
        return VOWELS[nasal && into > 0.7 ? "m" : vowel];
      };
      // One reciting tone, a step down on the last long syllable of the phrase.
      const f0 = (t: number) =>
        base *
        (t > length - 2.6 * beat ? 2 ** (-2 / 12) : 1) *
        (1 + 0.004 * Math.sin(t * 2 * Math.PI * 4.7));
      const n = seconds(length, rate);
      let line: Float32Array = articulate(glottal(n, rate, f0, rand), rate, vowelAt);
      // Consonants: dips for stops, hiss for s, breath for h, a nasal murmur for n.
      const breath = noise(n, rand);
      biquad(breath, rate, "highpass", 2500, 0.8);
      syllables.forEach(([, , onset], i) => {
        const s0 = seconds(onsets[i], rate);
        const span = seconds(onset === "s" ? 0.07 : 0.045, rate);
        for (let j = 0; j < span && s0 + j < n; j++) {
          const e = Math.sin((Math.PI * j) / span);
          if (onset === "stop") line[s0 + j] *= 1 - 0.95 * e;
          else if (onset === "n") line[s0 + j] *= 1 - 0.6 * e;
          else if (onset === "r") line[s0 + j] *= 1 - 0.4 * Math.abs(Math.sin(j / 40)) * e;
          else if (onset === "s") line[s0 + j] = line[s0 + j] * (1 - e) + breath[s0 + j] * e * 0.25;
          else if (onset === "h") line[s0 + j] += breath[s0 + j] * e * 0.12;
        }
      });
      if (wrong) {
        // Smeared and dragged, as if heard through water or through the dead.
        line = softClip(line, 1.6);
        for (let i = n - 1; i > 0; i--) line[i] = line[i] * 0.6 + line[i - 1] * 0.4;
      }
      mix(
        out,
        line,
        rate,
        at,
        v === 4 ? 0.5 : 0.85,
        (t) => Math.min(1, t / 0.08) * Math.min(1, (length - t) / 0.4),
      );
      at += length + 0.9 + rand() * 0.15;
    }
  }
  const room = hall(out, rate, wrong ? 1.2 : 0.8, wrong ? 1.4 : 1);
  return normalise(wrapLoop(room, rate, 2), 0.9);
}

/** A whisper: breath through moving vowel formants, sibilants, gone in two seconds. */
export function ghostWhisper(rate: number, rand: () => number): Float32Array {
  const length = seconds(2.2, rate);
  const src = noise(length, rand);
  const order: Vowel[] = ["a", "u", "e", "o", "i", "a"];
  const speech = articulate(src, rate, (t) => VOWELS[order[Math.floor(t * 5) % order.length]]);
  const hiss = biquad(noise(length, rand), rate, "highpass", 4000, 0.7);
  const out = new Float32Array(length);
  for (let i = 0; i < length; i++) {
    const t = i / rate;
    const syl = Math.abs(Math.sin(t * Math.PI * 4.6)) ** 1.5;
    const env = Math.min(1, t / 0.15) * Math.min(1, (2.2 - t) / 0.4);
    out[i] = (speech[i] * syl + hiss[i] * 0.15 * (1 - syl)) * env;
  }
  return normalise(out, 0.9);
}

/** A skor drum struck far off in the forest: pitch-dropping membrane, slap, decay. */
export function templeDrum(rate: number, rand: () => number): Float32Array {
  const length = seconds(4.5, rate);
  const out = new Float32Array(length);
  for (const at of [0, 1.15, 2.3]) {
    const n = seconds(1.6, rate);
    const hit = new Float32Array(n);
    let phase = 0;
    for (let i = 0; i < n; i++) {
      const t = i / rate;
      phase += (2 * Math.PI * (58 + 40 * Math.exp(-t * 14))) / rate;
      hit[i] = Math.sin(phase) * Math.exp(-t * 3.2) + (rand() - 0.5) * Math.exp(-t * 60) * 0.6;
    }
    place(out, biquad(hit, rate, "lowpass", 900, 0.7), rate, at, at === 2.3 ? 1.2 : 0.8);
  }
  return normalise(hall(out, rate, 0.5, 2.2), 0.9);
}

/** A large temple gong, struck once, beating as its inharmonic partials decay. */
export function templeGong(rate: number, rand: () => number): Float32Array {
  const length = seconds(9, rate);
  const out = new Float32Array(length);
  const partials: [number, number, number][] = [
    [92, 6, 1],
    [93.6, 6, 0.8],
    [181, 4.5, 0.5],
    [268, 3.5, 0.4],
    [411, 2.6, 0.3],
    [553, 2, 0.2],
    [838, 1.2, 0.12],
  ];
  for (const [f, d, g] of partials) {
    const ph = rand() * 6.28;
    for (let i = 0; i < length; i++) {
      const t = i / rate;
      out[i] += Math.sin(2 * Math.PI * f * t + ph) * Math.exp(-t / d) * g * Math.min(1, t * 60);
    }
  }
  return normalise(out, 0.9);
}

/** Three slow knocks on teak from inside a wall. */
export function woodKnocks(rate: number, rand: () => number): Float32Array {
  const out = new Float32Array(seconds(2.4, rate));
  for (const at of [0, 0.55, 1.4]) {
    const n = seconds(0.4, rate);
    const hit = noise(n, rand);
    for (let i = 0; i < n; i++) hit[i] *= Math.exp(-i / (rate * 0.004));
    const body = new Float32Array(n);
    for (const [f, d] of [
      [180, 0.07],
      [310, 0.05],
      [520, 0.03],
    ] as const)
      for (let i = 0; i < n; i++)
        body[i] += Math.sin((2 * Math.PI * f * i) / rate) * Math.exp(-i / (rate * d));
    for (let i = 0; i < n; i++) body[i] += hit[i] * 0.3;
    place(out, body, rate, at, 1);
  }
  return normalise(out, 0.9);
}

/** Bare footsteps right behind you on dead leaves, that stop when you stop. */
export function stepsBehind(rate: number, rand: () => number): Float32Array {
  const out = new Float32Array(seconds(3, rate));
  for (let k = 0; k < 5; k++) {
    const n = seconds(0.3, rate);
    const crunch = biquad(noise(n, rand), rate, "bandpass", 1800 + rand() * 1500, 0.9);
    for (let i = 0; i < n; i++) {
      const t = i / rate;
      crunch[i] *= Math.exp(-t * 18) * (0.6 + 0.4 * Math.sin(t * 500 * rand()));
    }
    const thud = new Float32Array(n);
    for (let i = 0; i < n; i++)
      thud[i] = Math.sin((2 * Math.PI * 70 * i) / rate) * Math.exp(-i / (rate * 0.05));
    place(out, crunch, rate, 0.2 + k * 0.52, 0.8);
    place(out, thud, rate, 0.2 + k * 0.52, 0.5);
  }
  return normalise(out, 0.9);
}

/** A heartbeat for when a Pret is close: lub-dub, low and felt more than heard. */
export function heartbeat(rate: number): Float32Array {
  const period = 0.82;
  const out = new Float32Array(seconds(period * 8, rate));
  for (let b = 0; b < 8; b++)
    for (const [off, g] of [
      [0, 1],
      [0.16, 0.6],
    ] as const) {
      const n = seconds(0.18, rate);
      const beat = new Float32Array(n);
      for (let i = 0; i < n; i++) {
        const t = i / rate;
        beat[i] =
          Math.sin(2 * Math.PI * (48 - 10 * t) * t) * Math.exp(-t * 26) * Math.min(1, t * 400);
      }
      place(out, beat, rate, b * period + off, g);
    }
  return normalise(out, 0.9);
}

/**
 * The apparition's scream: a woman's voice tearing upward through an "a" into a
 * shriek, doubled and distorted, over a sub-bass hit.
 */
export function ghostScream(rate: number, rand: () => number): Float32Array {
  const length = seconds(2.4, rate);
  const f0 = (t: number) => 320 + 900 * Math.min(1, t / 0.35) ** 0.6 + 60 * Math.sin(t * 70);
  const voice = articulate(glottal(length, rate, f0, rand), rate, (t) =>
    t < 0.3 ? [850, 1220, 2810] : [1000, 1500, 3300],
  );
  const rasp = biquad(noise(length, rand), rate, "bandpass", 2600, 1.2);
  const out = new Float32Array(length);
  for (let i = 0; i < length; i++) {
    const t = i / rate;
    const env = Math.min(1, t / 0.02) * Math.exp(-Math.max(0, t - 0.6) * 2.4);
    out[i] = (voice[i] + rasp[i] * 0.4) * env;
    out[i] += Math.sin(2 * Math.PI * (55 - 25 * t) * t) * Math.exp(-t * 3) * 0.8;
  }
  return normalise(softClip(out, 2.4), 0.9);
}

/** A child's single sob somewhere in the dark, cut off. */
export function distantSob(rate: number, rand: () => number): Float32Array {
  const length = seconds(1.8, rate);
  const f0 = (t: number) => 380 - 90 * t + 30 * Math.sin(t * 40);
  const voice = articulate(glottal(length, rate, f0, rand), rate, () =>
    VOWELS.u.map((f) => f * 1.35),
  );
  const out = new Float32Array(length);
  for (let i = 0; i < length; i++) {
    const t = i / rate;
    const catches = Math.abs(Math.sin(t * Math.PI * 3.3)) ** 2;
    out[i] = voice[i] * catches * Math.min(1, t / 0.05) * Math.max(0, 1 - t / 1.8);
  }
  return normalise(hall(out, rate, 0.7, 1.6), 0.9);
}

/** A stone image dragged a hand's breadth over brick: a low grinding scrape that judders. */
export function stoneGrind(rate: number, rand: () => number): Float32Array {
  const length = seconds(1.6, rate);
  const grit = biquad(noise(length, rand), rate, "bandpass", 420, 0.7);
  const rumble = biquad(noise(length, rand), rate, "lowpass", 90, 0.7);
  const out = new Float32Array(length);
  for (let i = 0; i < length; i++) {
    const t = i / rate;
    // Stick-slip: the weight catches and lurches a dozen times as it moves.
    const judder = 0.55 + 0.45 * Math.abs(Math.sin(t * Math.PI * 7.5 + Math.sin(t * 11) * 0.8));
    const env = Math.min(1, t / 0.08) * Math.max(0, 1 - t / 1.6) ** 0.6;
    out[i] = (grit[i] * 0.8 + rumble[i] * 1.6) * judder * env;
  }
  return normalise(hall(out, rate, 0.35, 1.2), 0.9);
}

/** Female formants: the male table scaled up a sixth. */
const female = (v: Vowel) => VOWELS[v].map((f) => f * 1.22);

/**
 * The kuntilanak's laugh: a thin, high woman's "hi-hi-hi" that runs down the
 * scale and ends in a long wavering note, breathy, far too happy, in a hall.
 */
export function kuntilanakLaugh(rate: number, rand: () => number): Float32Array {
  const out = new Float32Array(seconds(3.2, rate));
  const notes = 7;
  for (let k = 0; k <= notes; k++) {
    const last = k === notes;
    const len = last ? 0.62 : 0.12;
    const at = 0.05 + k * 0.19;
    const f0 = 860 - k * 38;
    const n = seconds(len, rate);
    const src = glottal(
      n,
      rate,
      (t) => f0 * (1 + (last ? 0.03 * Math.sin(t * 38) : 0)) * (1 - t * 0.25),
      rand,
    );
    const air = biquad(noise(n, rand), rate, "highpass", 2400, 0.7);
    for (let i = 0; i < n; i++) src[i] = src[i] * 0.8 + air[i] * 0.35;
    const voice = articulate(src, rate, (t) => (t < 0.02 ? female("e") : female("i")));
    for (let i = 0; i < n; i++) {
      const t = i / rate;
      // An "h" of breath, the voiced note, then cut off sharp.
      voice[i] *= Math.min(1, t / 0.012) * Math.max(0, 1 - t / len) ** (last ? 0.6 : 0.25);
    }
    place(out, voice, rate, at, 1);
  }
  return normalise(hall(out, rate, 0.75, 1.5), 0.9);
}

/** A neck snapping over too far: two dry cracks and a gristly pop, close. */
export function boneCrack(rate: number, rand: () => number): Float32Array {
  const out = new Float32Array(seconds(0.7, rate));
  for (const [at, gain] of [
    [0.02, 1],
    [0.055, 0.7],
    [0.11, 0.45],
  ] as const) {
    const n = seconds(0.06, rate);
    const snap = biquad(noise(n, rand), rate, "highpass", 1600 + rand() * 900, 0.8);
    for (let i = 0; i < n; i++) {
      const t = i / rate;
      snap[i] =
        snap[i] * Math.exp(-t / 0.004) +
        Math.sin(2 * Math.PI * 1150 * t) * Math.exp(-t / 0.006) * 0.4;
    }
    place(out, snap, rate, at, gain);
  }
  const thump = new Float32Array(seconds(0.2, rate));
  for (let i = 0; i < thump.length; i++) {
    const t = i / rate;
    thump[i] = Math.sin(2 * Math.PI * 95 * t) * Math.exp(-t / 0.04);
  }
  place(out, thump, rate, 0.02, 0.6);
  return normalise(hall(out, rate, 0.25, 0.8), 0.9);
}

/** Where she was a moment ago: a breath sucked in hard and cut off dead. */
export function vanishBreath(rate: number, rand: () => number): Float32Array {
  const length = seconds(0.75, rate);
  const gasp = biquad(noise(length, rand), rate, "bandpass", 1100, 0.9);
  const low = biquad(noise(length, rand), rate, "lowpass", 260, 0.7);
  const out = new Float32Array(length);
  const end = 0.62;
  for (let i = 0; i < length; i++) {
    const t = i / rate;
    if (t > end) break;
    // Swelling like a reversed sigh, then nothing: no tail at all.
    const swell = (t / end) ** 3.2 * Math.min(1, (end - t) / 0.004);
    out[i] = (gasp[i] + low[i] * 1.4) * swell;
  }
  return normalise(out, 0.9);
}

/** A bound corpse landing from a hop: a heavy thud through the ground, cloth slapping. */
export function pocongThud(rate: number, rand: () => number): Float32Array {
  const out = new Float32Array(seconds(0.6, rate));
  const n = seconds(0.4, rate);
  const body = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const t = i / rate;
    body[i] = Math.sin(2 * Math.PI * (72 - 30 * t) * t) * Math.exp(-t / 0.09);
  }
  place(out, body, rate, 0, 1);
  const cloth = biquad(noise(seconds(0.12, rate), rand), rate, "bandpass", 520, 0.8);
  for (let i = 0; i < cloth.length; i++) cloth[i] *= Math.exp(-i / rate / 0.03);
  place(out, cloth, rate, 0.004, 0.55);
  const grit = biquad(noise(seconds(0.08, rate), rand), rate, "highpass", 2600, 0.7);
  for (let i = 0; i < grit.length; i++) grit[i] *= Math.exp(-i / rate / 0.015);
  place(out, grit, rate, 0.006, 0.25);
  return normalise(out, 0.9);
}

/** A moan from inside the shroud: low, shut-mouthed, catching, the cloth muffling it. */
export function pocongGroan(rate: number, rand: () => number): Float32Array {
  const length = seconds(2.6, rate);
  const f0 = (t: number) => 88 - 16 * t + 4 * Math.sin(t * 9);
  const voice = articulate(glottal(length, rate, f0, rand), rate, (t) =>
    t < 1.2 ? VOWELS.u : VOWELS.o,
  );
  const muffled = biquad(voice, rate, "lowpass", 650, 0.7);
  for (let i = 0; i < length; i++) {
    const t = i / rate;
    const catchy = 0.7 + 0.3 * Math.abs(Math.sin(t * Math.PI * 2.4));
    muffled[i] *= Math.min(1, t / 0.25) * Math.max(0, 1 - t / 2.6) ** 0.7 * catchy;
  }
  return normalise(softClip(hall(muffled, rate, 0.3, 1), 1.6), 0.9);
}
