import { formant, noise, normalise, wrapLoop } from "../../../audio/synth";

/** Wordless female-like lament, breath and subharmonics; original synthesized audio. */
export function krasueLament(rate: number, rand: () => number): Float32Array {
  const out = new Float32Array(Math.round(rate * 6.25));
  const air = formant(noise(out.length, rand), rate, [
    [730, 180, 0.7],
    [1350, 220, 0.6],
    [3100, 450, 0.3],
  ]);
  let phase = 0;
  for (let i = 0; i < out.length; i++) {
    const t = i / rate;
    phase += (185 + Math.sin(t * 0.94) * 38 + Math.sin(t * 32) * 3) / rate;
    const swell = 0.3 + 0.7 * (0.5 + 0.5 * Math.sin((t * Math.PI) / 3 - 1)) ** 2;
    const voiced = Math.sin(phase * Math.PI * 2) * 0.36 + Math.sin(phase * Math.PI * 4.016) * 0.13;
    out[i] = (voiced + air[i] * 1.8 + Math.sin(t * Math.PI * 2 * 43) * 0.09) * swell;
  }
  return normalise(wrapLoop(out, rate, 0.25), 0.48);
}

/** An immediate open-vowel scream, with breath, a ragged rise and dying tail. */
export function krasueShriek(rate: number, rand: () => number): Float32Array {
  const out = new Float32Array(Math.round(rate * 2.4));
  const excitation = noise(out.length, rand);
  let phase = 0;
  for (let i = 0; i < out.length; i++) {
    const t = i / rate;
    phase +=
      (570 + Math.sin((Math.min(1, t / 0.35) * Math.PI) / 2) * 260 + Math.sin(t * 47) * 29) / rate;
    excitation[i] =
      Math.sin(phase * Math.PI * 2) * 0.6 +
      Math.sin(phase * Math.PI * 4) * 0.2 +
      excitation[i] * 0.45;
  }
  const voice = formant(excitation, rate, [
    [850, 260, 1],
    [1700, 350, 0.7],
    [2900, 450, 0.5],
    [3800, 650, 0.3],
  ]);
  for (let i = 0; i < out.length; i++) {
    const t = i / rate;
    const envelope = Math.min(1, t / 0.025) * Math.min(1, (2.4 - t) / 0.45);
    out[i] = Math.tanh(voice[i] * 2.8) * envelope * (0.85 + Math.sin(t * 53) * 0.15);
  }
  out[out.length - 1] = 0;
  return normalise(out, 0.6);
}
