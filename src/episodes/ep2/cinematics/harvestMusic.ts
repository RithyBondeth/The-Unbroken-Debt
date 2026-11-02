/** Original instrumental harvest phrase. No words, chants or sampled performances. */
export function harvestMusic(rate: number): Float32Array {
  const duration = 24,
    out = new Float32Array(rate * duration),
    notes = [0, 4, 7, 9, 7, 4, 2, 0, 2, 4, 7, 12, 9, 7, 4, 2];
  for (let beat = 0; beat < 64; beat++) {
    const at = beat * 0.375,
      f = 220 * 2 ** (notes[beat % notes.length] / 12);
    for (let i = 0; i < Math.min(rate * 0.9, out.length - at * rate); i++) {
      const t = i / rate,
        envelope = (1 - Math.exp(-t * 160)) * Math.exp(-t * 6);
      out[Math.floor(at * rate) + i] +=
        envelope *
        (Math.sin(Math.PI * 2 * f * t) +
          0.26 * Math.sin(Math.PI * 2 * f * 2.01 * t) +
          0.1 * Math.sin(Math.PI * 2 * f * 3.98 * t)) *
        0.16;
    }
    if (beat % 4 === 0)
      for (let i = 0; i < Math.min(rate * 1.2, out.length - at * rate); i++) {
        const t = i / rate;
        out[Math.floor(at * rate) + i] +=
          Math.sin(Math.PI * 2 * 110 * t) * Math.exp(-t * 3) * (1 - Math.exp(-t * 80)) * 0.07;
      }
  }
  // Both ends are quiet; loop wrap does not click or add a false footstep.
  for (let i = 0; i < rate * 0.04; i++) {
    out[i] *= i / (rate * 0.04);
    out[out.length - 1 - i] *= i / (rate * 0.04);
  }
  return out;
}
