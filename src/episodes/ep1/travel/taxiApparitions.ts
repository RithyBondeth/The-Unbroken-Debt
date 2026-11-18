import { TAXI_GROUND_DROP, taxiDistance, taxiRoadHeading, taxiRoadPoint } from "./taxiMotion";
import { PREAY_CLIPS } from "../data/preayClips";

export type TaxiPassKind = "crossing" | "overtake";

export interface TaxiPass {
  kind: TaxiPassKind;
  /** Ride seconds when the form is first there. */
  start: number;
  seconds: number;
  /** Progress (0–1) at the scare's beat: closest in the road, or its hands on Sora's glass. */
  beat: number;
}

/**
 * Twice the Preay (a woman's ghost in a bloodied white dress) comes to the car. She never
 * runs; she is never seen to move faster than a person can, and mostly she is not seen
 * moving at all.
 * - `crossing`: as the lamps stutter she is already in the road ahead, walking across
 *   towards Sora's side at her own unhurried pace; the lightning at 37.8 s shows her nine
 *   metres off the bonnet, just after Sora asks who he is looking for. He brakes and
 *   swerves, the lamps blink, and when they come back the road is empty.
 * - `overtake`: a flickering stroke of lightning catches her standing in the trees on
 *   Sora's side four times, each time nearer, level with the car however fast it goes;
 *   the last flicker is her hands on Sora's window.
 */
export const TAXI_PASSES: readonly TaxiPass[] = [
  { kind: "crossing", start: 36.8, seconds: 1.35, beat: 1 / 1.35 },
  { kind: "overtake", start: 57.3, seconds: 0.75, beat: 0.63 / 0.75 },
];

/** The pass of `kind`. */
export function taxiPass(kind: TaxiPassKind): TaxiPass {
  return TAXI_PASSES.find((pass) => pass.kind === kind)!;
}

/** Ride seconds of a pass's beat. */
export function taxiPassBeat(pass: TaxiPass): number {
  return pass.start + pass.seconds * pass.beat;
}

/** The Preay's clips (tools/characters/build-preay.py, CMU motion capture). */
export type SpiritClip = "stand" | "walk" | "reach";

/** The performer's own ground speed in the walk, in metres a second at the figure's size. */
export const SPIRIT_WALK_SPEED = PREAY_CLIPS.walk.speed;

export interface SpiritPose {
  kind: "stander" | "crossing" | "overtake" | "window";
  /** Route-frame position (the frame the roadside is authored in) and facing. */
  x: number;
  z: number;
  /** Height of its feet: lowered when it stoops to the glass. */
  y: number;
  heading: number;
  clip: SpiritClip;
  /** Seconds into the clip. */
  clipTime: number;
  /** 0–1: how far its head turns to keep Sora in view. */
  look: number;
  /** False between the flickers that show it: it is there, but the dark hides it. */
  visible: boolean;
}

/**
 * Before either pass: something stands among the first trunks on Sora's side, at the
 * limit of the headlamps, half behind a tree. It does not move as the car comes up and
 * passes; it breathes, shifts its weight, and its head turns to keep the car in view.
 */
export const TAXI_STANDER = {
  /** Ride seconds the car draws level with it. */
  level: 23.4,
  lateral: 5.2,
  /** Seen from here (it is already standing there when the lamps reach it). */
  from: 17.4,
  /** Gone once it is this far behind Sora's window. */
  until: 24.5,
} as const;

/**
 * After the slap, when Sora is still looking at her window: the lamps fail, and the
 * next lightning shows it stooped at the glass, face to face, keeping pace with the car.
 */
export const TAXI_WINDOW = { start: 60.18, beat: 60.6, end: 61.02, lateral: 1.26 } as const;

/** The overtake's flickers: ride seconds, and where it stands (lateral, metres ahead of Sora). */
const GLIMPSES = [
  { at: 57.3, lateral: 7.2, ahead: 9.5, clipTime: 0.4 },
  { at: 57.52, lateral: 4.9, ahead: 4.6, clipTime: 1.9 },
  { at: 57.72, lateral: 3.2, ahead: 1.7, clipTime: 3.1 },
  { at: 57.93, lateral: 1.26, ahead: 0.15, clipTime: 1.25 },
] as const;
/** Half the width of one flicker of the stroke, in seconds. */
const FLICKER = 0.07;

/** Lightning, 0–1, from the ride clock: the storm's own strokes and the ones the scares need. */
export function taxiLightning(t: number): number {
  const pulse = (at: number, peak: number, sharp: number) => peak - Math.abs(t - at) * sharp;
  return Math.max(
    0,
    pulse(taxiPassBeat(taxiPass("crossing")), 1, 3),
    pulse(13.4, 0.7, 4),
    pulse(55.7, 0.9, 4),
    // One stroke that flickers four times as it finds the form in the trees.
    ...GLIMPSES.map((g, i) => {
      const peak = i === GLIMPSES.length - 1 ? 1 : 0.7;
      return pulse(g.at, peak, peak / FLICKER);
    }),
    // Two quick pulses: the first shows the face at the glass, the second an empty window.
    pulse(TAXI_WINDOW.beat, 1, 4.5),
    pulse(TAXI_WINDOW.beat + 0.62, 0.75, 6),
    // The lightning that shows the back seat in the mirror.
    pulse(TAXI_MIRROR.lean.beat, 0.85, 5),
  );
}

/** Where the Preay is at ride time `t`, and what it is doing; null when it is nowhere near. */
export function taxiSpiritAt(t: number): SpiritPose | null {
  if (t >= TAXI_STANDER.from && t <= TAXI_STANDER.until) {
    const along = taxiDistance(TAXI_STANDER.level),
      at = taxiRoadPoint(TAXI_STANDER.lateral, along);
    // Turned half towards the road the car comes along; the head does the rest.
    return {
      kind: "stander",
      x: at.x,
      z: at.z,
      y: -0.1 + TAXI_GROUND_DROP,
      heading: taxiRoadHeading(along) + Math.PI + 0.75,
      clip: "stand",
      clipTime: t - TAXI_STANDER.from,
      look: Math.min(1, (t - TAXI_STANDER.from) / 2.5),
      visible: true,
    };
  }
  const crossing = taxiPass("crossing");
  if (t >= crossing.start && t <= crossing.start + crossing.seconds) {
    const walked = t - crossing.start,
      along = taxiDistance(taxiPassBeat(crossing)) + 9,
      at = taxiRoadPoint(-0.95 + walked * SPIRIT_WALK_SPEED, along);
    return {
      kind: "crossing",
      x: at.x,
      z: at.z,
      y: -0.06 + TAXI_GROUND_DROP,
      heading: taxiRoadHeading(along) + Math.PI / 2,
      clip: "walk",
      clipTime: walked + 0.6,
      // Its head comes round to the lamps as they find it.
      look: Math.max(0, Math.min(0.85, (walked - 0.55) * 2)),
      visible: true,
    };
  }
  const overtake = taxiPass("overtake");
  if (t >= overtake.start - FLICKER && t <= overtake.start + overtake.seconds) {
    // It is somewhere between the flickers, unseen: there for the sound of it, not the eye.
    let i = GLIMPSES.findIndex((g) => g.at + FLICKER >= t);
    if (i < 0) i = GLIMPSES.length - 1;
    const g = GLIMPSES[i],
      along = taxiDistance(g.at) + g.ahead,
      at = taxiRoadPoint(g.lateral, along),
      last = i === GLIMPSES.length - 1;
    return {
      kind: "overtake",
      x: at.x,
      z: at.z,
      y: (last ? -0.12 : -0.08) + TAXI_GROUND_DROP,
      // Facing the car across the verge; at the glass, square on to it.
      heading: taxiRoadHeading(along) - Math.PI / 2 + (last ? 0 : 0.35),
      clip: last ? "reach" : "stand",
      clipTime: g.clipTime,
      look: 1,
      // Only while the flicker is bright enough to show it.
      visible: Math.abs(t - g.at) < FLICKER * 0.8,
    };
  }
  if (t >= TAXI_WINDOW.start && t <= TAXI_WINDOW.end) {
    const along = taxiDistance(t) - 0.2,
      at = taxiRoadPoint(TAXI_WINDOW.lateral, along);
    // Its face level with hers at the glass (the door hides the rest of it); it keeps
    // pace with the car without seeming to move, only breathing.
    return {
      kind: "window",
      x: at.x,
      z: at.z,
      // Cabin-relative. Her eyes are 1.47 m up: sunk a little, they are level with Sora's
      // in the Rosalie's low seat.
      y: -0.415,
      heading: taxiRoadHeading(along) - Math.PI / 2,
      clip: "stand",
      clipTime: 2.2 + (t - TAXI_WINDOW.start),
      look: 1,
      visible: true,
    };
  }
  return null;
}

/** The driver's reaction to the crossing: a yaw (radians) that jerks away and settles. */
export function taxiSwerve(t: number): number {
  const beat = taxiPassBeat(taxiPass("crossing")),
    s = t - beat - 0.12;
  if (s < 0 || s > 2.4) return 0;
  return -0.075 * Math.sin(s * 4.2) * Math.exp(-s * 1.7);
}

/** 0–1: how hard the driver flinches, peaking just after a crossing or the slap at the window. */
export function taxiFlinch(t: number): number {
  let amount = 0;
  for (const pass of TAXI_PASSES) {
    const s = t - taxiPassBeat(pass) - 0.08;
    if (s >= 0 && s < 3) amount = Math.max(amount, Math.min(1, s * 12) * Math.exp(-s * 1.6));
  }
  return amount;
}

const clamp01 = (v: number) => Math.max(0, Math.min(1, v));

/**
 * 0–1: what the car's electrics give the headlamps and the dash. They stutter
 * and die just before the crossing, so the lightning finds it already in the
 * road, blink once after it, and fail again before the face at the window.
 */
export function taxiElectrics(t: number): number {
  const stutter = (s: number) => (Math.sin(s * 61) * Math.sin(s * 23.7 + 1) > -0.15 ? 1 : 0.12);
  const cross = taxiPassBeat(taxiPass("crossing"));
  if (t > cross - 1.05 && t < cross - 0.03) return t < cross - 0.55 ? stutter(t) : 0;
  // As he brakes the lamps blink out once more; when they come back the road is empty.
  if (t > cross + 0.36 && t < cross + 0.62) return 0;
  // The dash and lamps sag as it leans out of the dark behind her.
  const lean = TAXI_MIRROR.lean.beat;
  if (t > lean - 0.3 && t < lean + 0.45) return t < lean ? stutter(t) : 0.35;
  const face = TAXI_WINDOW.beat;
  if (t > face - 0.85 && t < face + 1) {
    if (t < face - 0.45) return stutter(t);
    if (t < face + 0.5) return 0;
    return stutter(t) * clamp01((t - face - 0.5) / 0.5 + 0.4);
  }
  return 1;
}

/** How thick the haze lies, about 1: it thickens a little round each thing the road shows. */
export function taxiMistLevel(t: number): number {
  const hump = (centre: number, width: number) => Math.exp(-(((t - centre) / width) ** 2));
  return 1 + 0.12 * hump(21.5, 4) + 0.25 * hump(36.2, 4.5) + 0.2 * hump(59.5, 3.2);
}

/**
 * The back seat, seen only in the rear-view mirror. While the driver tells her
 * not to call to it, something sits behind Sora, still, its face just catching
 * the dash glow. Then, the moment she has said there is nobody behind them, the
 * lightning shows it leaning forward between the front seats, close to her ear.
 * Turning round finds the seat empty both times: it is only in the glass.
 */
export const TAXI_MIRROR = {
  seated: { from: 46.6, to: 48.9 },
  lean: { from: 52.05, beat: 52.3, to: 52.75 },
} as const;

export interface MirrorRiderPose {
  kind: "seated" | "lean";
  /** Cabin-frame position (the cabin does not move with the route) and posture. */
  x: number;
  y: number;
  z: number;
  lean: number;
  /** 0–1 dither coverage. */
  presence: number;
  /** -1 to 1: its head turned towards Sora. */
  attention: number;
}

/** The figure the mirror shows at ride time `t`, or null. */
export function taxiMirrorRiderAt(t: number): MirrorRiderPose | null {
  const { seated, lean } = TAXI_MIRROR;
  if (t >= seated.from && t <= seated.to) {
    const presence = clamp01(Math.min((t - seated.from) / 0.9, (seated.to - t) / 0.35));
    // Behind Sora on the rear bench, sitting far too tall: its head is bowed under the
    // roof, the rest of it down in the seat and the dark of the footwell.
    return { kind: "seated", x: 0.27, y: -0.92, z: -1.22, lean: 0.06, presence, attention: 0.15 };
  }
  if (t >= lean.from && t <= lean.to) {
    const p = clamp01((t - lean.from) / (lean.beat - lean.from));
    // Up between the front seat backs, bent towards her, its face just behind her shoulder.
    return {
      kind: "lean",
      x: 0.27 - 0.17 * p,
      y: -0.92 - 0.04 * p,
      z: -1.22 + 0.55 * p,
      lean: 0.06 + 0.2 * p,
      presence: 1,
      attention: 0.6,
    };
  }
  return null;
}
