import { GARDEN_OBSTACLES, type Point } from "./data/pagoda";
import {
  PAGODA_BALANCE as B,
  inKuti,
  blockedGardenProp,
  hearingRadius,
  crossesStupa,
} from "./data/balance";
export type PretMode = "patrol" | "listen" | "investigate" | "rush";
const distance = (a: Point, b: Point) => Math.hypot(a.x - b.x, a.z - b.z);
/** Obstacles inflated by the ghost's shoulder radius. */
export function gardenClear(p: Point): boolean {
  return (
    p.x >= -16 &&
    p.x <= 16 &&
    p.z >= -16 &&
    p.z <= 14 &&
    !blockedGardenProp(p) &&
    !GARDEN_OBSTACLES.some((s) => Math.abs(p.x - s.x) < 1.05 && Math.abs(p.z - s.z) < 1.05)
  );
}
/** Four-neighbour A*: never cuts through a stupa, even when a sound is behind it. */
export function gardenPath(from: Point, to: Point): Point[] {
  const snap = (p: Point): Point => ({ x: Math.round(p.x), z: Math.round(p.z) });
  const nearest = (p: Point): Point => {
    const q = snap(p);
    if (gardenClear(q)) return q;
    for (let r = 1; r < 5; r++)
      for (let x = -r; x <= r; x++)
        for (let z = -r; z <= r; z++) {
          const n = { x: q.x + x, z: q.z + z };
          if (gardenClear(n)) return n;
        }
    return { x: -15, z: 13 };
  };
  const start = nearest(from),
    goal = nearest(to),
    key = (p: Point) => `${p.x},${p.z}`;
  const open = [start],
    came = new Map<string, Point>(),
    cost = new Map([[key(start), 0]]);
  while (open.length) {
    open.sort(
      (a, b) => cost.get(key(a))! + distance(a, goal) - (cost.get(key(b))! + distance(b, goal)),
    );
    const p = open.shift()!;
    if (key(p) === key(goal)) {
      const path = [goal];
      let n = p;
      while (came.has(key(n))) {
        n = came.get(key(n))!;
        path.unshift(n);
      }
      return path.slice(1);
    }
    for (const [dx, dz] of [
      [1, 0],
      [-1, 0],
      [0, 1],
      [0, -1],
    ]) {
      const n = { x: p.x + dx, z: p.z + dz },
        k = key(n),
        g = cost.get(key(p))! + 1;
      if (!gardenClear(n) || g >= (cost.get(k) ?? Infinity)) continue;
      came.set(k, p);
      cost.set(k, g);
      if (!open.some((v) => key(v) === k)) open.push(n);
    }
  }
  return [];
}

/** A way from one point to another for a corpse; the garden grid unless the map's is set. */
export type Pathfinder = (from: Point, to: Point) => Point[];

/** Blind hungry ghosts react to hearing only; a lamp never gives Sora away. */
export class PretBrain {
  readonly position: Point;
  mode: PretMode = "patrol";
  yaw = 0;
  /** How it finds its way: the whole map's navigation once the area has loaded. */
  pathfinder: Pathfinder = gardenPath;
  private routeIndex = 0;
  private path: Point[] = [];
  private listenFor = 0;
  private interest = 0;
  private rushFor = 0;
  constructor(
    readonly route: readonly Point[],
    start = 0,
  ) {
    this.routeIndex = start % route.length;
    this.position = { ...route[this.routeIndex] };
  }
  hear(at: Point, loudness: number): boolean {
    if (loudness <= 0 || inKuti(at)) return false;
    const barriers = GARDEN_OBSTACLES.filter((s) => crossesStupa(this.position, at, s)).length;
    const transmission = Math.max(B.minimumTransmission, B.stupaTransmission ** barriers);
    const d = distance(at, this.position);
    if (d > hearingRadius(loudness) * transmission) return false;
    this.path = this.pathfinder(this.position, at);
    // A loud sound close by (a run, a gasp, a thrown bowl): a jerk round, then it comes fast.
    if (
      loudness >= B.rushLoudness &&
      d < B.rushRange &&
      this.mode !== "rush" &&
      this.rushFor <= 0
    ) {
      this.mode = "listen";
      this.listenFor = B.rushFreeze;
      this.rushFor = B.rushSeconds;
    } else if (this.mode === "patrol") {
      // Repeated footsteps renew the target without freezing an investigating ghost.
      this.mode = "listen";
      this.listenFor = B.listeningSeconds;
    }
    this.interest = B.searchSeconds;
    return true;
  }
  update(dt: number): void {
    if (this.listenFor > 0) {
      this.listenFor -= dt;
      if (this.listenFor <= 0) this.mode = this.rushFor > 0 ? "rush" : "investigate";
      return;
    }
    if (this.mode === "rush") {
      this.rushFor -= dt;
      if (this.rushFor <= 0) {
        this.rushFor = 0;
        this.mode = "investigate";
      }
    }
    if (this.mode === "investigate") {
      this.interest -= dt;
      if (this.interest <= 0) {
        this.mode = "patrol";
        this.path = [];
      }
    }
    if (!this.path.length && this.mode === "patrol") {
      this.routeIndex = (this.routeIndex + 1) % this.route.length;
      this.path = this.pathfinder(this.position, this.route[this.routeIndex]);
    }
    const goal = this.path[0];
    if (!goal) return;
    const d = distance(this.position, goal),
      step =
        dt *
        (this.mode === "patrol"
          ? B.patrolSpeed
          : this.mode === "rush"
            ? B.rushSpeed
            : B.investigateSpeed);
    this.yaw = Math.atan2(goal.x - this.position.x, goal.z - this.position.z);
    if (d <= step) {
      this.position.x = goal.x;
      this.position.z = goal.z;
      this.path.shift();
    } else {
      this.position.x += ((goal.x - this.position.x) / d) * step;
      this.position.z += ((goal.z - this.position.z) / d) * step;
    }
  }
  catches(player: Point): boolean {
    return !inKuti(player) && distance(player, this.position) < B.catchRadius;
  }
}

/** Six safe seconds, then one audible gasp; release is required before holding again. */
export class Breath {
  remaining: number = B.breathSeconds;
  holding = false;
  private exhausted = false;
  update(dt: number, pressed: boolean): boolean {
    if (!pressed) {
      this.holding = false;
      this.remaining = Math.min(B.breathSeconds, this.remaining + dt * B.breathRecovery);
      if (this.remaining >= B.breathRearm) this.exhausted = false;
      return false;
    }
    this.holding = !this.exhausted && this.remaining > 0;
    if (!this.holding) return false;
    this.remaining = Math.max(0, this.remaining - dt);
    if (this.remaining === 0) {
      this.holding = false;
      this.exhausted = true;
      return true;
    }
    return false;
  }
}
