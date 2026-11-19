import { biquad, bubble, mix, noise, normalise } from "@/audio/synth";

/**
 * A step through shin-deep paddy water: the slosh of the leg pushing through, the
 * suck of the foot leaving the mud under it, water running off the shin as it lifts,
 * a few drops and a bubble or two. About 0.6 s, mono, peak 0.9.
 */
export function wadeSplash(sampleRate: number, rand: () => number): Float32Array {
  const out = new Float32Array(Math.round(0.75 * sampleRate));
  // The slosh: low, rounded, a short swell and fall.
  const slosh = biquad(noise(Math.round(0.4 * sampleRate), rand), sampleRate, "lowpass", 520 + rand() * 260, 1.1);
  mix(out, slosh, sampleRate, 0.0, 1.0, (t) => Math.min(1, t / 0.03) * Math.exp(-t / 0.11));
  // Water pushed aside: mid splash.
  const splash = biquad(noise(Math.round(0.3 * sampleRate), rand), sampleRate, "bandpass", 1500 + rand() * 600, 0.9);
  mix(out, splash, sampleRate, 0.02, 0.55, (t) => Math.exp(-t / 0.07));
  // Running off the shin as the foot comes up: a thin trickle.
  const run = biquad(noise(Math.round(0.35 * sampleRate), rand), sampleRate, "bandpass", 3600 + rand() * 900, 1.4);
  mix(out, run, sampleRate, 0.18, 0.22, (t) => Math.min(1, t / 0.05) * Math.exp(-t / 0.12));
  // Drops falling back and a bubble from the mud.
  for (let k = 0; k < 4; k++)
    mix(out, bubble(sampleRate, 900 + rand() * 1500, 0.006 + rand() * 0.008), sampleRate,
      0.12 + rand() * 0.45, 0.22, () => 1);
  mix(out, bubble(sampleRate, 260 + rand() * 180, 0.03), sampleRate, 0.08 + rand() * 0.1, 0.35, () => 1);
  return normalise(out);
}
