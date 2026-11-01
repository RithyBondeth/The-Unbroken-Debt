import { TAXI_CONVERSATION } from "./taxiConversation";
import { taxiFlinch } from "./taxiApparitions";

/** Weights (0–1) for the driver's baked shapes; blinking is timed separately. */
export interface DriverFace {
  talk: number;
  look_road: number;
  look_sora: number;
  nod: number;
  grip: number;
}

const ease = (x: number) => {
  const c = Math.max(0, Math.min(1, x));
  return c * c * (3 - 2 * c);
};
/** Rises over `rise` s from `from`, holds, falls over `fall` s to `to`. */
const window = (t: number, from: number, to: number, rise = 0.4, fall = 0.5) =>
  Math.min(ease((t - from) / rise), ease((to - t) / fall));
const hash = (n: number) => {
  const x = Math.sin(n * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
};

/**
 * What the driver's face and hands do at ride time `t`. Speaking, his jaw moves
 * gently on syllables about three a second, closing between words and at the
 * end of the line; he glances round to Sora as he starts, then back to the road,
 * nodding on the stressed words and tapping two fingers on the rim. When
 * Sora speaks he half turns to listen. Otherwise he watches the road, except
 * while he keeps looking into the trees (20–34 s), and the shock of the crossing
 * snaps his eyes forward.
 */
export function taxiDriverFace(t: number): DriverFace {
  let talk = 0,
    sora = 0,
    nod = 0,
    grip = 0.12 * Math.max(0, Math.sin(t * 0.7)) ** 8;
  for (const [index, line] of TAXI_CONVERSATION.entries()) {
    const end = line.at + line.seconds,
      inLine = window(t, line.at, end, 0.25, 0.4);
    if (inLine <= 0) continue;
    const s = t - line.at;
    if (line.speaker === "Driver") {
      const syllable = s * 3.1 + hash(index) * 3,
        word = Math.floor(syllable / 3.2),
        within = syllable - word * 3.2,
        open = within < 2.6 ? Math.sin((within % 1) * Math.PI) ** 1.4 : 0;
      // The baked shape is a full jaw drop: speech only ever parts the lips a little.
      talk = inLine * open * (0.14 + 0.12 * hash(index * 31 + word)) * ease((end - t) / 0.3);
      sora = Math.max(sora, window(t, line.at, line.at + line.seconds * 0.45, 0.35, 0.6) * 0.75);
      nod = inLine * 0.55 * Math.max(0, Math.sin(s * 2.4 + hash(index))) ** 6;
      // Two fingers of his near hand lift and tap the rim as he talks.
      const taps = 0.5 + 0.5 * Math.sin(s * 7);
      grip = Math.max(grip, window(t, line.at + 0.6, line.at + 2.6, 0.3, 0.5) * 0.85 * taps);
    } else {
      sora = Math.max(sora, window(t, line.at + 0.5, line.at + 2.2, 0.5, 0.7) * 0.4);
    }
  }
  // He keeps looking into the forest on Sora's side (his rest pose) while she asks
  // why, then mostly watches the road; the crossing snaps his eyes forward.
  const forest = Math.max(window(t, 20.5, 24, 0.8, 0.8), window(t, 26.5, 34, 0.8, 0.8));
  const road = Math.max(
    0.85 * (1 - forest) * (1 - sora),
    taxiFlinch(t),
    window(t, 44, 50, 0.4, 1.5) * 0.9,
  );
  return { talk, look_road: road, look_sora: sora * (1 - taxiFlinch(t)), nod, grip };
}
