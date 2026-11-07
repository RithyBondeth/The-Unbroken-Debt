import { formant, noise, normalise, sweep, wrapLoop } from "@/audio/synth";

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

/**
 * The scare as it swoops in out of the dark: a rush of air that closes fast, a
 * stab of clashing, bowed screeches and a low blow felt in the chest, then a
 * long ragged tail. Original synthesized audio; plays once per arrival.
 */
export function krasueSting(rate: number, rand: () => number): Float32Array {
  const length = 3.2;
  const out = new Float32Array(Math.round(rate * length));
  // The rush: air torn past it, brightening as it closes, cut off as it brakes.
  const rush = sweep(
    noise(out.length, rand),
    rate,
    "bandpass",
    (t) => 380 + 2600 * Math.min(1, t / 0.75) ** 1.6,
    1.4,
  );
  // A cluster of bowed, out-of-tune screeches a semitone apart, wavering.
  const cluster = [622, 659, 698, 741, 1245, 1319, 1397];
  const phases = cluster.map(() => rand());
  const bow = noise(out.length, rand);
  let thud = 0;
  for (let i = 0; i < out.length; i++) {
    const t = i / rate;
    const hit = Math.max(0, t - 0.04);
    let screech = 0;
    for (let k = 0; k < cluster.length; k++) {
      const f = cluster[k] * (1 + 0.012 * Math.sin(t * (21 + k * 3.7) + k) + 0.004 * bow[i]);
      phases[k] += f / rate;
      const p = phases[k] % 1;
      // A bowed string's saw, softened at the top.
      screech += (2 * p - 1) * (k < 4 ? 0.22 : 0.12);
    }
    const stab = hit > 0 ? Math.min(1, hit / 0.012) * (0.25 + 0.75 * Math.exp(-hit / 0.55)) : 0;
    const tail = Math.min(1, Math.max(0, length - t) / 0.9);
    // The blow: a falling sine, felt more than heard.
    thud += (46 - 18 * Math.min(1, hit / 0.6)) / rate;
    const body = hit > 0 ? Math.sin(thud * Math.PI * 2) * Math.exp(-hit / 0.42) * 0.9 : 0;
    const air = rush[i] * 2.4 * Math.min(1, t / 0.35) * Math.exp(-Math.max(0, t - 0.75) / 0.18);
    out[i] = (Math.tanh(screech * 1.6) * stab * 0.8 + body + air + bow[i] * stab * 0.06) * tail;
  }
  out[out.length - 1] = 0;
  return normalise(out, 0.85);
}
