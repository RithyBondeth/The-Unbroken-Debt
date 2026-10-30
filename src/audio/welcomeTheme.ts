/** Original 32-second title motif: imperfect bell partials, long rests, distant
 * reflections. The final rest makes the loop seamless without timers or clicks.
 */
export function welcomeTheme(rate: number): Float32Array {
  const samples = new Float32Array(rate * 32);
  const notes = [
    [1.8, 146.83],
    [5.6, 220],
    [11.2, 155.56],
    [16, 110],
    [20.8, 164.81],
    [24.6, 146.83],
  ];
  for (const [at, frequency] of notes)
    for (const [delay, gain] of [
      [0, 1],
      [0.43, 0.26],
      [0.91, 0.12],
    ]) {
      const start = Math.round((at + delay) * rate);
      for (let i = 0; i < rate * 5.5 && start + i < samples.length; i++) {
        const t = i / rate;
        const attack = Math.min(1, t / 0.09);
        const tail = Math.min(1, (5.5 - t) / 0.6);
        const bell =
          Math.sin(t * frequency * Math.PI * 2) * Math.exp(-t / 1.75) * 0.075 +
          Math.sin(t * frequency * 2.013 * Math.PI * 2) * Math.exp(-t / 0.9) * 0.021 +
          Math.sin(t * frequency * 3.971 * Math.PI * 2) * Math.exp(-t / 0.5) * 0.008;
        samples[start + i] += bell * attack * tail * gain;
      }
    }
  return samples;
}
