import {
  biquad,
  brown,
  bubble,
  formant,
  mix,
  modal,
  noise,
  normalise,
  stickSlip,
  sweep,
  wrapLoop,
} from "../../../audio/synth";

/**
 * Synthesised stand-ins for the house and the ground under it (Audio Design
 * Document, section 3: "Upper house" and "Under the house") until the
 * recordings exist. Mono, peak 0.9 or less, pure functions. Beds wrap with a
 * crossfade, so they loop with no click and no dip.
 */

const seconds = (s: number, sampleRate: number) => Math.round(s * sampleRate);

/** Random impulses of random sign, sizes skewed small. */
function scatter(length: number, rand: () => number, count: number, skew = 2): Float32Array {
  const out = new Float32Array(length);
  for (let k = 0; k < count; k++)
    out[Math.floor(rand() * length)] += (rand() < 0.5 ? -1 : 1) * rand() ** skew;
  return out;
}

/**
 * Rain on the clay roof tiles, heard from the upper rooms: the drumming of
 * thousands of drops on the tiles just overhead, the deep wash of the whole
 * roof, and the run-off pouring from the eaves into the puddles below. Make
 * two with different seeds for a wide stereo bed.
 */
export function roofRain(sampleRate: number, rand: () => number): Float32Array {
  const fade = 1;
  const length = seconds(12 + fade, sampleRate);
  const out = new Float32Array(length);
  const wash = biquad(brown(length, rand, 0.992), sampleRate, "lowpass", 520, 0.7);
  const hiss = biquad(noise(length, rand), sampleRate, "bandpass", 1500, 0.6);
  for (let i = 0; i < length; i++) {
    const t = i / sampleRate;
    const swell = 0.82 + 0.18 * Math.sin(t * 0.37 + 0.6) * Math.sin(t * 0.11 + 2);
    out[i] = (wash[i] * 2.6 + hiss[i] * 0.16) * swell;
  }
  // Tiles: fired clay, small and stiff, so each drop is a short, dull "tock".
  const tiles = modal(scatter(length, rand, 9000, 2.5), sampleRate, [
    [1180, 0.006, 1],
    [1870, 0.005, 0.8],
    [2740, 0.0035, 0.55],
    [760, 0.008, 0.5],
  ]);
  // The battens and rafters under them, thudding with the heavier drops.
  const timber = modal(scatter(length, rand, 1600, 3), sampleRate, [
    [190, 0.02, 1],
    [340, 0.016, 0.7],
  ]);
  for (let i = 0; i < length; i++) out[i] += tiles[i] * 0.22 + timber[i] * 0.3;
  // Run-off from the eaves: steady streams of drops into the puddles outside.
  for (let k = 0; k < 700; k++)
    mix(
      out,
      bubble(sampleRate, 500 + rand() * 1400, 0.006 + rand() * 0.01),
      sampleRate,
      rand() * (length / sampleRate - 0.05),
      0.025 + rand() ** 2 * 0.06,
      () => 1,
    );
  biquad(out, sampleRate, "lowpass", 5000, 0.7);
  return normalise(wrapLoop(out, sampleRate, fade), 0.8);
}

/**
 * Wind through the shutters: slow gusts that never quite stop, the air
 * moaning faintly through the gaps, and a loose shutter knocking now and then.
 */
export function shutterWind(sampleRate: number, rand: () => number): Float32Array {
  const fade = 1.5;
  const length = seconds(16 + fade, sampleRate);
  const p = [rand() * 6, rand() * 6, rand() * 6];
  const gust = (t: number) =>
    Math.max(
      0,
      0.45 +
        0.3 * Math.sin(t * 0.39 + p[0]) +
        0.2 * Math.sin(t * 0.97 + p[1]) +
        0.1 * Math.sin(t * 2.3 + p[2]),
    );
  const rush = sweep(noise(length, rand), sampleRate, "lowpass", (t) => 220 + 700 * gust(t), 0.7);
  const moan = sweep(noise(length, rand), sampleRate, "bandpass", (t) => 360 + 150 * gust(t), 30);
  const whistle = sweep(
    noise(length, rand),
    sampleRate,
    "bandpass",
    (t) => 1150 + 300 * gust(t),
    45,
  );
  const out = new Float32Array(length);
  for (let i = 0; i < length; i++) {
    const g = gust(i / sampleRate);
    out[i] = rush[i] * g + moan[i] * 2.4 * g ** 2 + whistle[i] * 1.2 * g ** 3;
  }
  const knocks = new Float32Array(length);
  for (let k = 0; k < 4; k++) {
    const at = Math.floor(rand() * (length - sampleRate));
    knocks[at] = 0.6 + rand() * 0.4;
    knocks[at + seconds(0.09 + rand() * 0.05, sampleRate)] = 0.3 + rand() * 0.2;
  }
  const shutter = modal(knocks, sampleRate, [
    [240, 0.035, 1],
    [570, 0.022, 0.7],
    [1190, 0.013, 0.4],
  ]);
  for (let i = 0; i < length; i++) out[i] += shutter[i] * 0.9;
  return normalise(wrapLoop(out, sampleRate, fade), 0.7);
}

/**
 * The old house settling: a dry tick or pop where a joint shifts in the damp,
 * sometimes a short, light creak after it. Light and brief, never the long
 * groan of a board taking a body's weight (that belongs to the shadow form).
 */
export function houseSettle(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(0.6, sampleRate);
  const pop = new Float32Array(length);
  pop[seconds(0.01, sampleRate)] = 1;
  if (rand() < 0.6) pop[seconds(0.03 + rand() * 0.05, sampleRate)] = 0.4 + rand() * 0.3;
  const s = 0.8 + rand() * 0.5;
  const out = modal(pop, sampleRate, [
    [880 * s, 0.012, 1],
    [1530 * s, 0.009, 0.8],
    [2620 * s, 0.006, 0.55],
    [410 * s, 0.018, 0.6],
  ]);
  for (let i = 0; i < length; i++) out[i] *= 2;
  if (rand() < 0.65) {
    const d = 0.18 + rand() * 0.2;
    const creak = modal(
      stickSlip(
        seconds(d, sampleRate),
        sampleRate,
        rand,
        (t) => 120 + 140 * (t / d),
        (t) => Math.sin((Math.PI * t) / d) ** 1.5 * 0.5,
        0.3,
      ),
      sampleRate,
      [
        [640 * s, 0.02, 1],
        [1110 * s, 0.014, 0.6],
        [1890 * s, 0.009, 0.35],
      ],
    );
    mix(out, creak, sampleRate, 0.04 + rand() * 0.05, 1, () => 1);
  }
  return normalise(out, 0.7);
}

/**
 * Under the house: rain dripping through the floorboards above, each leak
 * keeping its own slow, uneven beat, landing in puddles, in the mud, and one
 * into an open jar with a deep, hollow plonk.
 */
export function floorDrips(sampleRate: number, rand: () => number): Float32Array {
  const fade = 0.5;
  const length = seconds(10 + fade, sampleRate);
  const out = new Float32Array(length);
  const jar = new Float32Array(length);
  for (let leak = 0; leak < 7; leak++) {
    const beat = 0.5 + rand() * 1.8;
    const into = leak === 0 ? "jar" : leak < 4 ? "puddle" : "mud";
    const pitch = 600 + rand() * 1400;
    for (let at = rand() * beat; at < 10 + fade - 0.1; at += beat * (0.75 + rand() * 0.5)) {
      if (into === "jar") {
        jar[seconds(at, sampleRate)] = 0.7 + rand() * 0.3;
        mix(out, bubble(sampleRate, 380 + rand() * 60, 0.03, 0.3), sampleRate, at, 0.4, () => 1);
      } else if (into === "puddle") {
        mix(
          out,
          bubble(sampleRate, pitch * (0.92 + rand() * 0.16), 0.008 + rand() * 0.006),
          sampleRate,
          at,
          0.35 + rand() * 0.3,
          () => 1,
        );
        mix(
          out,
          biquad(noise(seconds(0.02, sampleRate), rand), sampleRate, "highpass", 2500, 0.7),
          sampleRate,
          at,
          0.15,
          (t) => Math.exp(-t / 0.003),
        );
      } else {
        mix(
          out,
          biquad(noise(seconds(0.04, sampleRate), rand), sampleRate, "lowpass", 700, 0.8),
          sampleRate,
          at,
          0.5 + rand() * 0.3,
          (t) => Math.exp(-t / 0.008),
        );
      }
    }
  }
  const hollow = modal(jar, sampleRate, [
    [176, 0.12, 1],
    [412, 0.07, 0.6],
    [705, 0.04, 0.35],
  ]);
  for (let i = 0; i < length; i++) out[i] += hollow[i] * 1.3;
  // The rain all around the edges of the house, heard low and close to the ground.
  const edge = biquad(noise(length, rand), sampleRate, "lowpass", 1800, 0.6);
  for (let i = 0; i < length; i++) out[i] += edge[i] * 0.06;
  return normalise(wrapLoop(out, sampleRate, fade), 0.8);
}

/**
 * Sora's heart while she hides (S1-026), heard from inside her own chest: the
 * deep "lub" of the valves closing and the shorter, higher "dub", fast with fear.
 */
export function heartbeat(sampleRate: number, rand: () => number): Float32Array {
  const period = 0.68;
  const length = seconds(period, sampleRate);
  const out = new Float32Array(length);
  for (const [at, f, d, gain] of [
    [0.004, 46 + rand() * 4, 0.05, 1],
    [0.215, 62 + rand() * 4, 0.035, 0.7],
  ]) {
    const n = seconds(0.2, sampleRate);
    const beat = new Float32Array(n);
    let phase = 0;
    for (let i = 0; i < n; i++) {
      const t = i / sampleRate;
      phase += (f * (1 + 0.4 * Math.exp(-t / 0.015))) / sampleRate;
      beat[i] = Math.sin(2 * Math.PI * phase) * (1 - Math.exp(-t / 0.004)) * Math.exp(-t / d);
    }
    const valve = biquad(noise(n, rand), sampleRate, "bandpass", 140, 1.5);
    for (let i = 0; i < n; i++) beat[i] += valve[i] * 0.5 * Math.exp(-i / sampleRate / 0.012);
    mix(out, beat, sampleRate, at, gain, () => 1);
  }
  biquad(out, sampleRate, "lowpass", 400, 0.7);
  return normalise(out, 0.45);
}

/**
 * A 78 rpm shellac record's surface: the hiss of the groove, crackle where
 * grit sits in it, the deep rumble of the turntable, and the scratch that
 * comes round once a turn. Five turns, so the loop keeps the beat.
 */
export function shellacNoise(sampleRate: number, rand: () => number): Float32Array {
  const turn = 60 / 78;
  const length = seconds(turn * 5, sampleRate);
  const hiss = biquad(noise(length, rand), sampleRate, "bandpass", 3500, 0.7);
  const rumble = biquad(brown(length, rand, 0.995), sampleRate, "lowpass", 60, 0.7);
  const out = new Float32Array(length);
  for (let i = 0; i < length; i++) out[i] = hiss[i] * 0.5 + rumble[i] * 0.3;
  const crackle = scatter(length, rand, 260, 4);
  const pops = biquad(crackle, sampleRate, "highpass", 900, 0.7);
  for (let i = 0; i < length; i++) out[i] += pops[i] * 1.6;
  const scratchAt = rand() * turn;
  for (let k = 0; k < 5; k++)
    mix(
      out,
      biquad(noise(seconds(0.012, sampleRate), rand), sampleRate, "bandpass", 1800, 1),
      sampleRate,
      scratchAt + k * turn,
      0.5,
      (t) => Math.exp(-t / 0.003),
    );
  const n = seconds(0.02, sampleRate);
  for (let i = 0; i < n; i++) {
    out[i] *= i / n;
    out[length - 1 - i] *= i / n;
  }
  return normalise(out, 0.33);
}

/**
 * The shadow form scenting the air where it lost her (S1-031, "investigate
 * sniff"): three sharp, wet draws through a big nose, then a held breath.
 */
export function sniff(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(1, sampleRate);
  const out = new Float32Array(length);
  let at = 0.02;
  for (let k = 0; k < 3; k++) {
    const d = 0.09 + rand() * 0.05;
    const draw = formant(noise(seconds(d, sampleRate), rand), sampleRate, [
      [380, 120, 0.7],
      [1350, 300, 1],
      [2900, 600, 0.6],
    ]);
    mix(
      out,
      draw,
      sampleRate,
      at,
      1 - k * 0.12,
      (t) => Math.min(1, t / 0.012) * Math.exp(-t / (d * 0.5)),
    );
    // Wet: a click of mucus in the nostril.
    mix(out, bubble(sampleRate, 900 + rand() * 600, 0.003), sampleRate, at + d * 0.4, 0.2, () => 1);
    at += d + 0.06 + rand() * 0.05;
  }
  return normalise(out, 0.7);
}
