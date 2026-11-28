import { TAXI_CONVERSATION } from "./taxiConversation";
import { TAXI_MIRROR, TAXI_STANDER, TAXI_WINDOW, taxiFlinch } from "./taxiApparitions";
import { taxiAnxietyLevel } from "./TaxiSoundscape";

/** Weights (0–1) for the driver's baked head/face shapes; blinking is timed separately. */
export interface DriverFace {
  talk: number;
  look_road: number;
  look_sora: number;
  nod: number;
  grip: number;
}

/** Weights (0–1) for the driver's live skeletal body & steering-wheel morphs. */
export interface DriverBodyPose {
  steer_left: number;
  steer_right: number;
  grip_tense: number;
  breathe: number;
  lean_peer: number;
}

/** Weights (0–1) for Sora's live skeletal hands, cuffs, nails & wristwatch morphs. */
export interface SoraBodyPose {
  breathe: number;
  tense_grip: number;
  fidget: number;
}

const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
const ease = (x: number) => {
  const c = clamp01(x);
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
  // Subtle uneasy mirror-check micro-nod as the back-seat rider first sits behind Sora!
  const mirrorCheck = window(
    t,
    TAXI_MIRROR.seated.from + 0.3,
    TAXI_MIRROR.seated.to - 0.3,
    0.4,
    0.5,
  );
  nod = Math.min(1, nod + mirrorCheck * 0.16);
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

/**
 * Live human driving behavior for the driver's arms, hands, shirt cuffs & torso:
 * his hands physically turn the bakelite steering wheel around bends & emergency swerves,
 * clench white-knuckled during haunts/braking, breathe faster with fear, and lean forward
 * peering into dense monsoon rain & jungle fog.
 */
export function taxiDriverBody(t: number, wheelAngle: number): DriverBodyPose {
  const anxiety = taxiAnxietyLevel(t);
  const flinch = taxiFlinch(t);
  const braking = ease((t - 62.0) / 3.0) * (1 - ease((t - 70.5) / 1.5));
  const steerNorm = Math.max(-1, Math.min(1, wheelAngle / 0.16));

  // Breathing rate speeds naturally from relaxed ~15 bpm to tense ~32 bpm after scares
  const breathPhase = t * (1.55 + anxiety * 1.35);
  const breathe = clamp01((0.5 + 0.5 * Math.sin(breathPhase)) * (0.42 + 0.52 * anxiety));

  // Peering forward through heavy rain/fog before Beat 1, Beat 2, Beat 4 & village braking
  const lean_peer = clamp01(
    Math.max(
      window(t, 18.2, 23.8, 1.2, 1.0) * 0.55,
      window(t, 33.2, 38.6, 1.4, 0.9) * 0.82,
      window(t, 56.2, 61.5, 1.0, 1.2) * 0.88,
      window(t, 63.5, 68.5, 1.0, 1.4) * 0.65,
      flinch * 0.72,
    ),
  );

  // White-knuckle steering-wheel clench during fear spikes, swerve & hard braking
  const grip_tense = clamp01(anxiety * 0.48 + flinch * 0.92 + braking * 0.42);

  return {
    steer_left: clamp01(steerNorm),
    steer_right: clamp01(-steerNorm),
    grip_tense,
    breathe,
    lean_peer,
  };
}

/**
 * Live human passenger behavior for Sora's hands, sleeves, nails & antique wristwatch:
 * - Natural subtle breathing accelerating gently when scared
 * - Unconscious wrist/finger fidget & subtle watch-check tilt during quiet stretches
 * - Sharp white-knuckle knee/trouser clench + lingering adrenaline hand tremor on every shock!
 */
export function taxiSoraBody(t: number): SoraBodyPose {
  const anxiety = taxiAnxietyLevel(t);
  const flinch = taxiFlinch(t);

  // Subtle calm chest/lap breathing that quickens visibly when terrified
  const breathe = clamp01(
    (0.5 + 0.5 * Math.sin(t * (1.42 + anxiety * 1.55) + 0.8)) * (0.38 + 0.58 * anxiety),
  );

  // Extra startle clench on Beat 1 verge snap (in addition to major flinch beats 2–5)
  const snapStartle =
    t >= TAXI_STANDER.snapAt && t < TAXI_STANDER.snapAt + 2.2
      ? Math.min(1, (t - TAXI_STANDER.snapAt) * 14) *
        Math.exp(-(t - TAXI_STANDER.snapAt) * 1.7) *
        0.78
      : 0;
  // Post-window-face lingering nervous grip that slowly releases during braking
  const windowAftershock = window(t, TAXI_WINDOW.beat, TAXI_WINDOW.beat + 3.4, 0.08, 2.2) * 0.68;
  // Microscopic adrenaline hand tremor right after big shocks
  const tremor = flinch > 0.14 ? Math.sin(t * 62) * 0.09 * flinch : 0;
  const tense_grip = clamp01(
    Math.max(anxiety * 0.42, snapStartle, flinch * 0.96, windowAftershock) + tremor,
  );

  // Gentle organic watch-glance tilt & fingertip rest shift during calm stretches only
  const calm = 1 - clamp01(anxiety * 1.3 + flinch * 2.0);
  const fidgetWave =
    window(t, 5.2, 9.6, 1.1, 1.3) * 0.72 +
    window(t, 13.8, 17.0, 0.9, 1.0) * 0.55 +
    window(t, 26.2, 30.8, 1.0, 1.2) * 0.65 +
    window(t, 41.8, 45.2, 0.9, 1.0) * 0.58;
  const fidget = clamp01(fidgetWave * calm);

  return { breathe, tense_grip, fidget };
}
