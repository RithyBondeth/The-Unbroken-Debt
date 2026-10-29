import { Vector3 } from "@babylonjs/core/Maths/math.vector";

export interface CoverRect {
  minX: number;
  maxX: number;
  minZ: number;
  maxZ: number;
}
const PATROL = [
  new Vector3(-1.8, 0, 22),
  new Vector3(-1.8, 0, 12),
  new Vector3(2.8, 0, 12),
  new Vector3(2.8, 0, 24),
];

/** Visibility graph around solid cover. Every returned segment clears the actor's capsule. */
export class RoadNavigation {
  constructor(readonly obstacles: readonly CoverRect[] = []) {}
  clear(a: Vector3, b: Vector3): boolean {
    const steps = Math.max(1, Math.ceil(Vector3.Distance(a, b) / 0.1));
    for (let i = 0; i <= steps; i++) {
      const x = a.x + ((b.x - a.x) * i) / steps,
        z = a.z + ((b.z - a.z) * i) / steps;
      if (
        x < -7 ||
        x > 8 ||
        z < 9 ||
        z > 57 ||
        this.obstacles.some(
          (r) => x > r.minX - 0.36 && x < r.maxX + 0.36 && z > r.minZ - 0.36 && z < r.maxZ + 0.36,
        )
      )
        return false;
    }
    return true;
  }
  path(from: Vector3, target: Vector3): Vector3[] {
    const end = new Vector3(
      Math.max(-6.8, Math.min(7.8, target.x)),
      0,
      Math.max(9.2, Math.min(56.8, target.z)),
    );
    const nodes = [
      from,
      end,
      ...this.obstacles.flatMap((r) => [
        new Vector3(r.minX - 0.42, 0, r.minZ - 0.42),
        new Vector3(r.maxX + 0.42, 0, r.minZ - 0.42),
        new Vector3(r.minX - 0.42, 0, r.maxZ + 0.42),
        new Vector3(r.maxX + 0.42, 0, r.maxZ + 0.42),
      ]),
    ];
    const distances = nodes.map(() => Infinity),
      previous = nodes.map(() => -1),
      open = new Set(nodes.map((_, i) => i));
    distances[0] = 0;
    while (open.size) {
      let current = -1;
      for (const i of open) if (current < 0 || distances[i] < distances[current]) current = i;
      if (!Number.isFinite(distances[current])) break;
      if (current === 1) {
        const path: Vector3[] = [];
        for (let i = 1; i > 0; i = previous[i]) path.unshift(nodes[i]);
        return path;
      }
      open.delete(current);
      for (const i of open)
        if (this.clear(nodes[current], nodes[i])) {
          const cost = distances[current] + Vector3.Distance(nodes[current], nodes[i]);
          if (cost < distances[i]) {
            distances[i] = cost;
            previous[i] = current;
          }
        }
    }
    return [];
  }
}

export class EarlyStealthBrain {
  readonly position: Vector3;
  readonly direction = new Vector3(0, 0, 1);
  state: "patrol" | "investigate" | "chase" | "search" | "caught" = "patrol";
  suspicion = 0;
  elapsed = 0;
  private patrol = 1;
  private memory = 0;
  private wait = 0;
  private routeIn = 0;
  private route: Vector3[] = [];
  private readonly lastKnown = new Vector3();

  constructor(
    private readonly patrolPoints: readonly Vector3[] = PATROL,
    readonly navigation = new RoadNavigation(),
  ) {
    this.position = patrolPoints[0].clone();
  }

  hear(at: Vector3, loudness: number): void {
    if (
      this.state === "caught" ||
      this.state === "chase" ||
      Vector3.Distance(this.position, at) > loudness * 9
    )
      return;
    this.lastKnown.copyFrom(at);
    this.state = "investigate";
    this.memory = 5;
    this.routeIn = 0;
  }
  sees(at: Vector3, lit: boolean, crouched: boolean, unobstructed: boolean): boolean {
    const dx = at.x - this.position.x,
      dz = at.z - this.position.z,
      d = Math.hypot(dx, dz);
    return (
      unobstructed &&
      d < (lit ? 15 : crouched ? 6 : 9) &&
      (d < 1.4 || (dx * this.direction.x + dz * this.direction.z) / d > 0.42)
    );
  }
  update(dt: number, at: Vector3, lit: boolean, crouched: boolean, unobstructed: boolean): void {
    if (this.state === "caught") return;
    this.elapsed += dt;
    const sees = this.sees(at, lit, crouched, unobstructed);
    this.suspicion = Math.max(
      0,
      Math.min(1, this.suspicion + dt * (sees ? (lit ? 1.8 : 1.05) : -0.75)),
    );
    if (sees && this.state === "chase") {
      this.lastKnown.copyFrom(at);
      this.memory = 3;
    }
    if (this.suspicion >= 1) {
      this.state = "chase";
      this.lastKnown.copyFrom(at);
      this.memory = 3;
    }
    if (unobstructed && this.state === "chase" && Vector3.Distance(this.position, at) < 0.72) {
      this.state = "caught";
      return;
    }
    if (sees && this.state === "patrol" && this.suspicion > 0.1) {
      this.direction.copyFrom(at.subtract(this.position));
      this.direction.y = 0;
      this.direction.normalize();
      return;
    }
    if (this.state !== "patrol") {
      if (!sees) this.memory -= dt;
      if (this.memory <= 0 && this.state !== "search") {
        this.state = "search";
        this.wait = 3.5;
        this.suspicion = 0;
      }
      if (this.state === "search") {
        this.wait -= dt;
        this.direction.set(Math.sin(this.elapsed * 0.7), 0, Math.cos(this.elapsed * 0.7));
        if (this.wait <= 0) {
          this.state = "patrol";
          this.routeIn = 0;
        }
        return;
      }
    }
    const target = this.state === "patrol" ? this.patrolPoints[this.patrol] : this.lastKnown;
    if (Vector3.Distance(this.position, target) < 0.3) {
      if (this.state === "patrol") {
        this.wait -= dt;
        if (this.wait <= 0) {
          this.patrol = (this.patrol + 1) % this.patrolPoints.length;
          this.wait = 1.8;
          this.routeIn = 0;
        }
      } else {
        this.state = "search";
        this.wait = 3.5;
      }
      return;
    }
    this.routeIn -= dt;
    if (this.routeIn <= 0) {
      this.route = this.navigation.path(this.position, target);
      this.routeIn = 0.4;
    }
    while (this.route.length && Vector3.Distance(this.position, this.route[0]) < 0.12)
      this.route.shift();
    const next = this.route[0];
    if (!next) return;
    const to = next.subtract(this.position);
    to.y = 0;
    const distance = to.length();
    if (distance < 0.001) return;
    this.direction.copyFrom(to.scale(1 / distance));
    const step = this.position.add(
      this.direction.scale(
        Math.min(
          distance,
          dt * (this.state === "chase" ? 2.55 : this.state === "investigate" ? 1.2 : 0.85),
        ),
      ),
    );
    if (this.navigation.clear(this.position, step)) this.position.copyFrom(step);
  }
}
