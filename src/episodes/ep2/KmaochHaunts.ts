import { PAGODA_BALANCE as B } from "./data/balance";
import type { Point } from "./data/pagoda";
import type { PretBrain } from "./PretBrain";

/** How Sora sees corpse `i`: `facing` 1 when it is dead ahead of her, and how far. */
export interface HauntView {
  facing: number;
  distance: number;
}

/** What the haunts need to know of Sora and the ground. */
export interface HauntScene {
  feet: Point;
  /** Her heading, radians: forward is (sin, cos). */
  yaw: number;
  /** Seconds she has stood without moving. */
  still: number;
  /** In the kuti: nothing comes for her there. */
  safe: boolean;
  /** Whether a corpse could stand at `p`. */
  walkable(p: Point): boolean;
  /** Whether nothing stands between two points at eye height. */
  clear(a: Point, b: Point): boolean;
}

export type HauntEvent =
  /** Corpse `i` has started to follow her. */
  | { kind: "stalk"; i: number }
  /** Corpse `i` now stands just behind her, at `at`. */
  | { kind: "loom"; i: number; at: Point }
  /** She turned and saw the one behind her: its neck goes over and it lunges. */
  | { kind: "turn"; i: number; at: Point }
  /** The one behind her is gone from `at`: `seen`, in front of her, or quietly unseen. */
  | { kind: "gone"; i: number; at: Point; seen: boolean };

/** The point `gap` metres straight behind someone at `feet` facing `yaw`. */
export function behind(feet: Point, yaw: number, gap: number): Point {
  return { x: feet.x - Math.sin(yaw) * gap, z: feet.z - Math.cos(yaw) * gap };
}

/** Where the one behind her may stand: turned off straight behind (radians), and how far. */
const LOOM_SPOTS: readonly [number, number][] = [
  [0, 2.3],
  [0.35, 2.3],
  [-0.35, 2.3],
  [0, 2.9],
  [0.6, 2.6],
  [-0.6, 2.6],
  [0.9, 2.4],
  [-0.9, 2.4],
  [0, 3.4],
];
/** Seconds after she turns: the lunge starts, stops, and it is gone. */
const LUNGE_FROM = 0.28;
const LUNGE_TO = 0.55;
const LUNGE_GONE = 0.78;
/** It lunges no nearer than this: well outside a catch. */
const LUNGE_STOP = 1.05;

/**
 * The garden's dead do more than walk their rounds. Now and then one follows Sora, a few
 * metres behind, moving only while her back is turned: when she looks it stands still, and
 * looked at too long it is gone (ShroudedDead.watch). And if she stands still long enough
 * outside the kuti, one is put right behind her, to be found when she turns: its neck snaps
 * over, it lunges, and it is gone. Neither can catch her; only the dead on their rounds,
 * and those that hear her, can.
 */
export class KmaochHaunts {
  private nextStalk: number;
  private nextLoom: number;
  private stalker = -1;
  private stalkFor = 0;
  private repath = 0;
  /** Where the stalker was when it set off, to go back to if it is seen off. */
  private stalkHome: Point = { x: 0, z: 0 };
  private loom: {
    i: number;
    t: number;
    /** Seconds since she turned to it, or -1. */
    turned: number;
    unseen: number;
    home: Point;
    homeYaw: number;
  } | null = null;

  constructor(private readonly rand: () => number = Math.random) {
    this.nextStalk = 25 + rand() * 25;
    this.nextLoom = 40 + rand() * 40;
  }

  /** Which corpse is following her, or -1. */
  get following(): number {
    return this.stalker;
  }

  /** Which corpse stands behind her, or -1. */
  get looming(): number {
    return this.loom?.i ?? -1;
  }

  /**
   * One frame. `awake(i)` says whether corpse `i` walks now, `view(i)` how Sora sees it.
   * Moves and freezes the brains it uses; returns what the scene should show and sound.
   */
  update(
    dt: number,
    scene: HauntScene,
    brains: readonly PretBrain[],
    awake: (i: number) => boolean,
    view: (i: number) => HauntView,
  ): HauntEvent[] {
    const events: HauntEvent[] = [];
    this.updateStalk(dt, scene, brains, awake, view, events);
    this.updateLoom(dt, scene, brains, awake, view, events);
    return events;
  }

  /** Corpse `i` was looked at too long and vanished: it gives up and goes home. */
  vanished(i: number, brains: readonly PretBrain[]): void {
    if (i === this.looming) {
      this.endLoom(brains, [], false);
      return;
    }
    if (i !== this.stalker) return;
    brains[i].place(this.stalkHome);
    brains[i].resume();
    this.stalker = -1;
  }

  /** Lets go of every corpse (a retry, a cinematic, the end of the garden). */
  reset(brains: readonly PretBrain[]): void {
    if (this.stalker >= 0) brains[this.stalker].resume();
    if (this.loom) {
      brains[this.loom.i].place(this.loom.home, this.loom.homeYaw);
      brains[this.loom.i].resume();
    }
    this.stalker = -1;
    this.loom = null;
  }

  private updateStalk(
    dt: number,
    scene: HauntScene,
    brains: readonly PretBrain[],
    awake: (i: number) => boolean,
    view: (i: number) => HauntView,
    events: HauntEvent[],
  ): void {
    if (this.stalker < 0) {
      if (scene.safe) return;
      this.nextStalk -= dt;
      if (this.nextStalk > 0) return;
      let best = -1,
        bestDistance = Infinity;
      brains.forEach((b, i) => {
        if (!awake(i) || b.mode !== "patrol" || i === this.looming) return;
        const v = view(i);
        // One she cannot see, near enough to come up on her before long.
        if (v.distance < 9 || v.distance > 30 || v.facing > 0.3) return;
        if (v.distance < bestDistance) [best, bestDistance] = [i, v.distance];
      });
      if (best < 0) {
        this.nextStalk = 5;
        return;
      }
      this.stalker = best;
      this.stalkFor = B.stalkSeconds;
      this.repath = 0;
      this.stalkHome = { ...brains[best].position };
      this.nextStalk = 45 + this.rand() * 50;
      brains[best].stalk(behind(scene.feet, scene.yaw, B.stalkGap));
      events.push({ kind: "stalk", i: best });
      return;
    }
    const i = this.stalker,
      b = brains[i];
    this.stalkFor -= dt;
    // Something it heard has taken it over, or it has had its time, or she is safe.
    if (b.mode !== "stalk" || !awake(i) || this.stalkFor <= 0 || scene.safe) {
      b.frozen = false;
      if (b.mode === "stalk") b.resume();
      this.stalker = -1;
      return;
    }
    const v = view(i);
    const seen = v.facing > 0.8 && v.distance < 24 && scene.clear(scene.feet, b.position);
    b.frozen = seen || v.distance <= B.stalkGap + 0.3;
    this.repath -= dt;
    if (!b.frozen && this.repath <= 0) {
      this.repath = 0.8;
      const to = behind(scene.feet, scene.yaw, B.stalkGap);
      b.stalk(scene.walkable(to) ? to : scene.feet);
    }
  }

  private updateLoom(
    dt: number,
    scene: HauntScene,
    brains: readonly PretBrain[],
    awake: (i: number) => boolean,
    view: (i: number) => HauntView,
    events: HauntEvent[],
  ): void {
    if (!this.loom) {
      if (scene.safe) return;
      this.nextLoom -= dt;
      if (this.nextLoom > 0 || scene.still < 4) return;
      // Straight behind her if it can stand there, else a little to one side.
      const spot = LOOM_SPOTS.map(([turn, gap]) => behind(scene.feet, scene.yaw + turn, gap)).find(
        (p) => scene.walkable(p) && scene.clear(scene.feet, p),
      );
      if (!spot) {
        this.nextLoom = 2;
        return;
      }
      // The one already following, if there is one; else the nearest she cannot see.
      let pick = -1,
        nearest = Infinity;
      brains.forEach((b, i) => {
        if (!awake(i) || (b.mode !== "patrol" && b.mode !== "stalk")) return;
        const v = view(i);
        if (i !== this.stalker && (v.distance < 7 || v.facing > 0.2)) return;
        const d = i === this.stalker ? -1 : v.distance;
        if (d < nearest) [pick, nearest] = [i, d];
      });
      if (pick < 0) {
        this.nextLoom = 4;
        return;
      }
      const b = brains[pick];
      const home = pick === this.stalker ? this.stalkHome : { ...b.position };
      if (pick === this.stalker) this.stalker = -1;
      this.loom = { i: pick, t: 0, turned: -1, unseen: 0, home, homeYaw: b.yaw };
      b.place(spot, Math.atan2(scene.feet.x - spot.x, scene.feet.z - spot.z));
      b.mode = "loom";
      b.frozen = true;
      this.nextLoom = 80 + this.rand() * 70;
      events.push({ kind: "loom", i: pick, at: { ...spot } });
      return;
    }
    const loom = this.loom,
      b = brains[loom.i];
    loom.t += dt;
    const v = view(loom.i);
    if (loom.turned < 0) {
      if (v.facing > 0.5 && v.distance < 8) {
        loom.turned = 0;
        events.push({ kind: "turn", i: loom.i, at: { ...b.position } });
        return;
      }
      // She walked off without turning: it is not there when she next looks.
      loom.unseen = (v.distance > 4 || loom.t > 30) && v.facing < 0.3 ? loom.unseen + dt : 0;
      if (loom.unseen > 2.5) this.endLoom(brains, events, false);
      return;
    }
    loom.turned += dt;
    if (loom.turned > LUNGE_FROM && loom.turned < LUNGE_TO) {
      const dx = scene.feet.x - b.position.x,
        dz = scene.feet.z - b.position.z;
      const d = Math.hypot(dx, dz) || 1;
      const step = Math.min(dt * 5, Math.max(0, d - LUNGE_STOP));
      b.position.x += (dx / d) * step;
      b.position.z += (dz / d) * step;
      b.yaw = Math.atan2(dx, dz);
    }
    if (loom.turned >= LUNGE_GONE) this.endLoom(brains, events, true);
  }

  private endLoom(brains: readonly PretBrain[], events: HauntEvent[], seen: boolean): void {
    const loom = this.loom!,
      b = brains[loom.i];
    events.push({ kind: "gone", i: loom.i, at: { ...b.position }, seen });
    b.place(loom.home, loom.homeYaw);
    b.resume();
    this.loom = null;
  }
}
