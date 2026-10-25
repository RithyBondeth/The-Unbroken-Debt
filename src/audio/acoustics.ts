import { biquad, noise } from "./synth";

/**
 * The spaces of Episode 1 and how they sound (Audio Design Document, section
 * 3, "Reverb"). Every sound on the effects, threat and voice buses is sent
 * into the current space's reverb, so a step upstairs rings off teak walls and
 * the same step under the house dies in the mud and the low boards.
 */
export type SpaceName = "studio" | "house" | "wardrobe" | "underHouse" | "tent" | "outdoors";

export interface Space {
  /** Seconds the late tail takes to fall 60 dB, in the lows, mids and highs. */
  rt60: [low: number, mid: number, high: number];
  /** Seconds before the first reflection: the distance to the nearest surface. */
  preDelay: number;
  /** Early reflections [seconds, gain]: the walls, floor and ceiling one by one. */
  early: [number, number][];
  /** How much of the reverb is heard (send level, linear). */
  wet: number;
  /**
   * What reaches the listener of the open-air ambience (rain, frogs, the
   * chant): low-pass cutoff in Hz and gain. Walls take the highs first.
   */
  occlusion: [cutoff: number, gain: number];
}

export const SPACES: Record<SpaceName, Space> = {
  // A small plastered room with shutters: bright, short.
  studio: {
    rt60: [0.55, 0.5, 0.32],
    preDelay: 0.004,
    early: [
      [0.006, 0.6],
      [0.009, 0.45],
      [0.013, 0.4],
      [0.018, 0.3],
      [0.024, 0.22],
    ],
    wet: 0.2,
    // The prologue's rain is already the rain heard from inside.
    occlusion: [20000, 1],
  },
  // A small wooden room up on stilts: warm, a little boomy, quick to die.
  house: {
    rt60: [0.7, 0.5, 0.22],
    preDelay: 0.003,
    early: [
      [0.005, 0.55],
      [0.008, 0.5],
      [0.011, 0.35],
      [0.016, 0.3],
      [0.021, 0.2],
    ],
    wet: 0.3,
    occlusion: [1300, 0.65],
  },
  // Shut in a wardrobe among the clothes (S1-026): close, dead, and the world
  // outside the door muffled.
  wardrobe: {
    rt60: [0.18, 0.1, 0.05],
    preDelay: 0.001,
    early: [
      [0.0015, 0.5],
      [0.003, 0.35],
    ],
    wet: 0.22,
    occlusion: [800, 0.5],
  },
  // Low and semi-open: mud below, boards a metre above. Boxy, a flutter between
  // floor and ceiling, and the open sides let the tail out fast.
  underHouse: {
    rt60: [0.45, 0.28, 0.12],
    preDelay: 0.002,
    early: [
      [0.003, 0.6],
      [0.006, 0.45],
      [0.009, 0.34],
      [0.012, 0.25],
      [0.015, 0.18],
      [0.018, 0.12],
    ],
    wet: 0.32,
    occlusion: [5000, 0.85],
  },
  // A cloth pavilion: little to reflect, and the cloth swallows the highs.
  tent: {
    rt60: [0.32, 0.24, 0.1],
    preDelay: 0.006,
    early: [
      [0.01, 0.3],
      [0.017, 0.2],
    ],
    wet: 0.16,
    occlusion: [12000, 0.95],
  },
  // A village at night in the rain: slapback from the houses and the treeline,
  // a long, dark tail scattered by wet foliage.
  outdoors: {
    rt60: [1.5, 1.0, 0.35],
    preDelay: 0.02,
    early: [
      [0.045, 0.35],
      [0.09, 0.25],
      [0.14, 0.2],
      [0.21, 0.14],
    ],
    wet: 0.2,
    occlusion: [20000, 1],
  },
};

/**
 * A stereo impulse response for `space`: its early reflections, alternating
 * between the ears, then a diffuse tail that dies faster in the highs than in
 * the lows. The two channels are decorrelated so the reverb surrounds the
 * listener instead of sitting between the ears.
 */
export function impulseResponse(
  sampleRate: number,
  rand: () => number,
  space: Space,
): [Float32Array, Float32Array] {
  const [low, mid, high] = space.rt60;
  const length = Math.round((Math.max(low, mid, high) * 1.1 + space.preDelay + 0.05) * sampleRate);
  const channels: [Float32Array, Float32Array] = [
    new Float32Array(length),
    new Float32Array(length),
  ];
  const start = Math.round(space.preDelay * sampleRate);
  // A level falls 60 dB in rt60 seconds: exp(-6.91 t / rt60).
  const fall = (rt60: number) => 6.91 / rt60;
  channels.forEach((out, c) => {
    const tail = noise(length, rand);
    const lows = biquad(tail.slice(), sampleRate, "lowpass", 300, 0.7);
    const highs = biquad(tail.slice(), sampleRate, "highpass", 3000, 0.7);
    for (let i = start; i < length; i++) {
      const t = (i - start) / sampleRate;
      const mids = tail[i] - lows[i] - highs[i];
      // The tail builds up over the first few milliseconds as reflections multiply.
      const onset = 1 - Math.exp(-t / 0.008);
      out[i] =
        onset *
        (lows[i] * Math.exp(-fall(low) * t) +
          mids * Math.exp(-fall(mid) * t) +
          highs[i] * Math.exp(-fall(high) * t)) *
        0.35;
    }
    space.early.forEach(([at, gain], k) => {
      const i = start + Math.round((at + (rand() - 0.5) * 0.0008) * sampleRate);
      if (i < length) out[i] += gain * ((k + c) % 2 ? 0.6 : 1) * (rand() < 0.2 ? -1 : 1);
    });
    // Surfaces absorb some highs with every bounce.
    biquad(out, sampleRate, "lowpass", 9000, 0.7);
  });
  return channels;
}
