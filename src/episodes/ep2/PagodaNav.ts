import type { Scene } from "@babylonjs/core/scene";
import type { Point } from "./data/pagoda";

/** An obstacle's footprint (runtime X east, Z south). */
export interface Footprint {
  minX: number;
  maxX: number;
  minZ: number;
  maxZ: number;
}

/** Metres per grid cell. */
const CELL = 0.5;
/** A corpse's shoulders: obstacles are grown by this much. */
const RADIUS = 0.35;
/** Most cells A* may open for one path, so a hopeless search never stalls a frame. */
const BUDGET = 60000;

/**
 * Where the dead can walk, over the whole map: the compound, the clearing and the lost
 * garden. A grid of half-metre cells marks every collider standing at body height (walls,
 * stupas, trunks, tables, the tank's rim); paths are 8-way A* across it, then pulled
 * straight wherever the way is open, so a corpse walks the line a person would, not a
 * staircase of right angles.
 */
export class PagodaNav {
  private readonly blocked: Uint8Array;
  private readonly width: number;
  private readonly height: number;
  // Search buffers, kept between calls: a corpse asks for a path on every step it hears.
  private readonly cost: Float32Array;
  private readonly came: Int32Array;
  private readonly closed: Uint8Array;

  constructor(
    obstacles: readonly Footprint[],
    readonly bounds: Footprint = { minX: -84, maxX: 66, minZ: -100, maxZ: 43 },
  ) {
    this.width = Math.ceil((bounds.maxX - bounds.minX) / CELL);
    this.height = Math.ceil((bounds.maxZ - bounds.minZ) / CELL);
    this.blocked = new Uint8Array(this.width * this.height);
    this.cost = new Float32Array(this.blocked.length);
    this.came = new Int32Array(this.blocked.length);
    this.closed = new Uint8Array(this.blocked.length);
    for (const o of obstacles) {
      const i0 = this.col(o.minX - RADIUS),
        i1 = this.col(o.maxX + RADIUS),
        j0 = this.row(o.minZ - RADIUS),
        j1 = this.row(o.maxZ + RADIUS);
      for (let j = Math.max(0, j0); j <= Math.min(this.height - 1, j1); j++)
        for (let i = Math.max(0, i0); i <= Math.min(this.width - 1, i1); i++)
          this.blocked[j * this.width + i] = 1;
    }
  }

  /**
   * The colliders of the loaded area that stand at body height. Ground slabs, floors, the
   * low brick tiers and ramps are walkable (their tops are under 35 cm).
   */
  static fromScene(scene: Scene): PagodaNav {
    const obstacles: Footprint[] = [];
    for (const mesh of scene.meshes) {
      if (!mesh.name.startsWith("col_")) continue;
      mesh.computeWorldMatrix(true);
      const box = mesh.getBoundingInfo().boundingBox;
      const lo = box.minimumWorld,
        hi = box.maximumWorld;
      if (hi.y < 0.35 || lo.y > 1.6) continue;
      // Huge thin floors stood on edge are not obstacles either.
      if (hi.x - lo.x > 60 && hi.z - lo.z > 60) continue;
      obstacles.push({ minX: lo.x, maxX: hi.x, minZ: lo.z, maxZ: hi.z });
    }
    return new PagodaNav(obstacles);
  }

  private col(x: number): number {
    return Math.floor((x - this.bounds.minX) / CELL);
  }
  private row(z: number): number {
    return Math.floor((z - this.bounds.minZ) / CELL);
  }
  private centre(i: number, j: number): Point {
    return { x: this.bounds.minX + (i + 0.5) * CELL, z: this.bounds.minZ + (j + 0.5) * CELL };
  }
  private open(i: number, j: number): boolean {
    return (
      i >= 0 && j >= 0 && i < this.width && j < this.height && !this.blocked[j * this.width + i]
    );
  }

  /** Whether a corpse could stand at `p`. */
  walkable(p: Point): boolean {
    return this.open(this.col(p.x), this.row(p.z));
  }

  /** True when a straight walk from `a` to `b` crosses no blocked cell. */
  straight(a: Point, b: Point): boolean {
    const d = Math.hypot(b.x - a.x, b.z - a.z);
    const steps = Math.ceil(d / (CELL * 0.5));
    for (let k = 0; k <= steps; k++) {
      const t = steps ? k / steps : 0;
      if (!this.walkable({ x: a.x + (b.x - a.x) * t, z: a.z + (b.z - a.z) * t })) return false;
    }
    return true;
  }

  /** The nearest open cell to `p`, searching outward a few metres. */
  private nearest(p: Point): [number, number] | null {
    const i = this.col(p.x),
      j = this.row(p.z);
    for (let r = 0; r < 12; r++)
      for (let dj = -r; dj <= r; dj++)
        for (let di = -r; di <= r; di++) {
          if (Math.max(Math.abs(di), Math.abs(dj)) !== r) continue;
          if (this.open(i + di, j + dj)) return [i + di, j + dj];
        }
    return null;
  }

  /** A walkable path from `from` to `to` (excluding `from`), or [] if there is none. */
  path(from: Point, to: Point): Point[] {
    const start = this.nearest(from),
      goal = this.nearest(to);
    if (!start || !goal) return [];
    const w = this.width;
    const s = start[1] * w + start[0],
      e = goal[1] * w + goal[0];
    if (s === e) return [to];
    const cost = this.cost.fill(Infinity),
      came = this.came.fill(-1),
      closed = this.closed.fill(0);
    const heap = new MinHeap();
    const gx = goal[0],
      gz = goal[1];
    const h = (i: number, j: number) => {
      const dx = Math.abs(i - gx),
        dz = Math.abs(j - gz);
      return Math.max(dx, dz) + 0.4142 * Math.min(dx, dz);
    };
    cost[s] = 0;
    heap.push(s, h(start[0], start[1]));
    let opened = 0;
    while (heap.size && opened < BUDGET) {
      const c = heap.pop();
      if (c === e) break;
      if (closed[c]) continue;
      closed[c] = 1;
      opened++;
      const ci = c % w,
        cj = (c - ci) / w;
      for (let dj = -1; dj <= 1; dj++)
        for (let di = -1; di <= 1; di++) {
          if (!di && !dj) continue;
          const ni = ci + di,
            nj = cj + dj;
          if (!this.open(ni, nj)) continue;
          // No squeezing diagonally between two blocked corners.
          if (di && dj && (!this.open(ci + di, cj) || !this.open(ci, cj + dj))) continue;
          const n = nj * w + ni;
          const g = cost[c] + (di && dj ? 1.4142 : 1);
          if (g >= cost[n]) continue;
          cost[n] = g;
          came[n] = c;
          heap.push(n, g + h(ni, nj));
        }
    }
    if (came[e] < 0) return [];
    const cells: Point[] = [];
    for (let c = e; c !== s; c = came[c]) {
      const i = c % w;
      cells.push(this.centre(i, (c - i) / w));
    }
    cells.reverse();
    cells[cells.length - 1] = this.walkable(to) ? { ...to } : cells[cells.length - 1];
    // Pull the path straight wherever the way is open.
    const out: Point[] = [];
    let anchor = from;
    for (let k = 0; k < cells.length; k++) {
      const next = cells[k + 1];
      if (next && this.straight(anchor, next)) continue;
      out.push(cells[k]);
      anchor = cells[k];
    }
    return out;
  }
}

/** A binary heap of cell indices by priority. */
class MinHeap {
  private readonly items: number[] = [];
  private readonly keys: number[] = [];
  get size(): number {
    return this.items.length;
  }
  push(item: number, key: number): void {
    this.items.push(item);
    this.keys.push(key);
    let i = this.items.length - 1;
    while (i > 0) {
      const p = (i - 1) >> 1;
      if (this.keys[p] <= this.keys[i]) break;
      this.swap(i, p);
      i = p;
    }
  }
  pop(): number {
    const top = this.items[0];
    const lastItem = this.items.pop()!,
      lastKey = this.keys.pop()!;
    if (this.items.length) {
      this.items[0] = lastItem;
      this.keys[0] = lastKey;
      let i = 0;
      for (;;) {
        const l = i * 2 + 1,
          r = l + 1;
        let m = i;
        if (l < this.items.length && this.keys[l] < this.keys[m]) m = l;
        if (r < this.items.length && this.keys[r] < this.keys[m]) m = r;
        if (m === i) break;
        this.swap(i, m);
        i = m;
      }
    }
    return top;
  }
  private swap(a: number, b: number): void {
    [this.items[a], this.items[b]] = [this.items[b], this.items[a]];
    [this.keys[a], this.keys[b]] = [this.keys[b], this.keys[a]];
  }
}
