import { biquad, formant, mix, modal, noise, normalise, softClip, stickSlip } from "../synth";

const seconds = (s: number, sampleRate: number) => Math.round(s * sampleRate);

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
