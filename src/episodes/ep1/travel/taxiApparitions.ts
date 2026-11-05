import { taxiDistance, taxiRoadHeading, taxiRoadPoint } from "./taxiMotion";

/** Metres along the route of the set pieces build-taxi.py places (RITUAL_Z, WATCHER_Z). */
export const TAXI_RITUAL_ALONG = 212;
export const TAXI_RITUAL_LATERAL = 5.4;

export type TaxiPassKind = "crossing" | "overtake";

export interface TaxiPass {
  kind: TaxiPassKind;
  /** Ride seconds when the form appears. */
  start: number;
  seconds: number;
  /** Progress (0–1) at the scare's beat: mid-road, or level with Sora's window. */
  beat: number;
}

/**
 * Twice a black shadow runs past the taxi, faster than a person can:
 * - `crossing`: across the road through the headlights in the lightning at 37.8 s,
 *   just after Sora asks who he is looking for. He brakes and swerves.
 * - `overtake`: up Sora's side from behind, level with her window, then off into
 *   the trees ahead, lit by lightning.
 */
export const TAXI_PASSES: readonly TaxiPass[] = [
  { kind: "crossing", start: 37.49, seconds: 0.62, beat: 0.5 },
  { kind: "overtake", start: 57.3, seconds: 1.5, beat: 0.42 },
];

/** The pass of `kind`. */
export function taxiPass(kind: TaxiPassKind): TaxiPass {
  return TAXI_PASSES.find((pass) => pass.kind === kind)!;
}

/** Ride seconds of a pass's beat. */
export function taxiPassBeat(pass: TaxiPass): number {
  return pass.start + pass.seconds * pass.beat;
}

export interface RunnerPose {
  kind: TaxiPassKind;
  progress: number;
  /** Route-frame position (the frame the roadside is authored in) and facing. */
  x: number;
  z: number;
  heading: number;
}

const smooth = (p: number) => p * p * (3 - 2 * p);

/** Where the running form is `lag` seconds behind its lead at ride time `t`; null when none runs. */
export function taxiRunnerAt(t: number, lag = 0): RunnerPose | null {
  for (const pass of TAXI_PASSES) {
    const p = (t - lag - pass.start) / pass.seconds;
    if (p < 0 || p > 1) continue;
    let lateral: number, along: number, facing: number;
    if (pass.kind === "crossing") {
      // Left verge to right verge, eight metres ahead, in a little over half a second.
      along = taxiDistance(pass.start) + 8 + p * 1.5;
      lateral = -5.2 + smooth(p) * 10.4;
      facing = Math.PI / 2;
    } else {
      // From behind Sora's door to well ahead, then veering off into the trees.
      along = taxiDistance(t - lag) - 6 + p * 17;
      const veer = Math.max(0, (p - 0.7) / 0.3);
      lateral = 2.35 + veer * veer * 4.5;
      facing = veer * 0.9;
    }
    const at = taxiRoadPoint(lateral, along);
    return {
      kind: pass.kind,
      progress: p,
      x: at.x,
      z: at.z,
      heading: taxiRoadHeading(along) + facing,
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
