import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { HUNT_OBSTACLES, type GroundObstacle } from "../data/hunt";

/** Ground-plane A*: the spirit routes around the same posts / jars as Sora. */
export class HuntNavigation {
  readonly radius = 0.36;
  private readonly step = 0.35;
  private readonly width = 33;
  private readonly depth = 23;
  private readonly cells: Vector3[] = [];
  private readonly open: boolean[] = [];
  constructor(readonly obstacles: readonly GroundObstacle[] = HUNT_OBSTACLES) {
    for (let z = 0; z < this.depth; z++)
      for (let x = 0; x < this.width; x++) {
        const at = new Vector3(-5.6 + x * this.step, 0, -17.6 + z * this.step);
        this.cells.push(at);
        this.open.push(this.walkable(at));
      }
  }
  walkable(at: Vector3, radius = this.radius): boolean {
    return (
      at.x >= -5.85 &&
      at.x <= 5.85 &&
      at.z >= -17.8 &&
      at.z <= -9.65 &&
      !this.obstacles.some(
        (b) =>
          at.x > b.minX - radius &&
          at.x < b.maxX + radius &&
          at.z > b.minZ - radius &&
          at.z < b.maxZ + radius,
      )
    );
  }
  clear(a: Vector3, b: Vector3, radius = this.radius): boolean {
    const steps = Math.max(1, Math.ceil(Vector3.Distance(a, b) / 0.08));
    for (let i = 0; i <= steps; i++)
      if (!this.walkable(Vector3.Lerp(a, b, i / steps), radius)) return false;
    return true;
  }
  path(from: Vector3, to: Vector3): Vector3[] {
    const start = this.nearest(from, true),
      end = this.nearest(to);
    if (start < 0 || end < 0) return [];
    const score = new Map([[start, 0]]),
      previous = new Map<number, number>(),
      pending = new Set([start]);
    let closest = start;
    while (pending.size) {
      let current = -1,
        best = Infinity;
      for (const index of pending) {
        const cost = score.get(index)! + Vector3.Distance(this.cells[index], this.cells[end]);
        if (cost < best) {
          current = index;
          best = cost;
        }
      }
      if (
        Vector3.DistanceSquared(this.cells[current], to) <
        Vector3.DistanceSquared(this.cells[closest], to)
      )
        closest = current;
      if (current === end) return this.smoothPath(from, to, current, previous);
      pending.delete(current);
      const x = current % this.width,
        z = Math.floor(current / this.width);
      for (const [dx, dz] of [
        [-1, 0],
        [1, 0],
        [0, -1],
        [0, 1],
        [-1, -1],
        [1, 1],
        [-1, 1],
        [1, -1],
      ]) {
        const nx = x + dx,
          nz = z + dz;
        if (nx < 0 || nx >= this.width || nz < 0 || nz >= this.depth) continue;
        const index = nz * this.width + nx;
        if (!this.open[index] || !this.clear(this.cells[current], this.cells[index])) continue;
        const cost = score.get(current)! + Math.hypot(dx, dz) * this.step;
        if (cost >= (score.get(index) ?? Infinity)) continue;
        score.set(index, cost);
        previous.set(index, current);
        pending.add(index);
      }
    }
    // A jar can leave a tiny disconnected pocket behind it. Approach the closest
    // reachable side instead of stalling forever at an unreachable snapped goal.
    return this.smoothPath(from, to, closest, previous);
  }
  private smoothPath(
    from: Vector3,
    to: Vector3,
    end: number,
    previous: Map<number, number>,
  ): Vector3[] {
    let current = end;
    const points = [this.cells[current].clone()];
    while (previous.has(current)) {
      current = previous.get(current)!;
      points.unshift(this.cells[current].clone());
    }
    points.unshift(from.clone());
    if (this.walkable(to) && this.clear(points.at(-1)!, to))
      points.push(new Vector3(to.x, 0, to.z));
    const smooth: Vector3[] = [];
    for (let i = 0; i < points.length;) {
      smooth.push(points[i]);
      if (i === points.length - 1) break;
      let next = points.length - 1;
      while (next > i + 1 && !this.clear(points[i], points[next])) next--;
      i = next;
    }
    return smooth.slice(1);
  }
  private nearest(at: Vector3, connected = false): number {
    let best = Infinity,
      result = -1;
    for (let i = 0; i < this.cells.length; i++) {
      if (!this.open[i]) continue;
      const distance = Vector3.DistanceSquared(at, this.cells[i]);
      if (distance < best && (!connected || this.clear(at, this.cells[i]))) {
        best = distance;
        result = i;
      }
    }
    return result;
  }
}
