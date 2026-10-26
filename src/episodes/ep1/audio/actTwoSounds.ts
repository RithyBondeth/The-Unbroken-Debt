import { biquad, brown, mix, modal, noise, normalise, sweep } from "../../../audio/synth";

/**
 * A2-01 cold gust, a wordless stand-in until the recorded wind cue exists: air
 * rushing in and brightening as it peaks, moaning through the gaps in the
 * shutters, the cloth hangings flapping, and the shutters knocking in their frames.
 */
export function coldGust(sampleRate: number, rand: () => number): Float32Array {
  const length = Math.round(sampleRate * 2.4);
  const strength = (t: number) => Math.sin((Math.PI * t) / 2.4) ** 2;
  const rush = sweep(
    noise(length, rand),
    sampleRate,
    "lowpass",
    (t) => 280 + 1500 * strength(t),
    0.7,
  );
  const body = biquad(brown(length, rand, 0.995), sampleRate, "lowpass", 160, 0.7);
  // The moan: air over a gap, a narrow resonance that rises as the gust pushes harder.
  const moan = sweep(
    noise(length, rand),
    sampleRate,
    "bandpass",
    (t) => 330 + 190 * strength(t),
    28,
  );
  const moan2 = sweep(
    noise(length, rand),
    sampleRate,
    "bandpass",
    (t) => 495 + 260 * strength(t),
    32,
  );
  const flap = biquad(noise(length, rand), sampleRate, "bandpass", 900, 0.8);
  const out = new Float32Array(length);
  for (let i = 0; i < length; i++) {
    const t = i / sampleRate;
    const s = strength(t);
    const flutter = 0.5 + 0.5 * Math.sin(t * 2 * Math.PI * (7 + 6 * s)) ** 2;
    out[i] =
      rush[i] * s * 0.9 +
      body[i] * s * 3 +
      (moan[i] * 3.2 + moan2[i] * 1.8) * s ** 1.5 +
      flap[i] * 0.25 * s ** 2 * flutter;
  }
  // The shutters knocking in their frames at the height of it.
  const knocks = new Float32Array(length);
  for (let k = 0; k < 5; k++)
    knocks[Math.round((0.8 + rand() * 0.9) * sampleRate)] = 0.5 + rand() * 0.5;
  const wood = modal(knocks, sampleRate, [
    [260, 0.03, 1],
    [610, 0.02, 0.7],
    [1240, 0.012, 0.4],
  ]);
  mix(out, wood, sampleRate, 0, 2.5, () => 1);
  return normalise(out, 0.75);
}
