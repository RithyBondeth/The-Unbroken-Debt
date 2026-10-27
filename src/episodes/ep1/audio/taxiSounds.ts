import { biquad, brown, noise, normalise } from "../../../audio/synth";

/** Motor, wet tyres and a two-stroke wiper loop. No dialogue or borrowed recordings. */
export function taxiMotor(rate: number, random: () => number): Float32Array {
  const n = rate * 6,
    out = new Float32Array(n);
  const road = biquad(brown(n, random), rate, "lowpass", 420, 0.7);
  for (let i = 0; i < n; i++) {
    const t = i / rate,
      fade = Math.min(1, t * 30, (6 - t) * 30);
    out[i] =
      fade *
      (road[i] * 0.8 +
        Math.sin(t * Math.PI * 2 * 48) * 0.08 +
        Math.sin(t * Math.PI * 2 * 96) * 0.025);
  }
  return normalise(out, 0.5);
}
export function taxiWipers(rate: number, random: () => number): Float32Array {
  const n = Math.round(rate * 1.8),
    out = biquad(noise(n, random), rate, "bandpass", 1450, 0.8);
  for (let i = 0; i < n; i++) {
    const t = i / rate,
      phase = (t % 0.9) / 0.9;
    out[i] *= Math.sin(Math.PI * phase) ** 7 * 0.5;
    if (phase < 0.055) out[i] += Math.sin(2 * Math.PI * 240 * t) * (1 - phase / 0.055) * 0.05;
  }
  return normalise(out, 0.32);
}
