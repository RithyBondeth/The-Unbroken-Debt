import { biquad, bubble, mix, noise, normalise } from "@/audio/synth";

/**
 * Something going into the pond: a heavy body's slap on still water, the
 * gulp of the hole closing over it, a spray falling back, then bubbles coming
 * up for a while and a last few drips off the jetty. Mono, peak 0.9.
 */
export function pondSplash(sampleRate: number, rand: () => number): Float32Array {
  const out = new Float32Array(Math.round(4.2 * sampleRate));
  // The slap: broadband, short, low-heavy.
  const slap = biquad(noise(Math.round(0.35 * sampleRate), rand), sampleRate, "lowpass", 900, 0.7);
  mix(out, slap, sampleRate, 0.0, 1.0, (t) => Math.exp(-t / 0.06));
  // The water closing: a falling low tone.
  const gulp = new Float32Array(Math.round(0.5 * sampleRate));
  let phase = 0;
  for (let i = 0; i < gulp.length; i++) {
    const t = i / sampleRate;
    phase += (140 - 90 * Math.min(1, t / 0.25)) / sampleRate;
    gulp[i] = Math.sin(2 * Math.PI * phase) * Math.exp(-t / 0.12);
  }
  mix(out, gulp, sampleRate, 0.05, 0.8, () => 1);
  // Spray falling back: a hiss of droplets.
  const spray = biquad(
    noise(Math.round(1.1 * sampleRate), rand),
    sampleRate,
    "bandpass",
    3200,
    0.8,
  );
  mix(out, spray, sampleRate, 0.12, 0.45, (t) => Math.min(1, t / 0.05) * Math.exp(-t / 0.35));
  // Bubbles rising for a few seconds, fewer and fewer.
  for (let k = 0; k < 26; k++) {
    const at = 0.35 + Math.pow(rand(), 1.6) * 3.2;
    const f = 380 + rand() * 900;
    mix(
      out,
      bubble(sampleRate, f, 0.012 + rand() * 0.02),
      sampleRate,
      at,
      0.25 * (1 - at / 4),
      () => 1,
    );
  }
  // Drips off the boards.
  for (let k = 0; k < 5; k++) {
    const at = 1.4 + rand() * 2.5;
    mix(out, bubble(sampleRate, 1400 + rand() * 1200, 0.006), sampleRate, at, 0.3, () => 1);
  }
  return normalise(out);
}
