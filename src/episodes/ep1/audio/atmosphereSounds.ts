import { biquad, mix, noise, normalise, wrapLoop } from "../../../audio/synth";

/** Wet leaves being brushed twice, followed by a smaller movement; no voice or attack cue. */
export function foliageMovement(rate: number, random: () => number): Float32Array {
  const out = new Float32Array(Math.round(rate * 4.6));
  for (const [at, duration, gain] of [
    [0.12, 1.05, 0.8],
    [1.55, 1.2, 1],
    [3.2, 0.9, 0.55],
  ]) {
    const take = biquad(noise(Math.round(rate * duration), random), rate, "bandpass", 1250, 0.65);
    const detail = biquad(noise(take.length, random), rate, "highpass", 3300, 0.7);
    for (let i = 0; i < take.length; i++) take[i] += detail[i] * 0.14;
    mix(
      out,
      take,
      rate,
      at,
      gain,
      (t) => Math.sin((Math.PI * t) / duration) ** 2 * (0.55 + 0.45 * Math.sin(t * 29) ** 2),
    );
  }
  return normalise(out, 0.6);
}

/** A low canopy wash with slow, irregular gusts; loop seam is crossfaded. */
export function canopyWind(rate: number, random: () => number): Float32Array {
  const out = biquad(noise(Math.round(rate * 15), random), rate, "lowpass", 850, 0.7);
  const phase = random() * Math.PI * 2;
  for (let i = 0; i < out.length; i++) {
    const t = i / rate;
    out[i] *=
      0.28 +
      0.42 * (0.5 + 0.5 * Math.sin(t * 0.51 + phase)) ** 2 +
      0.15 * Math.sin(t * 1.13 + 1.8) ** 2;
  }
  return normalise(wrapLoop(out, rate, 1), 0.45);
}

/** Soft pavilion cloth flexing in the wind, kept underneath the recitation. */
export function pavilionCloth(rate: number, random: () => number): Float32Array {
  const out = biquad(noise(Math.round(rate * 13), random), rate, "bandpass", 470, 0.65);
  for (let i = 0; i < out.length; i++) {
    const t = i / rate;
    const gust = Math.max(0, Math.sin(t * 0.63 + 0.8) + Math.sin(t * 1.17) * 0.35);
    out[i] *= 0.03 + gust * gust * (0.3 + 0.2 * Math.sin(t * 12.7) ** 2);
  }
  return normalise(wrapLoop(out, rate, 1), 0.4);
}
