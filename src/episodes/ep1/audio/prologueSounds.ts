import {
  biquad,
  brown,
  bubble,
  decay,
  formant,
  mix,
  modal,
  noise,
  normalise,
  softClip,
  stickSlip,
  sweep,
  wrapLoop,
} from "../../../audio/synth";

/**
 * Synthesised stand-ins for the prologue's sounds (Audio Design Document,
 * section 9) until the recordings exist. Mono, peak 0.9, pure functions.
 * Loops (rain, the clock, the bell, line static) wrap without a click.
 */

const seconds = (s: number, sampleRate: number) => Math.round(s * sampleRate);

function sine(length: number, sampleRate: number, frequency: (t: number) => number): Float32Array {
  const out = new Float32Array(length);
  let phase = 0;
  for (let i = 0; i < length; i++) {
    phase += (2 * Math.PI * frequency(i / sampleRate)) / sampleRate;
    out[i] = Math.sin(phase);
  }
  return out;
}

/** Fades both ends of a loop over `fade` seconds, so it repeats without a click. */
function seamless(samples: Float32Array, sampleRate: number, fade = 0.05): Float32Array {
  const n = seconds(fade, sampleRate);
  for (let i = 0; i < n; i++) {
    const k = i / n;
    samples[i] *= k;
    samples[samples.length - 1 - i] *= k;
  }
  return samples;
}

/** Random impulses at `perSecond`, each of random sign and a size skewed small. */
function scatter(length: number, rand: () => number, count: number, skew = 2): Float32Array {
  const out = new Float32Array(length);
  for (let k = 0; k < count; k++)
    out[Math.floor(rand() * length)] += (rand() < 0.5 ? -1 : 1) * rand() ** skew;
  return out;
}

/**
 * Heavy monsoon rain heard from inside the studio: the wash through the
 * walls, drops ringing on the tin awning, rapping the wooden shutters and
 * ticking on the glass, and the downpipe gurgling as it overflows.
 */
export function rainLoop(sampleRate: number, rand: () => number): Float32Array {
  const fade = 1;
  const length = seconds(12 + fade, sampleRate);
  const out = new Float32Array(length);
  // The wash, through the walls: low and full, its top end taken by the glass.
  const hiss = biquad(
    biquad(noise(length, rand), sampleRate, "bandpass", 2400, 0.5),
    sampleRate,
    "lowpass",
    3800,
    0.7,
  );
  const wash = biquad(brown(length, rand, 0.99), sampleRate, "lowpass", 420, 0.7);
  for (let i = 0; i < length; i++) {
    const swell = 0.88 + 0.12 * Math.sin((i / sampleRate) * 0.45);
    out[i] = (hiss[i] * 0.4 + wash[i] * 2.2) * swell;
  }
  // The tin awning over the window: one sheet, so every drop rings the same modes.
  const tin = modal(scatter(length, rand, 2600), sampleRate, [
    [2210, 0.035, 1],
    [3130, 0.028, 0.8],
    [4470, 0.02, 0.6],
    [5890, 0.014, 0.4],
    [1480, 0.045, 0.5],
  ]);
  // The shutters: dull wooden raps.
  const wood = modal(scatter(length, rand, 700, 1.5), sampleRate, [
    [620, 0.012, 1],
    [1180, 0.009, 0.7],
    [1950, 0.006, 0.5],
  ]);
  // The glass: tiny, bright ticks.
  const glass = modal(scatter(length, rand, 900, 3), sampleRate, [
    [3900, 0.004, 1],
    [6100, 0.003, 0.6],
  ]);
  for (let i = 0; i < length; i++) out[i] += tin[i] * 0.16 + wood[i] * 0.5 + glass[i] * 0.3;
  // The downpipe overflowing: a stream of bubbles, its flow surging.
  for (let k = 0; k < 520; k++) {
    const at = rand() * (length / sampleRate - 0.05);
    const surge = 0.5 + 0.5 * Math.sin(at * 1.7 + 0.4) * Math.sin(at * 0.53);
    mix(
      out,
      bubble(sampleRate, 320 + rand() * 700, 0.006 + rand() * 0.01),
      sampleRate,
      at,
      0.05 * surge * (0.3 + rand()),
      () => 1,
    );
  }
  return normalise(wrapLoop(out, sampleRate, fade), 0.9);
}

/**
 * The mantel clock: each beat is the escapement's two clicks (the pallet
 * unlocking, the tooth dropping), ringing the brass works and the wooden
 * case; the tock's swing sounds a little different. One second per loop.
 */
export function clockLoop(sampleRate: number, rand: () => number): Float32Array {
  const out = new Float32Array(sampleRate);
  const works: [number, number, number][] = [
    [2870, 0.03, 1],
    [4410, 0.022, 0.7],
    [6230, 0.014, 0.45],
    [1260, 0.035, 0.5],
    [640, 0.05, 0.35],
  ];
  for (const [at, scale, gain] of [
    [0.012, 1, 1],
    [0.512, 0.94, 0.72],
  ]) {
    const clicks = new Float32Array(seconds(0.12, sampleRate));
    clicks[0] = 0.7;
    clicks[seconds(0.0045 + rand() * 0.001, sampleRate)] = 1;
    clicks[seconds(0.009, sampleRate)] = 0.25;
    const ring = modal(
      clicks,
      sampleRate,
      works.map(([f, d, g]) => [f * scale, d, g]),
    );
    mix(out, ring, sampleRate, at, gain, () => 1);
  }
  return normalise(out, 0.33);
}

/**
 * The clock stopping: the pendulum knocks the case, the mainspring gives a
 * dull twang, and the works go dead.
 */
export function clockStop(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(0.6, sampleRate);
  const hit = new Float32Array(length);
  for (let i = 0; i < seconds(0.006, sampleRate); i++)
    hit[i] = (rand() * 2 - 1) * Math.exp(-i / seconds(0.0015, sampleRate));
  const out = modal(hit, sampleRate, [
    [138, 0.12, 1],
    [262, 0.08, 0.8],
    [517, 0.05, 0.6],
    [930, 0.03, 0.45],
    [1640, 0.016, 0.3],
  ]);
  const spring = modal(hit, sampleRate, [
    [372, 0.35, 0.18],
    [1031, 0.22, 0.1],
    [2215, 0.12, 0.06],
  ]);
  const body = sine(length, sampleRate, (t) => 120 - t * 50);
  for (let i = 0; i < length; i++) {
    const t = i / sampleRate;
    out[i] = out[i] * 6 + spring[i] * 4 + body[i] * 0.45 * Math.exp(-t / 0.07);
  }
  return normalise(out, 0.9);
}

/**
 * A 1930s magneto telephone bell: a clapper hammering between two small
 * steel gongs a little out of tune with each other, 20 strikes a second for
 * 1.6 s, the armature buzzing, then the gongs ringing away and 2.4 s of quiet.
 */
export function phoneRing(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(4, sampleRate);
  const strikes = seconds(1.6, sampleRate);
  const left = new Float32Array(length);
  const right = new Float32Array(length);
  for (let k = 0; k < 32; k++) {
    const i = Math.round((k * strikes) / 32) + Math.floor(rand() * seconds(0.002, sampleRate));
    (k % 2 ? right : left)[i] = 0.85 + rand() * 0.15;
  }
  const gong = (f: number): [number, number, number][] => [
    [f, 0.55, 1],
    [f * 2.32, 0.32, 0.65],
    [f * 4.25, 0.18, 0.45],
    [f * 6.63, 0.1, 0.3],
    [f * 9.38, 0.06, 0.18],
  ];
  const a = modal(left, sampleRate, gong(1047));
  const b = modal(right, sampleRate, gong(1118));
  const out = new Float32Array(length);
  for (let i = 0; i < length; i++) out[i] = a[i] + b[i];
  const buzz = biquad(noise(strikes, rand), sampleRate, "bandpass", 3100, 2.5);
  for (let i = 0; i < strikes; i++) {
    const t = i / sampleRate;
    out[i] += buzz[i] * 0.08 * (0.6 + 0.4 * Math.sin(t * 2 * Math.PI * 20));
  }
  return seamless(normalise(out, 0.9), sampleRate, 0.01);
}

/**
 * A bad provincial line: band-limited hiss, mains hum leaking in, the line
 * fading and swelling, crackle in bursts and a faint whistle of crosstalk.
 */
export function lineStatic(sampleRate: number, rand: () => number): Float32Array {
  const fade = 0.5;
  const length = seconds(3 + fade, sampleRate);
  const out = biquad(
    biquad(noise(length, rand), sampleRate, "highpass", 350, 0.7),
    sampleRate,
    "lowpass",
    3200,
    0.7,
  );
  const drift = biquad(noise(length, rand), sampleRate, "lowpass", 3, 0.7);
  let driftPeak = 1e-6;
  for (const d of drift) driftPeak = Math.max(driftPeak, Math.abs(d));
  for (let i = 0; i < length; i++) {
    const t = i / sampleRate;
    const hum =
      Math.sin(2 * Math.PI * 50 * t) * 0.05 +
      Math.sin(2 * Math.PI * 150 * t) * 0.04 +
      Math.sin(2 * Math.PI * 250 * t) * 0.02;
    const whistle = Math.sin(2 * Math.PI * (1830 + 40 * Math.sin(t * 1.3)) * t) * 0.012;
    out[i] = out[i] * 0.3 * (0.75 + 0.25 * (drift[i] / driftPeak)) + hum + whistle;
  }
  // Crackle comes in bursts, as a wet wire shorts and clears.
  for (let burst = 0; burst < 7; burst++) {
    const start = rand() * (length / sampleRate - 0.3);
    for (let k = 0; k < 6 + rand() * 18; k++) {
      const crack = noise(seconds(0.004, sampleRate), rand);
      mix(out, crack, sampleRate, start + rand() * 0.25, 0.4 + rand() * 0.9, decay(0.0015));
    }
  }
  return normalise(wrapLoop(out, sampleRate, fade), 0.8);
}

/** Squeezes a sound into what a 1930s line carries: 350 Hz to 3 kHz, and a carbon mic's grit. */
function telephone(samples: Float32Array, sampleRate: number, drive = 2): Float32Array {
  biquad(samples, sampleRate, "highpass", 350, 0.8);
  biquad(samples, sampleRate, "highpass", 350, 0.8);
  biquad(samples, sampleRate, "lowpass", 3000, 0.8);
  biquad(samples, sampleRate, "lowpass", 3000, 0.8);
  return softClip(normalise(samples, 1), drive);
}

/**
 * The end of the call, all of it through the line: a woman's scream, cracking
 * and rising, glass breaking, something heavy falling against the walls, the
 * receiver knocked and dragged, then the line cuts dead.
 */
export function callScream(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(3.2, sampleRate);
  const raw = new Float32Array(length);
  // The voice: a glottal buzz with jitter, rising, its pitch breaking near the top.
  const screamFor = 1.45;
  const n = seconds(screamFor, sampleRate);
  const buzz = new Float32Array(n);
  let phase = 0,
    wobble = 0,
    cycle = 0;
  for (let i = 0; i < n; i++) {
    const t = i / sampleRate;
    wobble += (rand() - 0.5) * 0.02 - wobble * 0.002;
    const f0 =
      (520 + 380 * Math.min(1, t / 0.5) + (t > 0.9 ? 120 * Math.sin((t - 0.9) * 9) : 0)) *
      (1 + 0.025 * Math.sin(t * 2 * Math.PI * 7.5) + wobble);
    phase += f0 / sampleRate;
    if (phase >= 1) {
      phase -= 1;
      cycle++;
    }
    // A sawtooth, every other cycle weaker: the rough period-doubling of a throat at its limit.
    buzz[i] = (phase * 2 - 1) * (cycle % 2 ? 0.7 : 1);
  }
  const voice = formant(buzz, sampleRate, [
    [950, 130, 1],
    [1450, 160, 0.75],
    [2900, 260, 0.45],
    [3800, 400, 0.2],
  ]);
  const breath = formant(noise(n, rand), sampleRate, [
    [950, 300, 1],
    [2900, 600, 0.5],
  ]);
  mix(
    raw,
    voice,
    sampleRate,
    0.03,
    1,
    (t) => Math.min(1, t / 0.08) * (t > 1.15 ? Math.max(0, 1 - (t - 1.15) / 0.3) : 1),
  );
  mix(raw, breath, sampleRate, 0.03, 0.25, (t) => (t < screamFor ? Math.min(1, t / 0.05) : 0));
  // Glass: the pane cracks, then shards ring as they fall and scatter.
  mix(
    raw,
    biquad(noise(seconds(0.35, sampleRate), rand), sampleRate, "highpass", 2200, 0.7),
    sampleRate,
    1.22,
    1.1,
    decay(0.06),
  );
  const shards = new Float32Array(seconds(1.2, sampleRate));
  for (let k = 0; k < 70; k++) {
    const at = Math.floor(rand() ** 1.6 * shards.length * 0.85);
    shards[at] += (rand() < 0.5 ? -1 : 1) * (0.3 + rand() * 0.7);
  }
  const ringing = modal(shards, sampleRate, [
    [3150, 0.04, 1],
    [4630, 0.03, 0.8],
    [5870, 0.02, 0.6],
    [2410, 0.05, 0.5],
    [7300, 0.012, 0.4],
  ]);
  mix(raw, ringing, sampleRate, 1.25, 0.5, () => 1);
  // Something heavy falls against the wall and floor.
  for (const at of [1.85, 2.18, 2.42]) {
    const thump = new Float32Array(seconds(0.5, sampleRate));
    for (let i = 0; i < seconds(0.008, sampleRate); i++) thump[i] = rand() * 2 - 1;
    const room = modal(thump, sampleRate, [
      [78, 0.12, 1],
      [143, 0.08, 0.8],
      [266, 0.05, 0.5],
      [590, 0.025, 0.3],
    ]);
    mix(raw, room, sampleRate, at, 5 + rand() * 2, () => 1);
  }
  // The receiver knocked off its hook and dragged across the desk.
  const drag = modal(
    stickSlip(
      seconds(0.35, sampleRate),
      sampleRate,
      rand,
      (t) => 90 + 200 * t,
      (t) => Math.sin((Math.PI * t) / 0.35),
      0.6,
    ),
    sampleRate,
    [
      [820, 0.012, 1],
      [1450, 0.008, 0.6],
    ],
  );
  mix(raw, drag, sampleRate, 2.55, 1.2, () => 1);
  const cut = 2.95;
  const line = telephone(raw, sampleRate, 4);
  const hiss = biquad(noise(length, rand), sampleRate, "bandpass", 1600, 0.8);
  const out = new Float32Array(length);
  for (let i = 0; i < length; i++) {
    const t = i / sampleRate;
    out[i] = t < cut ? line[i] * 0.8 + hiss[i] * 0.05 : 0;
  }
  // The cut: one hard click, then nothing at all.
  mix(out, noise(seconds(0.003, sampleRate), rand), sampleRate, cut, 0.7, decay(0.0008));
  return normalise(out, 0.9);
}

/**
 * Thunder after the lightning: the near crack tearing across the sky, then
 * the long roll, gusts of rumble arriving later and darker from further along
 * the bolt, until only the lowest notes are left.
 */
export function thunder(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(5, sampleRate);
  const out = new Float32Array(length);
  // The crack: a cluster of sharp, ripping bursts.
  for (let k = 0; k < 9; k++) {
    const at = 0.02 + rand() ** 1.5 * 0.22;
    const rip = biquad(noise(seconds(0.12, sampleRate), rand), sampleRate, "lowpass", 2600, 0.7);
    mix(out, rip, sampleRate, at, 0.35 + rand() * 0.45, decay(0.02 + rand() * 0.03));
  }
  // The roll: many rumbles, sparser and darker the later they arrive.
  const rumble = new Float32Array(length);
  const deep = brown(length, rand, 0.997);
  for (let k = 0; k < 34; k++) {
    const at = 0.1 + rand() ** 1.4 * 4.2;
    const d = 0.15 + rand() * 0.5;
    const gain = (0.5 + rand() * 0.5) * Math.exp(-at / 2.2);
    const start = seconds(at, sampleRate);
    for (let i = 0; i < seconds(d * 4, sampleRate) && start + i < length; i++) {
      const t = i / sampleRate;
      rumble[start + i] += deep[start + i] * gain * (1 - Math.exp(-t / 0.03)) * Math.exp(-t / d);
    }
  }
  const darkening = sweep(
    rumble,
    sampleRate,
    "lowpass",
    (t) => 900 * Math.exp(-t / 1.1) + 110,
    0.8,
  );
  for (let i = 0; i < length; i++) {
    const t = i / sampleRate;
    out[i] += darkening[i] * 9 * Math.min(1, (5 - t) / 0.6);
  }
  return normalise(out, 0.9);
}

/**
 * P07's fade: riding a 1930s train. The bogies over each rail joint
 * ("da-dum ... da-dum"), the steel ringing, the carriage's rumble and creak,
 * and the engine's whistle far ahead.
 */
export function trainPassing(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(6, sampleRate);
  const out = biquad(brown(length, rand, 0.993), sampleRate, "lowpass", 240, 0.7);
  for (let i = 0; i < length; i++) {
    const t = i / sampleRate;
    out[i] *= 3 * (1 + 0.15 * Math.sin(t * 2 * Math.PI * 1.7));
  }
  const joints = new Float32Array(length);
  for (let at = 0.15; at < 5.7; at += 0.86)
    for (const lag of [0, 0.105, 0.47, 0.575])
      joints[seconds(at + lag + rand() * 0.004, sampleRate)] = 0.8 + rand() * 0.2;
  const clack = modal(joints, sampleRate, [
    [430, 0.04, 1],
    [1180, 0.025, 0.7],
    [2350, 0.014, 0.4],
    [180, 0.06, 0.8],
  ]);
  for (let i = 0; i < length; i++) out[i] += clack[i] * 1.6;
  const creak = modal(
    stickSlip(
      length,
      sampleRate,
      rand,
      (t) => 70 + 30 * Math.sin(t * 2.3),
      () => 0.25,
      0.4,
    ),
    sampleRate,
    [
      [740, 0.02, 1],
      [1310, 0.014, 0.6],
    ],
  );
  for (let i = 0; i < length; i++) out[i] += creak[i] * 0.4;
  // The whistle: three steam pipes sounding a chord, breathy, far off.
  const whistle = new Float32Array(seconds(1.4, sampleRate));
  for (const f of [523, 659, 784]) {
    const pipe = sine(
      whistle.length,
      sampleRate,
      (t) => f * (0.985 + 0.015 * Math.min(1, t / 0.2)),
    );
    for (let i = 0; i < whistle.length; i++) whistle[i] += pipe[i] * 0.3;
  }
  const steam = biquad(noise(whistle.length, rand), sampleRate, "bandpass", 1400, 1.2);
  for (let i = 0; i < whistle.length; i++) whistle[i] += steam[i] * 0.25;
  biquad(whistle, sampleRate, "lowpass", 1800, 0.7);
  mix(
    out,
    whistle,
    sampleRate,
    1.1,
    0.35,
    (t) => Math.min(1, t / 0.12) * Math.min(1, (1.4 - t) / 0.4),
  );
  for (let i = 0; i < length; i++) {
    const t = i / sampleRate;
    out[i] *= Math.min(1, t / 1.2) * Math.min(1, (6 - t) / 1.5);
  }
  return normalise(out, 0.9);
}

/**
 * A pen nib scratching ink onto paper (P02): the nib catching on the fibres in
 * tiny bright clicks, the paper's hiss, rising and falling with each stroke.
 */
export function penScratch(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(3.6, sampleRate);
  // Four strokes, with the same approach, nib lifts and withdrawal as P02.
  const stroke = (t: number) => {
    const progress = (t - 0.432) / 2.736;
    if (progress <= 0 || progress >= 1) return 0;
    const cycle = progress * 4;
    const phase = cycle % 1;
    const writingFraction = cycle >= 3 ? 0.95 : 0.82;
    if (phase >= writingFraction) return 0;
    return Math.sin((phase / writingFraction) * Math.PI) ** 0.7;
  };
  const nib = modal(
    stickSlip(length, sampleRate, rand, (t) => 380 + 520 * stroke(t), stroke, 0.9),
    sampleRate,
    [
      [5400, 0.002, 1],
      [7600, 0.0015, 0.7],
      [3300, 0.003, 0.4],
    ],
  );
  const paper = biquad(noise(length, rand), sampleRate, "bandpass", 4600, 1.1);
  const out = new Float32Array(length);
  for (let i = 0; i < length; i++) out[i] = nib[i] * 1.2 + paper[i] * 0.4 * stroke(i / sampleRate);
  return normalise(out, 0.9);
}

/** Something light picked up: cloth brushing, and paper crinkling in the hand (P03, P04). */
export function pickUp(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(0.35, sampleRate);
  const swish = biquad(noise(length, rand), sampleRate, "bandpass", 1300, 0.7);
  const crinkle = new Float32Array(length);
  for (let k = 0; k < 90; k++)
    crinkle[Math.floor((0.03 + rand() ** 0.8 * 0.28) * sampleRate)] = rand() * 2 - 1;
  const paper = biquad(
    modal(crinkle, sampleRate, [
      [2900, 0.002, 1],
      [4700, 0.0015, 0.8],
      [6800, 0.001, 0.5],
    ]),
    sampleRate,
    "highpass",
    1500,
    0.7,
  );
  const out = new Float32Array(length);
  for (let i = 0; i < length; i++) {
    const t = i / sampleRate;
    out[i] = swish[i] * 0.5 * Math.sin((Math.PI * t) / 0.35) ** 2 + paper[i] * 1.4;
  }
  return normalise(out, 0.6);
}

/**
 * A wooden drawer dragged open: runners juddering against the carcass in
 * stick-slip, the box resonating, then the knock as it stops.
 */
export function drawerOpen(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(0.55, sampleRate);
  const box: [number, number, number][] = [
    [212 + rand() * 30, 0.03, 1],
    [468, 0.022, 0.8],
    [905, 0.015, 0.6],
    [1690, 0.009, 0.4],
    [2900, 0.005, 0.25],
  ];
  const slide = stickSlip(
    length,
    sampleRate,
    rand,
    (t) => 95 + 160 * Math.sin((Math.PI * Math.min(t, 0.46)) / 0.46),
    (t) => (t < 0.47 ? Math.min(1, t / 0.04) : 0),
    0.55,
  );
  const out = modal(slide, sampleRate, box);
  const rub = biquad(noise(length, rand), sampleRate, "bandpass", 1100, 0.9);
  for (let i = 0; i < length; i++) out[i] += rub[i] * (i / sampleRate < 0.47 ? 0.05 : 0);
  const stop = new Float32Array(length);
  for (let i = 0; i < seconds(0.004, sampleRate); i++) stop[i] = rand() * 2 - 1;
  mix(out, modal(stop, sampleRate, box), sampleRate, 0.475, 0.6, () => 1);
  return normalise(out, 0.8);
}

/** A candle snuffed by a draught: the puff, the flame's flutter, then the wick's thin hiss. */
export function candleOut(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(0.7, sampleRate);
  const puff = biquad(noise(length, rand), sampleRate, "lowpass", 520, 0.7);
  const flutter = biquad(noise(length, rand), sampleRate, "bandpass", 180, 2);
  const wick = biquad(noise(length, rand), sampleRate, "bandpass", 5200, 2);
  const out = new Float32Array(length);
  for (let i = 0; i < length; i++) {
    const t = i / sampleRate;
    out[i] =
      puff[i] * Math.min(1, t / 0.04) * Math.exp(-t / 0.12) +
      flutter[i] * 1.5 * Math.exp(-t / 0.08) * (0.6 + 0.4 * Math.sin(t * 2 * Math.PI * 14)) +
      wick[i] * 0.05 * Math.min(1, t / 0.15) * Math.max(0, 1 - t / 0.7);
  }
  return normalise(out, 0.6);
}
