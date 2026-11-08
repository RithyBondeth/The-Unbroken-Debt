import type { Point } from "./pagoda";
/** Distances are metres, durations are active gameplay seconds. Episode 1 player speeds stay intact. */
export const PAGODA_BALANCE = {
  simulationStep: 1 / 30,
  patrolSpeed: 0.62,
  investigateSpeed: 1.22,
  /** A loud sound close by: the corpse snaps round and comes at a stumbling run. */
  rushSpeed: 2.5,
  rushRange: 10,
  rushLoudness: 1,
  rushSeconds: 3.5,
  rushFreeze: 0.3,
  /** Following Sora unseen: quick while her back is turned, never nearer than `stalkGap`. */
  stalkSpeed: 1.05,
  stalkGap: 5,
  stalkSeconds: 28,
  /** The dead that crawl go slower on patrol and scuttle when they hear something. */
  crawlSpeed: 0.42,
  crawlInvestigateSpeed: 0.95,
  crawlRushSpeed: 1.7,
  listeningSeconds: 0.75,
  searchSeconds: 9,
  catchRadius: 0.72,
  hearingFloor: 1.1,
  hearingScale: 12,
  hearingCap: 20,
  stupaTransmission: 0.62,
  minimumTransmission: 0.32,
  breathingLoudness: 0.09,
  breathingInterval: 1.6,
  breathSeconds: 6,
  breathRecovery: 0.75,
  breathRearm: 2,
  loadGrace: 4,
  readingGrace: 1.4,
  escapeSeconds: 90,
  escapeWarnings: [60, 30, 12] as readonly number[],
  bowlRange: 7,
  bowlLoudness: 1.3,
};
/** This is the actual kuti interior, behind its wall and threshold. */
export function inKuti(p: Point): boolean {
  return p.x > -21.35 && p.x < -14.65 && p.z > 8.65 && p.z < 15.35;
}
/** Expand building/table footprints by a Pret's shoulders, as with the stupas. */
export function blockedGardenProp(p: Point): boolean {
  return (p.x < -14.15 && p.z > 8.15) || (p.x > 15.15 && p.z > 7.25 && p.z < 8.75);
}
export function hearingRadius(loudness: number): number {
  return loudness <= 0
    ? 0
    : Math.min(
        PAGODA_BALANCE.hearingCap,
        PAGODA_BALANCE.hearingFloor + loudness * PAGODA_BALANCE.hearingScale,
      );
}
/** Whether a straight sound path crosses a monument's footprint. Slab intersection has no corner gaps. */
export function crossesStupa(a: Point, b: Point, center: Point): boolean {
  let lo = 0,
    hi = 1;
  for (const axis of ["x", "z"] as const) {
    const delta = b[axis] - a[axis],
      min = center[axis] - 0.72,
      max = center[axis] + 0.72;
    if (Math.abs(delta) < 1e-8) {
      if (a[axis] < min || a[axis] > max) return false;
      continue;
    }
    const p = (min - a[axis]) / delta,
      q = (max - a[axis]) / delta;
    lo = Math.max(lo, Math.min(p, q));
    hi = Math.min(hi, Math.max(p, q));
    if (lo > hi) return false;
  }
  return hi >= 0 && lo <= 1;
}
/** A paused window/menu never consumes the escape allowance. Warning crossings fire once. */
export class EscapeClock {
  remaining: number = PAGODA_BALANCE.escapeSeconds;
  private warned = new Set<number>();
  reset(): void {
    this.remaining = PAGODA_BALANCE.escapeSeconds;
    this.warned.clear();
  }
  update(dt: number, active: boolean): number[] {
    if (!active) return [];
    const before = this.remaining;
    this.remaining = Math.max(0, this.remaining + -Math.max(0, dt));
    return PAGODA_BALANCE.escapeWarnings.filter((t) => {
      if (before > t && this.remaining <= t && !this.warned.has(t)) {
        this.warned.add(t);
        return true;
      }
      return false;
    });
  }
  get expired(): boolean {
    return this.remaining === 0;
  }
}

/** Match the Havok controller’s stability cap so low frame rates never speed up threats. */
export function simulationStep(dt: number): number {
  return Math.max(0, Math.min(PAGODA_BALANCE.simulationStep, dt));
}
