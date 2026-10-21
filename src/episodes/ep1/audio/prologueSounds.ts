import { biquad, decay, mix, noise, normalise } from "../../../audio/synth";

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

/** Heavy monsoon rain on shutters and a tin roof: steady hiss, a low wash and drops. */
export function rainLoop(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(6, sampleRate);
  const hiss = biquad(noise(length, rand), sampleRate, "bandpass", 3200, 0.5);
  const wash = biquad(noise(length, rand), sampleRate, "lowpass", 380, 0.7);
  const out = new Float32Array(length);
  for (let i = 0; i < length; i++) out[i] = hiss[i] * 0.55 + wash[i] * 1.6;
  for (let k = 0; k < 260; k++) {
    const drop = biquad(
      noise(seconds(0.02, sampleRate), rand),
      sampleRate,
      "bandpass",
      1800 + rand() * 4000,
      4,
    );
    mix(out, drop, sampleRate, rand() * 5.95, 0.3 + rand() * 0.6, decay(0.004));
  }
  return seamless(normalise(out, 0.9), sampleRate, 0.3);
}

/** The mantel clock: tick and a lower tock, one second per loop. */
export function clockLoop(sampleRate: number, rand: () => number): Float32Array {
  const out = new Float32Array(sampleRate);
  for (const [at, f, gain] of [
    [0.01, 3200, 1],
    [0.51, 2300, 0.75],
  ]) {
    const click = biquad(noise(seconds(0.03, sampleRate), rand), sampleRate, "bandpass", f, 6);
    mix(out, click, sampleRate, at, gain, decay(0.006));
  }
  return normalise(out, 0.9);
}

/** The clock stopping: one heavy, dull knock. */
export function clockStop(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(0.6, sampleRate);
  const out = sine(length, sampleRate, (t) => 140 - t * 60);
  const knock = biquad(noise(length, rand), sampleRate, "bandpass", 900, 2);
  for (let i = 0; i < length; i++)
    out[i] = (out[i] * 0.8 + knock[i] * 0.4) * Math.exp(-i / sampleRate / 0.09);
  return normalise(out, 0.9);
}

/** A brass hand-crank telephone bell: a striker at 20 Hz for 1.6 s, then 2.4 s of quiet. */
export function phoneRing(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(4, sampleRate);
  const ring = seconds(1.6, sampleRate);
  const out = new Float32Array(length);
  const partials = [
    [1150, 1],
    [1720, 0.6],
    [2890, 0.35],
    [4150, 0.2],
  ];
  for (const [f, gain] of partials) {
    const tone = sine(ring, sampleRate, () => f);
    for (let i = 0; i < ring; i++) {
      const strike = (i / sampleRate) % 0.05;
      out[i] += tone[i] * gain * Math.exp(-strike / 0.02);
    }
  }
  mix(
    out,
    biquad(noise(ring, rand), sampleRate, "bandpass", 2600, 3),
    sampleRate,
    0,
    0.15,
    () => 1,
  );
  return seamless(normalise(out, 0.9), sampleRate, 0.01);
}

/** Crackle and hiss on a bad provincial line. */
export function lineStatic(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(3, sampleRate);
  const out = biquad(noise(length, rand), sampleRate, "bandpass", 1600, 0.8);
  for (let i = 0; i < length; i++) out[i] *= 0.35;
  for (let k = 0; k < 90; k++) {
    const crack = noise(seconds(0.006, sampleRate), rand);
    mix(out, crack, sampleRate, rand() * 2.99, 0.6 + rand(), decay(0.002));
  }
  return seamless(normalise(out, 0.8), sampleRate, 0.1);
}

/** The end of the call: a rising screech, glass breaking, heavy thuds, then the line cuts. */
export function callScream(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(3.2, sampleRate);
  const out = new Float32Array(length);
  const screech = sine(
    seconds(1.4, sampleRate),
    sampleRate,
    (t) => 900 + t * 1500 + Math.sin(t * 40) * 120,
  );
  const grit = biquad(noise(screech.length, rand), sampleRate, "bandpass", 2400, 1.5);
  for (let i = 0; i < screech.length; i++)
    screech[i] = Math.tanh((screech[i] + grit[i] * 0.8) * 2.5);
  mix(
    out,
    screech,
    sampleRate,
    0,
    0.8,
    (t) => Math.min(1, t / 0.15) * (t > 1.2 ? Math.max(0, 1 - (t - 1.2) / 0.2) : 1),
  );
  for (let k = 0; k < 40; k++) {
    const shard = sine(seconds(0.25, sampleRate), sampleRate, () => 3000 + rand() * 6000);
    mix(out, shard, sampleRate, 1.25 + rand() * 0.5, 0.25, decay(0.05));
  }
  mix(
    out,
    biquad(noise(seconds(0.4, sampleRate), rand), sampleRate, "highpass", 2500, 0.7),
    sampleRate,
    1.25,
    1,
    decay(0.12),
  );
  for (const at of [1.9, 2.25, 2.5]) {
    const thud = sine(seconds(0.4, sampleRate), sampleRate, (t) => 75 - t * 40);
    mix(out, thud, sampleRate, at, 1.2, decay(0.09));
  }
  return normalise(out, 0.9);
}

/** Thunder after the lightning: a crack, then a long low roll. */
export function thunder(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(5, sampleRate);
  const roll = biquad(noise(length, rand), sampleRate, "lowpass", 140, 0.8);
  const crack = biquad(noise(seconds(0.5, sampleRate), rand), sampleRate, "lowpass", 900, 0.7);
  const out = new Float32Array(length);
  mix(
    out,
    roll,
    sampleRate,
    0,
    1,
    (t) => Math.min(1, t / 0.3) * Math.exp(-t / 1.6) * (1 + 0.4 * Math.sin(t * 5)),
  );
  mix(out, crack, sampleRate, 0.05, 0.6, decay(0.15));
  return normalise(out, 0.9);
}

/** P07's fade: a train on the rails, wheels knocking over the joints. */
export function trainPassing(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(6, sampleRate);
  const out = biquad(noise(length, rand), sampleRate, "lowpass", 260, 0.7);
  for (let i = 0; i < length; i++) out[i] *= 0.6;
  for (let at = 0.2; at < 5.6; at += 0.42) {
    for (const lag of [0, 0.11]) {
      const knock = biquad(noise(seconds(0.05, sampleRate), rand), sampleRate, "bandpass", 420, 3);
      mix(out, knock, sampleRate, at + lag, 1.4, decay(0.02));
    }
  }
  for (let i = 0; i < length; i++) {
    const t = i / sampleRate;
    out[i] *= Math.min(1, t / 1.2) * Math.min(1, (6 - t) / 1.5);
  }
  return normalise(out, 0.9);
}

/** A pen nib scratching ink onto paper (P02). */
export function penScratch(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(0.9, sampleRate);
  const out = biquad(noise(length, rand), sampleRate, "bandpass", 5200, 1.2);
  for (let i = 0; i < length; i++) {
    const t = i / sampleRate;
    out[i] *= (0.6 + 0.4 * Math.sin(t * 38)) * Math.min(1, t / 0.05) * Math.min(1, (0.9 - t) / 0.2);
  }
  return normalise(out, 0.7);
}

/** Something light picked up: cloth and paper (P03, P04). */
export function pickUp(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(0.35, sampleRate);
  const out = biquad(noise(length, rand), sampleRate, "bandpass", 2400, 0.9);
  for (let i = 0; i < length; i++) {
    const t = i / sampleRate;
    out[i] *= Math.sin((Math.PI * t) / 0.35) ** 2;
  }
  return normalise(out, 0.6);
}

/** A wooden drawer dragged open. */
export function drawerOpen(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(0.55, sampleRate);
  const out = biquad(noise(length, rand), sampleRate, "bandpass", 700, 1.5);
  for (let i = 0; i < length; i++) {
    const t = i / sampleRate;
    out[i] *= (0.5 + 0.5 * Math.abs(Math.sin(t * 60))) * Math.min(1, (0.55 - t) / 0.1);
  }
  mix(
    out,
    biquad(noise(seconds(0.04, sampleRate), rand), sampleRate, "bandpass", 300, 2),
    sampleRate,
    0.48,
    2,
    decay(0.02),
  );
  return normalise(out, 0.8);
}

/** A candle flame snuffed by a draught. */
export function candleOut(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(0.7, sampleRate);
  const out = biquad(noise(length, rand), sampleRate, "lowpass", 600, 0.7);
  for (let i = 0; i < length; i++) {
    const t = i / sampleRate;
    out[i] *= Math.min(1, t / 0.15) * Math.exp(-t / 0.2);
  }
  return normalise(out, 0.6);
}
