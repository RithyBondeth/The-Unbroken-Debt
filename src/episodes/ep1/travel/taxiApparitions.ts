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
 * Five escalating, fast and unpredictable haunts across the 72 s storm drive:
 * - Beat 1 (`stander` + snap): motionless among the first trees, snapping 2 m closer on a lightning blink.
 * - Beat 2 (`crossing`): electrics die into silence, then lightning & headlamps catch her SPRINTING at
 *   blistering speed across the flooded ruts 8 m ahead of the bonnet as the driver wrenches the wheel.
 * - Beat 3 (`mirror` seated → snap-lunge): looms behind Sora in the rear-view mirror, then snaps
 *   forward right behind her ear in 0.18 s the moment she says nobody is there.
 * - Beat 4 (`overtake` + `window`): four rapid strobes in 0.58 s catch her hurtling out of the dark
 *   jungle straight onto Sora's side glass, followed after a pitch-black lull by her face pressed
 *   dead-on against the rain-streaked pane.
 * - Beat 5 (`bonnet`): just as the car brakes for the village and tension drops, a split-second
 *   lightning silhouette flashes her inches off the bonnet right through the windscreen wipers.
 */
export const TAXI_PASSES: readonly TaxiPass[] = [
  { kind: "crossing", start: 37.05, seconds: 0.98, beat: 0.73 / 0.98 },
  { kind: "overtake", start: 57.3, seconds: 0.66, beat: 0.58 / 0.66 },
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
export type SpiritClip = "stand" | "walk" | "hurry" | "reach";

/** Ground speed during walk and blistering sprint (m/s). */
export const SPIRIT_WALK_SPEED = PREAY_CLIPS.walk.speed;
export const SPIRIT_SPRINT_SPEED = Math.max(5.4, PREAY_CLIPS.hurry.speed * 2.1);

export interface SpiritPose {
  kind: "stander" | "crossing" | "overtake" | "window" | "bonnet";
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
 * Beat 1: standing among the first trunks on Sora's right verge, turning its head to follow
 * the car — then snapping 2.1 m closer in a split-second lightning blink right as the cab passes!
 */
export const TAXI_STANDER = {
  /** Ride seconds the car draws level with it. */
  level: 23.4,
  lateral: 5.2,
  /** Lightning blink where she snaps 2.4 m closer right inside the right headlight beam ahead of the windscreen! */
  snapAt: 22.55,
  /** Seen from here (already standing there when the headlight cones find her). */
  from: 17.4,
  /** Gone once past Sora's window. */
  until: 24.0,
} as const;

/**
 * Beat 4b: after the side-window slap, electrics die into pitch darkness — then the next
 * lightning stroke reveals her face & reaching hands pressed dead-on outside Sora's glass.
 */
export const TAXI_WINDOW = { start: 60.16, beat: 60.56, end: 60.96, lateral: 1.18 } as const;

/**
 * Beat 5: unexpected final split-second bonnet silhouette during braking when the player thinks
 * the ride is safely over — gone on the very next wiper sweep!
 */
export const TAXI_BONNET = {
  start: 65.45,
  beat: 65.56,
  end: 65.72,
  ahead: 3.5,
  lateral: 0.28,
} as const;

/** Beat 4a: blistering 0.58 s four-flicker strobe chase hurtling out of the dark jungle onto Sora's glass! */
const GLIMPSES = [
  { at: 57.3, lateral: 7.4, ahead: 8.6, clipTime: 0.25 },
  { at: 57.49, lateral: 4.7, ahead: 4.1, clipTime: 0.85 },
  { at: 57.68, lateral: 2.5, ahead: 1.4, clipTime: 1.45 },
  { at: 57.88, lateral: 1.18, ahead: 0.12, clipTime: 1.25 },
] as const;

/** Half the width of one lightning flicker strobe, in seconds (tighter & faster!). */
const FLICKER = 0.062;

/** Lightning, 0–1, from the ride clock: dramatic storm strokes & rapid haunt strobes. */
export function taxiLightning(t: number): number {
  const pulse = (at: number, peak: number, sharp: number) => peak - Math.abs(t - at) * sharp;
  return Math.max(
    0,
    // Early distant monsoon storm flashes across the flooded paddies
    pulse(9.2, 0.55, 5),
    pulse(13.4, 0.78, 4.2),
    // Beat 1: sharp split-second blink right as the verge watcher snaps closer
    pulse(TAXI_STANDER.snapAt, 0.92, 9),
    // Beat 2: blinding strike illuminating the high-speed road sprint
    pulse(taxiPassBeat(taxiPass("crossing")), 1, 3.6),
    // Storm precursor before the jungle ambush
    pulse(55.6, 0.9, 4.4),
    // Beat 4a: rapid four-flicker strobe chase out of the jungle
    ...GLIMPSES.map((g, i) => {
      const peak = i === GLIMPSES.length - 1 ? 1 : 0.76;
      return pulse(g.at, peak, peak / FLICKER);
    }),
    // Beat 4b: blinding eye-level glass press, then a second flicker showing an empty window
    pulse(TAXI_WINDOW.beat, 1, 5.0),
    pulse(TAXI_WINDOW.beat + 0.52, 0.82, 7.2),
    // Beat 3: cold flash catching the mirror snap-lunge right behind Sora
    pulse(TAXI_MIRROR.lean.beat, 0.95, 6.2),
    // Beat 5: unexpected brutal braking flash directly in front of the bonnet
    pulse(TAXI_BONNET.beat, 1, 7.5),
  );
}

/** Where the Preay is at ride time `t`, and what she is doing; null when nowhere near. */
export function taxiSpiritAt(t: number): SpiritPose | null {
  // Beat 1: Verge watcher who snaps 2.45 m closer into the right headlight beam during the 22.55 s lightning blink!
  if (t >= TAXI_STANDER.from && t <= TAXI_STANDER.until) {
    const snapped = t >= TAXI_STANDER.snapAt - 0.05;
    const along = taxiDistance(TAXI_STANDER.level);
    const lat = snapped ? 2.75 : TAXI_STANDER.lateral;
    const at = taxiRoadPoint(lat, along);
    return {
      kind: "stander",
      x: at.x,
      z: at.z,
      y: -0.1 + TAXI_GROUND_DROP,
      heading: taxiRoadHeading(along) + Math.PI + (snapped ? 0.55 : 0.75),
      clip: snapped ? "reach" : "stand",
      clipTime: snapped ? 0.35 + (t - TAXI_STANDER.snapAt) * 1.4 : t - TAXI_STANDER.from,
      look: snapped ? 1 : Math.min(1, (t - TAXI_STANDER.from) / 2.2),
      visible: snapped ? Math.abs(t - TAXI_STANDER.snapAt) < 0.16 : true,
    };
  }

  // Beat 2: Blistering fast high-speed sprint straight across the twin headlight fog cones!
  const crossing = taxiPass("crossing");
  if (t >= crossing.start && t <= crossing.start + crossing.seconds) {
    const sprinted = t - crossing.start;
    const along = taxiDistance(taxiPassBeat(crossing)) + 8.0;
    const at = taxiRoadPoint(-2.35 + sprinted * SPIRIT_SPRINT_SPEED, along);
    return {
      kind: "crossing",
      x: at.x,
      z: at.z,
      y: -0.06 + TAXI_GROUND_DROP,
      heading: taxiRoadHeading(along) + Math.PI / 2,
      clip: "hurry",
      clipTime: sprinted * 2.2 + 0.15,
      look: Math.max(0, Math.min(1, sprinted * 2.4)),
      visible: true,
    };
  }

  // Beat 4a: Supersonic 4-strobe chase hurtling from the trees straight onto Sora's window glass!
  const overtake = taxiPass("overtake");
  if (t >= overtake.start - FLICKER && t <= overtake.start + overtake.seconds) {
    let i = GLIMPSES.findIndex((g) => g.at + FLICKER >= t);
    if (i < 0) i = GLIMPSES.length - 1;
    const g = GLIMPSES[i];
    const along = taxiDistance(g.at) + g.ahead;
    const at = taxiRoadPoint(g.lateral, along);
    const last = i === GLIMPSES.length - 1;
    return {
      kind: "overtake",
      x: at.x,
      z: at.z,
      y: (last ? -0.14 : -0.08) + TAXI_GROUND_DROP,
      heading: taxiRoadHeading(along) - Math.PI / 2 + (last ? 0 : 0.25),
      clip: last ? "reach" : "hurry",
      clipTime: g.clipTime,
      look: 1,
      visible: Math.abs(t - g.at) < FLICKER * 0.85,
    };
  }

  // Beat 4b: Pressed dead-on outside Sora's rain-streaked glass at eye level!
  if (t >= TAXI_WINDOW.start && t <= TAXI_WINDOW.end) {
    const along = taxiDistance(t) - 0.04;
    const at = taxiRoadPoint(TAXI_WINDOW.lateral, along);
    return {
      kind: "window",
      x: at.x,
      z: at.z,
      y: -0.37,
      heading: taxiRoadHeading(along) - Math.PI / 2,
      clip: "reach",
      clipTime: 0.24 + (t - TAXI_WINDOW.start) * 0.45,
      look: 1,
      visible: true,
    };
  }

  // Beat 5: Unexpected split-second silhouette directly off the wet bonnet during braking!
  if (t >= TAXI_BONNET.start && t <= TAXI_BONNET.end) {
    const along = taxiDistance(TAXI_BONNET.beat) + TAXI_BONNET.ahead;
    const at = taxiRoadPoint(TAXI_BONNET.lateral, along);
    return {
      kind: "bonnet",
      x: at.x,
      z: at.z,
      y: -0.08 + TAXI_GROUND_DROP,
      heading: taxiRoadHeading(along) + Math.PI,
      clip: "reach",
      clipTime: 1.15 + (t - TAXI_BONNET.start) * 1.5,
      look: 1,
      visible: Math.abs(t - TAXI_BONNET.beat) < 0.11,
    };
  }

  return null;
}

/** The driver's violent emergency swerve on the crossing (plus a sharp jolt on the final bonnet flash). */
export function taxiSwerve(t: number): number {
  const beat = taxiPassBeat(taxiPass("crossing"));
  const s = t - beat - 0.08;
  let yaw = 0;
  if (s >= 0 && s <= 2.3) yaw += -0.115 * Math.sin(s * 4.8) * Math.exp(-s * 1.75);
  const sb = t - TAXI_BONNET.beat - 0.04;
  if (sb >= 0 && sb <= 1.2) yaw += 0.042 * Math.sin(sb * 6.2) * Math.exp(-sb * 3.1);
  return yaw;
}

/** 0–1: visceral shock flinch peaking sharply on every major haunt impact (drives camera jolt & driver flinch). */
export function taxiFlinch(t: number): number {
  let amount = 0;
  const beats = [
    taxiPassBeat(taxiPass("crossing")),
    TAXI_MIRROR.lean.beat,
    taxiPassBeat(taxiPass("overtake")),
    TAXI_WINDOW.beat,
    TAXI_BONNET.beat,
  ];
  for (const beat of beats) {
    const s = t - beat - 0.04;
    if (s >= 0 && s < 2.6) amount = Math.max(amount, Math.min(1, s * 18) * Math.exp(-s * 2.0));
  }
  return amount;
}

const clamp01 = (v: number) => Math.max(0, Math.min(1, v));

/**
 * 0–1: vacuum-silence ducking BEFORE major haunt impacts!
 * Sucks rain, engine & wind down into an eerie suffocating dead-air vacuum 0.6–1.3 s before
 * Beats 2, 3, 4b, and 5 so the sudden spatial impact detonates with maximum anxiety & shock.
 */
export function taxiVacuumDuck(t: number): number {
  const window = (start: number, peak: number, drop: number) => {
    if (t < start || t > drop) return 0;
    if (t < peak) return clamp01((t - start) / Math.max(0.05, peak - start));
    return clamp01(1 - (t - peak) / Math.max(0.02, drop - peak));
  };
  const cross = taxiPassBeat(taxiPass("crossing"));
  return Math.max(
    window(cross - 1.25, cross - 0.14, cross - 0.01) * 0.78,
    window(TAXI_MIRROR.lean.beat - 0.95, TAXI_MIRROR.lean.beat - 0.08, TAXI_MIRROR.lean.beat) *
      0.82,
    window(TAXI_WINDOW.beat - 1.15, TAXI_WINDOW.beat - 0.1, TAXI_WINDOW.beat - 0.01) * 0.86,
    window(TAXI_BONNET.beat - 0.72, TAXI_BONNET.beat - 0.08, TAXI_BONNET.beat) * 0.72,
  );
}

/**
 * 0–1: what the car's electrics give the twin headlamps, dash & radio.
 * They sputter and plunge into pitch darkness right before key scares so only lightning reveals her!
 */
export function taxiElectrics(t: number): number {
  const stutter = (s: number) => (Math.sin(s * 67) * Math.sin(s * 27.3 + 1) > -0.15 ? 1 : 0.08);
  const cross = taxiPassBeat(taxiPass("crossing"));
  if (t > cross - 1.05 && t < cross - 0.03) return t < cross - 0.52 ? stutter(t) : 0;
  // Brief blackout right after swerve; when lamps come back the road is dead empty.
  if (t > cross + 0.34 && t < cross + 0.6) return 0;
  // Dash and lamps sag as she snaps forward behind Sora in the mirror.
  const lean = TAXI_MIRROR.lean.beat;
  if (t > lean - 0.32 && t < lean + 0.44) return t < lean ? stutter(t) : 0.28;
  // Total blackout before the eye-level glass press.
  const face = TAXI_WINDOW.beat;
  if (t > face - 0.88 && t < face + 0.95) {
    if (t < face - 0.45) return stutter(t);
    if (t < face + 0.48) return 0;
    return stutter(t) * clamp01((t - face - 0.48) / 0.45 + 0.4);
  }
  // Final sudden stutter during braking for the unexpected bonnet silhouette!
  if (t > TAXI_BONNET.start - 0.14 && t < TAXI_BONNET.end + 0.18) {
    return t < TAXI_BONNET.beat ? 0 : stutter(t);
  }
  return 1;
}

/** How thick the storm mist lies: swells eerily around every haunt without turning into a white wall. */
export function taxiMistLevel(t: number): number {
  const hump = (centre: number, width: number) => Math.exp(-(((t - centre) / width) ** 2));
  return (
    1 +
    0.14 * hump(21.5, 4) +
    0.26 * hump(36.5, 4.2) +
    0.22 * hump(59.4, 3.2) +
    0.16 * hump(65.4, 2.2)
  );
}

/**
 * Beat 3: The back seat, seen only in the rear-view mirror. Sits motionless behind Sora
 * while the driver warns her — then snaps forward in 0.18 s right behind her shoulder!
 */
export const TAXI_MIRROR = {
  seated: { from: 46.6, to: 49.1 },
  lean: { from: 52.04, beat: 52.22, to: 53.05 },
} as const;

export interface MirrorRiderPose {
  kind: "seated" | "lean";
  /** Cabin-frame position (the cabin does not move with the route) and posture. */
  x: number;
  y: number;
  z: number;
  lean: number;
  /** 0–1 visibility coverage. */
  presence: number;
  /** -1 to 1: head turned towards Sora. */
  attention: number;
  /** True when she manifests physically inside the cabin (not just in the mirror glass). */
  inCabin: boolean;
}

/** The figure haunting the back seat & rear-view mirror at ride time `t`, or null. */
export function taxiMirrorRiderAt(t: number): MirrorRiderPose | null {
  const { seated, lean } = TAXI_MIRROR;
  if (t >= seated.from && t <= seated.to) {
    const presence = clamp01(Math.min((t - seated.from) / 0.6, (seated.to - t) / 0.35));
    return {
      kind: "seated",
      x: 0.14,
      y: -0.49,
      z: -1.14,
      lean: 0.03,
      presence,
      attention: 0.65,
      inCabin: false,
    };
  }
  if (t >= lean.from && t <= lean.to) {
    // Explosive snap-lunge ease-out curve (fills the entire mirror & leans between the front seats in 0.18 s!)
    const raw = clamp01((t - lean.from) / (lean.beat - lean.from));
    const p = 1 - (1 - raw) ** 3;
    const fadeOut = clamp01((lean.to - t) / 0.18);
    return {
      kind: "lean",
      x: 0.14 - 0.06 * p,
      y: -0.49 + 0.1 * p,
      z: -1.14 + 0.54 * p,
      lean: 0.03 + 0.04 * p,
      presence: fadeOut,
      attention: 1,
      inCabin: true,
    };
  }
  return null;
}
