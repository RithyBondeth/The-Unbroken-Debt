import { biquad, noise, normalise } from "../../../audio/synth";

/** A2-01 cold gust, a wordless stand-in until the recorded wind cue exists. */
export function coldGust(sampleRate: number, rand: () => number): Float32Array {
  const out = biquad(noise(Math.round(sampleRate * 2.4), rand), sampleRate, "lowpass", 900, 0.7);
  for (let i = 0; i < out.length; i++) out[i] *= Math.sin((Math.PI * i) / out.length) ** 2;
  return normalise(out, 0.75);
}
