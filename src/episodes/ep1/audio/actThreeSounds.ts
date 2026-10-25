import {
  biquad,
  bubble,
  formant,
  mix,
  modal,
  noise,
  normalise,
  softClip,
  stickSlip,
} from "../../../audio/synth";

/**
 * Synthesised stand-ins for Act III (Audio Design Document, section 8:
 * S1-029, S1-030, S1-033, S1-034) until the recordings exist. Mono, peak 0.9
 * or less, pure functions.
 */

const seconds = (s: number, sampleRate: number) => Math.round(s * sampleRate);

/**
 * Something knocking from inside the coffin (S1-029): a blow on the boards
 * that booms in the hollow box, the loose lid jumping and rattling back down,
 * the shroud's cloth shifting.
 */
export function coffinKnock(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(0.85, sampleRate);
  const blow = new Float32Array(length);
  for (let i = 0; i < seconds(0.006, sampleRate); i++)
    blow[i] = (rand() * 2 - 1) * Math.exp(-i / seconds(0.002, sampleRate));
  // The lid lifts and falls back: a few smaller, quickening knocks.
  let at = 0.06 + rand() * 0.02;
  for (let k = 0; k < 4; k++) {
    blow[seconds(at, sampleRate)] += (0.5 - k * 0.1) * (rand() < 0.5 ? -1 : 1);
    at += 0.045 - k * 0.008;
  }
  const out = modal(blow, sampleRate, [
    [88, 0.09, 1],
    [151, 0.07, 0.85],
    [243, 0.05, 0.7],
    [520, 0.03, 0.5],
    [870, 0.02, 0.4],
    [1430, 0.012, 0.25],
  ]);
  const cloth = biquad(noise(length, rand), sampleRate, "bandpass", 1600, 0.7);
  for (let i = 0; i < length; i++) {
    const t = i / sampleRate;
    out[i] = out[i] * 8 + cloth[i] * 0.05 * Math.sin(Math.min(1, t / 0.5) * Math.PI);
  }
  return normalise(out, 0.8);
}

/**
 * A fired-clay lid lifted off a water jar (S1-030): grit grinding clay on
 * clay, the jar's rim ringing as it comes free, the water inside slopping.
 */
export function jarLid(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(0.7, sampleRate);
  const clay: [number, number, number][] = [
    [690 + rand() * 60, 0.05, 1],
    [1620, 0.035, 0.7],
    [2870, 0.02, 0.45],
    [4300, 0.012, 0.3],
  ];
  const grind = stickSlip(
    seconds(0.35, sampleRate),
    sampleRate,
    rand,
    (t) => 260 + 400 * (t / 0.35),
    (t) => Math.sin((Math.PI * t) / 0.35) * 0.6,
    0.9,
  );
  const out = new Float32Array(length);
  mix(out, modal(grind, sampleRate, clay), sampleRate, 0.02, 1, () => 1);
  const free = new Float32Array(seconds(0.35, sampleRate));
  free[0] = 1;
  mix(out, modal(free, sampleRate, clay), sampleRate, 0.38, 1.5, () => 1);
  for (let k = 0; k < 5; k++)
    mix(
      out,
      bubble(sampleRate, 260 + rand() * 300, 0.02 + rand() * 0.02, 0.3),
      sampleRate,
      0.42 + rand() * 0.2,
      0.25,
      () => 1,
    );
  return normalise(out, 0.4);
}

/**
 * The fading screech as the token burns (S1-034): not a human voice, a high
 * shriek with a lower one grinding under it, both torn at the throat, the
 * stone grind of the Neak Ta beneath, drawn away into the wind.
 */
export function spiritShriek(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(2, sampleRate);
  const out = new Float32Array(length);
  for (const [base, fall, gain, mouth] of [
    [1050, 420, 1, [1300, 2200, 3600]],
    [370, 110, 0.6, [700, 1250, 2600]],
  ] as const) {
    const buzz = new Float32Array(length);
    let phase = 0,
      wobble = 0;
    for (let i = 0; i < length; i++) {
      const t = i / sampleRate;
      wobble += (rand() - 0.5) * 0.03 - wobble * 0.003;
      phase += ((base - fall * t + 30 * Math.sin(t * 31)) * (1 + wobble)) / sampleRate;
      if (phase >= 1) phase -= 1;
      buzz[i] = phase * 2 - 1;
    }
    const v = formant(buzz, sampleRate, [
      [mouth[0], 160, 1],
      [mouth[1], 220, 0.7],
      [mouth[2], 360, 0.35],
    ]);
    softClip(normalise(v, 1), 2.5);
    mix(out, v, sampleRate, 0, gain, (t) => Math.min(1, t / 0.04) * Math.exp(-t * 1.9));
  }
  const grind = modal(
    stickSlip(
      length,
      sampleRate,
      rand,
      (t) => 30 + 25 * t,
      (t) => Math.exp(-t * 1.2),
      0.9,
    ),
    sampleRate,
    [
      [170, 0.02, 1],
      [390, 0.012, 0.6],
      [820, 0.008, 0.4],
    ],
  );
  const wind = biquad(noise(length, rand), sampleRate, "bandpass", 700, 0.7);
  for (let i = 0; i < length; i++) {
    const t = i / sampleRate;
    out[i] += grind[i] * 1.2 + wind[i] * 0.25 * Math.min(1, t / 0.6) * Math.exp(-t * 0.8);
  }
  return normalise(out, 0.6);
}

/**
 * The ritual's wordless timing stand-in until the licensed chant is recorded
 * (S1-038): no voice and no invented text, only a low drone and its fifth,
 * each doubled a fraction off so they beat slowly, swelling and falling like
 * a long breath.
 */
export function ritualDrone(sampleRate: number, rand: () => number): Float32Array {
  const length = seconds(4, sampleRate);
  const out = new Float32Array(length);
  const p = rand() * 6;
  for (let i = 0; i < length; i++) {
    const t = i / sampleRate;
    let v = 0;
    for (const [f, g] of [
      [98, 0.12],
      [98.5, 0.06],
      [196, 0.03],
      [147, 0.05],
      [147.5, 0.025],
      [294, 0.01],
    ])
      v += Math.sin(2 * Math.PI * f * t + p * f) * g;
    out[i] = v * Math.sin((Math.PI * t) / 4) ** 2;
  }
  return normalise(out, 0.17);
}
