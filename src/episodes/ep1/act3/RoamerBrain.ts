import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import {
  HOUSE_ARENA,
  HUNT_ARENAS,
  ROAMER_CHASE_SPEED,
  ROAMER_FOLLOWS_AFTER,
  ROAMER_PATROL_SPEED,
  ROAMER_ROUTE,
  arenaAt,
  huntHearing,
  type HuntArena,
} from "../data/hunt";
import { HuntNavigation } from "./HuntNavigation";

export type RoamerState = "idle" | "patrol" | "investigating" | "chasing" | "caught";

/**
 * The roamer of the Act III hunt. She keeps to one arena at a time (the ground under the
 * back block, or the rice barn's floor): she hears and sees only there, and catches only
 * there. When Sora goes from one to the other, the roamer comes in after her a few
 * seconds later, by the other arena's way in (the first point of its route).
 */
export class RoamerBrain {
  state: RoamerState = "idle";
  readonly position = ROAMER_ROUTE[0].clone();
  readonly direction = new Vector3(0, 0, 1);
  elapsed = 0;
  arena: HuntArena = HOUSE_ARENA;
  private route = 1;
  private points: Vector3[] = [];
  private target: Vector3 | null = null;
  private repath = 0;
  private search = 0;
  private destination: Vector3 | null = null;
  private memory = 0;
  /** Seconds Sora has been in the other arena. */
  private away = 0;
  private readonly navigations = new Map<string, HuntNavigation>();
  constructor(navigation?: HuntNavigation) {
    for (const arena of HUNT_ARENAS)
      this.navigations.set(
        arena.id,
        navigation && navigation.arena.id === arena.id ? navigation : new HuntNavigation(arena),
      );
  }
  /** The current arena's navigation. */
  get navigation(): HuntNavigation {
    return this.navigations.get(this.arena.id)!;
  }
  get active(): boolean {
    return this.state !== "idle" && this.state !== "caught";
  }
  start(arena: HuntArena = HOUSE_ARENA): void {
    this.enter(arena);
    this.elapsed = 0;
    this.state = "patrol";
  }
  reset(): void {
    this.state = "idle";
    this.points = [];
    this.target = null;
  }
  /** Into `arena` by its way in, patrolling. */
  enter(arena: HuntArena): void {
    this.arena = arena;
    this.position.copyFrom(arena.route[0]);
    this.route = 1 % arena.route.length;
    this.points = [];
    this.target = null;
    this.destination = null;
    this.repath = 0;
    this.search = 0;
    this.memory = 0;
    this.away = 0;
    if (this.active) this.state = "patrol";
  }
  hear(at: Vector3, loudness: number, jar = false): boolean {
    if (
      !this.active ||
      arenaAt(at) !== this.arena ||
      this.state === "chasing" ||
      Vector3.Distance(this.position, at) > huntHearing(loudness, jar)
    )
      return false;
    this.state = "investigating";
    this.target = new Vector3(at.x, this.arena.floor, at.z);
    this.points = [];
    this.repath = 0;
    this.search = 4;
    return true;
  }
  /** Sight is supplied by the rendered level's occlusion ray, never through walls or upstairs. */
  update(dt: number, sora: Vector3, openLamp: boolean, visible: boolean): void {
    let left = Math.max(0, dt);
    while (left > 1e-8 && this.active) {
      const step = Math.min(left, 0.05);
      left -= step;
      this.elapsed += step;
      // She comes after Sora into the other arena.
      const where = arenaAt(sora);
      if (where && where !== this.arena) {
        this.away += step;
        if (this.away >= ROAMER_FOLLOWS_AFTER) this.enter(where);
        continue;
      }
      this.away = 0;
      const here = where === this.arena;
      const distance = Vector3.Distance(this.position, sora);
      const seen = here && visible && distance <= (openLamp ? 10 : 1.5);
      if (seen) {
        this.state = "chasing";
        this.target = new Vector3(sora.x, this.arena.floor, sora.z);
        this.memory = 2.5;
        this.search = 4;
      } else if (this.state === "chasing") {
        this.memory -= step;
        if (this.memory <= 0) this.state = "investigating";
      }
      if (this.contact(sora)) {
        this.state = "caught";
        return;
      }
      const route = this.arena.route;
      this.repath -= step;
      if (this.repath <= 0) {
        this.points = this.navigation.path(this.position, this.target ?? route[this.route]);
        this.destination = this.points.at(-1)?.clone() ?? this.position.clone();
        this.repath = 0.4;
      }
      const arrived =
        !this.points.length ||
        (!!this.destination && Vector3.Distance(this.position, this.destination) < 0.05);
      if (arrived) {
        if (this.target) {
          this.search -= step;
          if (this.search <= 0) {
            this.target = null;
            this.state = "patrol";
            this.points = [];
            this.repath = 0;
          }
        } else {
          this.route = (this.route + 1) % route.length;
          this.points = [];
          this.repath = 0;
        }
      } else {
        const to = this.points[0].subtract(this.position),
          length = to.length();
        const travel = step * (this.state === "chasing" ? ROAMER_CHASE_SPEED : ROAMER_PATROL_SPEED);
        if (length > 0.001) {
          this.direction.copyFrom(to).normalize();
          const next = this.position.add(to.scale(Math.min(1, travel / length)));
          if (this.navigation.clear(this.position, next)) this.position.copyFrom(next);
          else this.points = [];
        }
        if (length <= travel + 0.001) this.points.shift();
      }
      if (this.contact(sora)) {
        this.state = "caught";
        return;
      }
    }
  }
  private contact(sora: Vector3): boolean {
    return (
      arenaAt(sora) === this.arena &&
      Math.abs(sora.y - this.arena.floor) < 0.7 &&
      Vector3.Distance(this.position, sora) < 0.72 &&
      this.navigation.clear(this.position, new Vector3(sora.x, this.arena.floor, sora.z), 0.01)
    );
  }
}
