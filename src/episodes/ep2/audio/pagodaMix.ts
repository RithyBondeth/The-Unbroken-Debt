import type { PagodaSpace } from "@/audio/acoustics";

/**
 * The rules of Episode 2's mix, kept apart from the sounds so they can be tested:
 * how often things happen, how far off, how loud for how near a threat is, and
 * which room the listener is in. The aim is a night that sounds recorded, not
 * scripted: every repeat a different take, a little off pitch, at an uneven gap.
 */

type Range = readonly [number, number];

/** Seconds between events (uniform in the range). */
export const GAPS = {
  /** A whisper somewhere behind: rare enough to stay unsettling. */
  whisper: [60, 150],
  /** Knocks in the walls of the kuti or the hall. */
  knock: [150, 300],
  /** Old timber giving way behind Sora in the escape. */
  escapeSnap: [5, 11],
  /** The far temple drum and gong, a sob in the trees. */
  far: [70, 150],
  /** A dog in the village, an owl, a gecko on the eaves. */
  call: [14, 34],
  /** A tree or the bamboo answering the wind (shorter as the wind rises). */
  creak: [12, 30],
  /** How long one insect take plays before the night drifts to another. */
  bedSwap: [70, 150],
  /** The chant stopping dead, every voice at once (and the insects with it). */
  chantSilence: [120, 260],
  /** How long that silence holds before the chant creeps back. */
  silenceLength: [6, 12],
  /** The chant answered from the trees where no monks are. */
  chantAnswer: [70, 160],
  /** How long the answer is heard each time. */
  answerLength: [18, 40],
  /** Bare steps behind a player who stands still too long. */
  steps: [45, 120],
} as const satisfies Record<string, Range>;

/** Metres from the listener. */
export const DISTANCES = {
  whisper: [4, 8],
  far: [30, 60],
  dog: [45, 70],
  owl: [14, 30],
  creak: [9, 24],
  knock: [3, 5],
  steps: [3.5, 6],
} as const satisfies Record<string, Range>;

/** A value uniformly within `range`. */
export function between(range: Range, rand: () => number): number {
  return range[0] + rand() * (range[1] - range[0]);
}

/** A playback rate within ±`amount` of 1 (±5% by default: a different voice each time). */
export function pitchJitter(rand: () => number, amount = 0.05): number {
  return 1 + (rand() * 2 - 1) * amount;
}

/** Eases `current` toward `target` with time constant `tau` seconds (frame-rate independent). */
export function approach(current: number, target: number, dt: number, tau: number): number {
  if (tau <= 0) return target;
  return current + (target - current) * (1 - Math.exp(-Math.max(0, dt) / tau));
}

/** The scripture library over the pond, runtime coordinates (X east, Z south). */
export function inLibrary(x: number, z: number): boolean {
  return Math.abs(x) < 4.6 && z < -27.9 && z > -36.1;
}

/** The room the listener is in, for its reverb and the walls' muffling of the night. */
export function pagodaSpace(
  x: number,
  z: number,
  where: { safe: boolean; inHall: boolean },
): PagodaSpace {
  if (where.safe) return "kuti";
  if (where.inHall) return "hall";
  if (inLibrary(x, z)) return "library";
  return "jungle";
}

/** 0 when the nearest threat is `far` metres or more away, rising smoothly to 1 at `near`. */
export function closeness(distance: number, near: number, far: number): number {
  const u = Math.max(0, Math.min(1, (far - distance) / (far - near)));
  return u * u * (3 - 2 * u);
}

/**
 * How much the night life (insects, frogs, calls) falls away as a Pret draws
 * near: nothing beyond 14 m, most of it within 4 m. Silence is the warning.
 */
export function nightDuck(nearestPret: number, threatActive: boolean): number {
  return Math.max(threatActive ? 0.35 : 0, 0.8 * closeness(nearestPret, 4, 14));
}

/** The heartbeat's level and rate: only with a Pret within about 8 m, quickening as it nears. */
export function heartbeat(nearestPret: number): { level: number; rate: number } {
  const c = closeness(nearestPret, 2, 8);
  return { level: 0.24 * c, rate: 0.92 + 0.26 * c };
}

/** Wind bed levels for its strength at the listener (`amount`; the pagoda's calm is about 0.3). */
export function windLevels(amount: number): { canopy: number; leaves: number } {
  const a = Math.max(0, Math.min(2, amount));
  return { canopy: 0.07 + 0.32 * a ** 1.2, leaves: 0.05 + 0.22 * a ** 1.4 };
}

/** A point `distance` metres from (x, z) at `angle` radians from straight behind a `yaw` heading. */
export function behind(
  x: number,
  z: number,
  yaw: number,
  distance: number,
  angle: number,
): { x: number; z: number } {
  const a = yaw + Math.PI + angle;
  return { x: x + Math.sin(a) * distance, z: z + Math.cos(a) * distance };
}

/** A point `distance` metres from (x, z) in a random direction. */
export function around(
  x: number,
  z: number,
  distance: number,
  rand: () => number,
): { x: number; z: number } {
  const a = rand() * Math.PI * 2;
  return { x: x + Math.cos(a) * distance, z: z + Math.sin(a) * distance };
}

/**
 * Per-Pret breathing that never falls into step: each breathes at its own rate
 * (±8%) and starts at its own point in the loop.
 */
export function breathVoices(
  count: number,
  loopSeconds: number,
  rand: () => number,
): { rate: number; offset: number }[] {
  return Array.from({ length: count }, (_, i) => ({
    rate: 0.92 + ((i + rand() * 0.8) / Math.max(1, count)) * 0.16,
    offset: rand() * loopSeconds,
  }));
}

/**
 * A take other than `last` (so no take is heard twice running).
 */
export function pickTake(count: number, last: number, rand: () => number): number {
  if (count < 2) return 0;
  const k = Math.floor(rand() * (count - 1));
  return k >= last ? k + 1 : k;
}
