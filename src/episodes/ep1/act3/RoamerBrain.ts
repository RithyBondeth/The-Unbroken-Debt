import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { ROAMER_ROUTE, huntHearing, inHunt } from "../data/hunt";
import { HuntNavigation } from "./HuntNavigation";

export type RoamerState = "idle" | "patrol" | "investigating" | "chasing" | "caught";
export class RoamerBrain {
  state: RoamerState = "idle";
  readonly position = ROAMER_ROUTE[0].clone();
  readonly direction = new Vector3(0, 0, 1);
  elapsed = 0;
  private route = 1;
  private points: Vector3[] = [];
  private target: Vector3 | null = null;
  private repath = 0;
  private search = 0;
  private destination: Vector3 | null = null;
  private memory = 0;
  constructor(readonly navigation = new HuntNavigation()) {}
  get active(): boolean {
    return this.state !== "idle" && this.state !== "caught";
  }
  start(): void {
    this.position.copyFrom(ROAMER_ROUTE[0]);
    this.route = 1;
    this.points = [];
    this.target = null;
    this.destination = null;
    this.repath = 0;
    this.search = 0;
    this.memory = 0;
    this.elapsed = 0;
    this.state = "patrol";
  }
  reset(): void {
    this.state = "idle";
    this.points = [];
    this.target = null;
  }
  hear(at: Vector3, loudness: number, jar = false): boolean {
    if (
      !this.active ||
      !inHunt(at) ||
      this.state === "chasing" ||
      Vector3.Distance(this.position, at) > huntHearing(loudness, jar)
    )
      return false;
    this.state = "investigating";
    this.target = new Vector3(at.x, 0, at.z);
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
      const distance = Vector3.Distance(this.position, sora);
      const seen = inHunt(sora) && visible && distance <= (openLamp ? 10 : 1.5);
      if (seen) {
        this.state = "chasing";
        this.target = new Vector3(sora.x, 0, sora.z);
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
      this.repath -= step;
      if (this.repath <= 0) {
        this.points = this.navigation.path(this.position, this.target ?? ROAMER_ROUTE[this.route]);
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
          this.route = (this.route + 1) % ROAMER_ROUTE.length;
          this.points = [];
          this.repath = 0;
        }
      } else {
        const to = this.points[0].subtract(this.position),
          length = to.length();
        const travel = step * (this.state === "chasing" ? 2.4 : 1.3);
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
      inHunt(sora) &&
      Math.abs(sora.y) < 0.7 &&
      Vector3.Distance(this.position, sora) < 0.72 &&
      this.navigation.clear(this.position, new Vector3(sora.x, 0, sora.z), 0.01)
    );
  }
}
