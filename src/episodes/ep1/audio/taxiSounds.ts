import { biquad, brown, modal, noise, normalise, stickSlip, wrapLoop } from "../../../audio/synth";

/**
 * A 1930s four-cylinder touring car heard from the back seat, 10 s loop: each
 * cylinder's firing a slightly different size (old plugs, worn rings), pulsing
 * through the exhaust and the steel body; the tappets ticking; the gearbox
 * whining; tyres hissing on a flooded laterite road, splashing through
 * puddles and thumping over ruts while the body rattles. No borrowed recordings.
 */
export function taxiMotor(rate: number, random: () => number): Float32Array {
  const n = Math.round(rate * 10.5),
    pulses = new Float32Array(n),
    ticks = new Float32Array(n),
    knocks = new Float32Array(n);
  const sizes = [1, 0.82, 0.94, 0.77];
  let phase = 0,
    cylinder = 0;
  for (let i = 0; i < n; i++) {
    const t = i / rate;
    // About 1150 rpm, labouring a little as the road climbs and the mud drags.
    const firing = 38 * (1 + 0.035 * Math.sin(t * 0.9) + 0.015 * Math.sin(t * 2.7 + 1));
    phase += firing / rate;
    if (phase >= 1) {
      phase -= 1;
      cylinder = (cylinder + 1) % 4;
      pulses[i] = sizes[cylinder] * (0.85 + 0.3 * random());
      ticks[i] = 0.4 + 0.6 * random();
    }
  }
  // Exhaust and body resonances, heard through the floor.
  const exhaust = modal(pulses, rate, [
    [76, 0.045, 1],
    [152, 0.03, 0.55],
    [233, 0.02, 0.4],
    [410, 0.012, 0.22],
    [690, 0.007, 0.12],
  ]);
  const tappets = biquad(
    modal(ticks, rate, [[Math.min(3100, rate * 0.4), 0.003, 1]]),
    rate,
    "highpass",
    Math.min(1800, rate * 0.4),
    0.7,
  );
  const tyres = biquad(noise(n, random), rate, "bandpass", Math.min(2600, rate * 0.4), 0.45);
  const road = biquad(brown(n, random), rate, "lowpass", 220, 0.7);
  // Ruts and potholes: a dull thump under the car, the body rattling after it.
  for (let t = 0.7; t < 10; t += 1.1 + random() * 1.7)
    knocks[Math.round(t * rate)] = 0.5 + random() * 0.5;
  const thumps = modal(knocks, rate, [
    [48, 0.09, 1],
    [97, 0.05, 0.5],
  ]);
  const rattle = biquad(
    modal(
      stickSlip(
        n,
        rate,
        random,
        () => 70,
        (t) => Math.exp(-((t % 1.4) * 9)),
        0.8,
      ),
      rate,
      [
        [Math.min(1240, rate * 0.4), 0.01, 0.6],
        [Math.min(2230, rate * 0.4), 0.006, 0.4],
      ],
    ),
    rate,
    "highpass",
    900,
    0.7,
  );
  const out = new Float32Array(n);
  let splash = 0;
  for (let i = 0; i < n; i++) {
    const t = i / rate;
    // Through a puddle every few seconds: the hiss surges and water hits the arches.
    if (i % Math.round(rate * 3.3) === Math.round(rate * 1.9)) splash = 1;
    splash *= Math.exp(-1 / (rate * 0.35));
    const whine = Math.sin(2 * Math.PI * 38 * 11.5 * t) * 0.012;
    out[i] =
      exhaust[i] * 0.32 +
      tappets[i] * 0.05 +
      tyres[i] * (0.18 + splash * 0.9) +
      road[i] * 0.9 +
      thumps[i] * 0.35 +
      rattle[i] * 0.06 +
      whine;
  }
  // Inside the cabin the highs are dulled by the body and the rain on it.
  return normalise(
    wrapLoop(biquad(out, rate, "lowpass", Math.min(3800, rate * 0.4), 0.7), rate, 0.5),
    0.5,
  );
}

/**
 * Vacuum-driven wipers, as 1930s cars had: slow and never quite even (the
 * vacuum sags when the engine labours), the rubber juddering and squeaking on
 * wet glass, the linkage knocking at each end of the sweep and the motor's
 * faint hiss under it. About 6 s loop.
 */
export function taxiWipers(rate: number, random: () => number): Float32Array {
  const strokes = [1.05, 1.2, 1.12, 1.31, 1.08];
  const total = strokes.reduce((a, b) => a + b, 0);
  const n = Math.round(rate * (total + 0.3));
  const out = new Float32Array(n);
  const water = biquad(noise(n, random), rate, "bandpass", Math.min(1450, rate * 0.4), 0.8);
  const hiss = biquad(noise(n, random), rate, "highpass", Math.min(3000, rate * 0.4), 0.7);
  const judder = modal(
    stickSlip(
      n,
      rate,
      random,
      (t) => 90 + 50 * Math.sin(t * 5),
      () => 1,
      0.5,
    ),
    rate,
    [
      [Math.min(1900, rate * 0.4), 0.004, 1],
      [Math.min(3400, rate * 0.4), 0.002, 0.5],
    ],
  );
  const clunk = modal(new Float32Array([1]), rate, [
    [180, 0.03, 1],
    [520, 0.012, 0.4],
  ]);
  let start = 0;
  for (const seconds of strokes) {
    const from = Math.round(start * rate),
      to = Math.round((start + seconds) * rate);
    for (let i = from; i < to && i < n; i++) {
      const p = (i - from) / (to - from);
      // Fast in the middle of the sweep, slowing into each end.
      const speed = Math.sin(Math.PI * p);
      out[i] += water[i] * speed ** 2 * 0.5 + judder[i] * speed ** 3 * 0.12;
    }
    for (let i = 0; i < clunk.length && to + i < n; i++) out[to + i] += clunk[i] * 0.12;
    start += seconds;
  }
  for (let i = 0; i < n; i++) out[i] += hiss[i] * 0.01;
  return normalise(wrapLoop(out, rate, 0.3), 0.32);
}
