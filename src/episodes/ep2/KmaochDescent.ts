import type { Point } from "./data/pagoda";
import type { PretBrain } from "./PretBrain";
import type { HauntView } from "./KmaochHaunts";
import { trunkAt, trunkRadius, type ClimbTree } from "./pagodaTrees";

/** What the descent needs of Sora and the ground. */
export interface DescentScene {
  feet: Point;
  yaw: number;
  safe: boolean;
  walkable(p: Point): boolean;
  clear(a: Point, b: Point): boolean;
}

/** Where the body is while it is on the tree: `out` points from the trunk towards Sora. */
export interface DescentPose {
  i: number;
  x: number;
  y: number;
  z: number;
  out: Point;
  /** 0 head down on the bark, 1 on the ground facing her. */
  flip: number;
  /** How fast its limbs go, as a multiple of the recorded crawl. */
  rate: number;
}

export type DescentEvent =
  /** Corpse `i` is on a trunk above her, unseen; it scratches until she looks. */
  | { kind: "scratch"; i: number; at: { x: number; y: number; z: number } }
  /** She has seen it: it comes down head first, fast. */
  | { kind: "down"; i: number; at: { x: number; y: number; z: number } }
  /** It hits the ground at the foot of the tree. */
  | { kind: "land"; i: number; at: Point }
  /** It comes for her on hands and knees. */
  | { kind: "charge"; i: number; at: Point };

/** Seconds between descents: the first comes a while into the garden. */
const FIRST = [30, 60] as const;
const GAP = [70, 150] as const;
/** The trees it may use: in front of her once she turns, not too close to see it come. */
const NEAR = 4.5;
const FAR = 9.5;
/** Metres a second down the trunk, and where its hips let go of the bark. */
const DOWN_SPEED = 2.9;
const LET_GO = 1.1;
const FLIP_SECONDS = 0.2;
/** It crouches where it landed, head jerking, before it comes. */
const CROUCH = 0.45;
/** It gives up waiting if she never looks, or walks off. */
const WAIT = 14;
const GIVE_UP = 20;
/** Seconds it keeps finding her again while it comes. */
const HOMING = 3;

type Phase = "wait" | "down" | "flip" | "crouch";

/**
 * A kmaoch comes down a tree at Sora, head first. While she is turned away one is put
 * high on a trunk in front of where she is going; its nails rake the bark now and then
 * until she looks. Then it scuttles down the trunk far faster than anything should,
 * drops the last of the way with a thud, crouches a breath, and comes at her on hands
 * and knees. It is a real hunter from then on: it can catch her.
 */
export class KmaochDescent {
  private nextDescent: number;
  private readonly used = new Set<number>();
  private state: {
    i: number;
    tree: number;
    phase: Phase;
    t: number;
    y: number;
    /** The bark facing her where it starts, and low down where it lets go. */
    upper: Point;
    lower: Point;
    top: number;
    out: Point;
    base: Point;
    home: Point;
    homeYaw: number;
    nextScratch: number;
  } | null = null;
  /** Corpses that came down crawling, and whether they crawled before: until they rest. */
  private readonly crawling = new Map<number, { was: boolean; homing: number }>();

  constructor(private readonly rand: () => number = Math.random) {
    this.nextDescent = FIRST[0] + rand() * (FIRST[1] - FIRST[0]);
  }

  /** Which corpse is on (or coming off) a tree, or -1. */
  get active(): number {
    return this.state?.i ?? -1;
  }

  /** The body on the tree, for the rig; null when none is. */
  pose(): DescentPose | null {
    const s = this.state;
    if (!s || s.phase === "crouch") return null;
    const flip = s.phase === "flip" ? Math.min(1, s.t / FLIP_SECONDS) : 0;
    const bark = s.base;
    const trunk = this.surfaceAt(s);
    return {
      i: s.i,
      x: trunk.x + (bark.x - trunk.x) * flip,
      y: s.y * (1 - flip),
      z: trunk.z + (bark.z - trunk.z) * flip,
      out: s.out,
      flip,
      rate: s.phase === "wait" ? 0.05 : 6,
    };
  }

  update(
    dt: number,
    scene: DescentScene,
    trees: readonly ClimbTree[],
    brains: readonly PretBrain[],
    free: (i: number) => boolean,
    view: (i: number) => HauntView,
  ): DescentEvent[] {
    const events: DescentEvent[] = [];
    this.settle(dt, scene, brains);
    if (!this.state) {
      if (scene.safe) return events;
      this.nextDescent -= dt;
      if (this.nextDescent > 0) return events;
      this.nextDescent = 4;
      this.arm(scene, trees, brains, free, view);
      return events;
    }
    const s = this.state,
      b = brains[s.i],
      tree = trees[s.tree];
    s.t += dt;
    const at = () => ({ ...this.surfaceAt(s), y: s.y + 0.5 });
    switch (s.phase) {
      case "wait": {
        const dx = tree.x - scene.feet.x,
          dz = tree.z - scene.feet.z;
        const d = Math.hypot(dx, dz) || 1;
        const looking = (Math.sin(scene.yaw) * dx + Math.cos(scene.yaw) * dz) / d;
        if (looking > 0.82 && d < FAR + 4) {
          s.phase = "down";
          s.t = 0;
          events.push({ kind: "down", i: s.i, at: at() });
          break;
        }
        if (d > GIVE_UP || s.t > WAIT || scene.safe) {
          this.release(brains);
          break;
        }
        s.nextScratch -= dt;
        if (s.nextScratch <= 0) {
          s.nextScratch = 1.4 + this.rand() * 1.4;
          events.push({ kind: "scratch", i: s.i, at: at() });
        }
        break;
      }
      case "down":
        s.y = Math.max(LET_GO, s.y - DOWN_SPEED * dt);
        if (s.y <= LET_GO) {
          s.phase = "flip";
          s.t = 0;
        }
        break;
      case "flip":
        if (s.t >= FLIP_SECONDS) {
          s.phase = "crouch";
          s.t = 0;
          b.place(s.base, Math.atan2(scene.feet.x - s.base.x, scene.feet.z - s.base.z));
          this.crawling.set(s.i, { was: b.crawls, homing: HOMING });
          b.crawls = true;
          events.push({ kind: "land", i: s.i, at: { ...s.base } });
        }
        break;
      case "crouch":
        b.yaw = Math.atan2(scene.feet.x - b.position.x, scene.feet.z - b.position.z);
        if (s.t >= CROUCH) {
          b.charge(scene.feet);
          events.push({ kind: "charge", i: s.i, at: { ...b.position } });
          this.state = null;
          this.nextDescent = GAP[0] + this.rand() * (GAP[1] - GAP[0]);
        }
        break;
    }
    return events;
  }

  /** Lets go of every corpse (the garden over, a cinematic, a retry). */
  reset(brains: readonly PretBrain[]): void {
    if (this.state) this.release(brains);
    for (const [i, c] of this.crawling) brains[i].crawls = c.was;
    this.crawling.clear();
  }

  /** Puts a corpse on a tree ahead of where she is turned from, if one fits. */
  private arm(
    scene: DescentScene,
    trees: readonly ClimbTree[],
    brains: readonly PretBrain[],
    free: (i: number) => boolean,
    view: (i: number) => HauntView,
  ): void {
    // The nearest free corpse she cannot see, a good way off, is the one moved.
    let pick = -1,
      far = 0;
    brains.forEach((b, i) => {
      if (!free(i) || b.mode !== "patrol") return;
      const v = view(i);
      // Never moved where she could see it go: behind her, hidden, or lost in the dark.
      const unseen = v.facing < 0.3 || v.distance > 24 || !scene.clear(scene.feet, b.position);
      if (v.distance < 15 || !unseen) return;
      if (pick < 0 || v.distance < far) [pick, far] = [i, v.distance];
    });
    if (pick < 0) return;
    const fx = Math.sin(scene.yaw),
      fz = Math.cos(scene.yaw);
    let best = -1,
      bestScore = Infinity;
    let base: Point | null = null,
      out: Point = { x: 0, z: 0 };
    trees.forEach((t, k) => {
      if (this.used.has(k)) return;
      const dx = t.x - scene.feet.x,
        dz = t.z - scene.feet.z;
      const d = Math.hypot(dx, dz);
      if (d < NEAR || d > FAR) return;
      // Behind her or to the side: she finds it by turning, never sees it put there.
      if ((fx * dx + fz * dz) / d > 0.2) return;
      const u = { x: -dx / d, z: -dz / d };
      const r = trunkRadius(t, scene.feet, (p) => scene.walkable(p));
      const foot = { x: t.x + u.x * (r + 0.6), z: t.z + u.z * (r + 0.6) };
      // Up high it shows over the stupas; on the ground it finds its own way to her.
      if (!scene.walkable(foot)) return;
      // The nearer the better: it should be plain when she turns.
      if (d < bestScore) {
        [best, bestScore, base, out] = [k, d, foot, u];
      }
    });
    if (best < 0 || !base) return;
    const b = brains[pick];
    const tree = trees[best];
    this.used.add(best);
    const top = Math.min(7.5, tree.height * 0.55);
    // The bark facing her at a height: the trunk's own middle there, out by its own girth.
    const surface = (y: number): Point => {
      const slice = trunkAt(tree, y);
      const dx = scene.feet.x - slice.x,
        dz = scene.feet.z - slice.z;
      const d = Math.hypot(dx, dz) || 1;
      return { x: slice.x + (dx / d) * (slice.r + 0.04), z: slice.z + (dz / d) * (slice.r + 0.04) };
    };
    this.state = {
      i: pick,
      tree: best,
      phase: "wait",
      t: 0,
      y: top,
      upper: surface(top),
      lower: surface(1.2),
      top,
      out,
      base,
      home: { ...b.position },
      homeYaw: b.yaw,
      nextScratch: 0.6,
    };
    // Held by the tree: it neither hears nor catches until it lets go.
    b.place(base, b.yaw);
    b.mode = "loom";
    b.frozen = true;
  }

  /** The bark under the body at its height: the trunk swells towards its foot. */
  private surfaceAt(s: NonNullable<KmaochDescent["state"]>): Point {
    const u = Math.max(0, Math.min(1, (s.y - 1.2) / Math.max(0.1, s.top - 1.2)));
    return {
      x: s.lower.x + (s.upper.x - s.lower.x) * u,
      z: s.lower.z + (s.upper.z - s.lower.z) * u,
    };
  }

  /** Gone back to its rounds, unseen. */
  private release(brains: readonly PretBrain[]): void {
    const s = this.state!;
    brains[s.i].place(s.home, s.homeYaw);
    brains[s.i].resume();
    this.state = null;
    this.nextDescent = 20 + this.rand() * 20;
  }

  /** The ones that came down keep finding her a while, then rise again when they rest. */
  private settle(dt: number, scene: DescentScene, brains: readonly PretBrain[]): void {
    for (const [i, c] of this.crawling) {
      const b = brains[i];
      if (b.mode === "rush" && c.homing > 0) {
        const before = c.homing;
        c.homing -= dt;
        // Every half second it finds her again.
        if (Math.floor(before * 2) !== Math.floor(c.homing * 2)) b.charge(scene.feet, false);
      }
      if (b.mode === "patrol") {
        b.crawls = c.was;
        this.crawling.delete(i);
      }
    }
  }
}
