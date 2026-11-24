import { Vector3 } from "@babylonjs/core/Maths/math.vector";

/** Fixed simulation step for the Krasue's hair and viscera (s). */
export const STRAND_STEP = 1 / 120;

export interface StrandSpec {
  /** Pull back toward the sculpted rest shape, per joint, 1/s² (joint 0 is pinned). */
  stiffness: readonly number[];
  /** Air drag, 1/s: how quickly a joint's own swing dies away. */
  drag: number;
  /** Extra downward pull, m/s². */
  gravity: number;
  /** Strength of the night air's gusts, m/s², growing toward the tip. */
  wind: number;
  /** How far each joint may stray from its rest place, m... */
  slack: readonly number[];
  /** ...and at most this fraction of its distance from the root (a short strand stays short). */
  slackRatio?: number;
  /** Puts each strand's gusts out of step with its neighbours'. */
  seed: number;
}

/**
 * One hanging or streaming chain (a lock of hair, the string of viscera): Verlet points
 * in world space pinned at the root, pulled toward the rest shape the head (or the
 * throat) carries, dragged by the air, nudged by gusts, kept at their lengths. Moving the
 * root through the air is what makes the rest trail, swing and settle.
 */
export class Strand {
  readonly points: Vector3[];
  private readonly previous: Vector3[];
  private readonly lengths: number[];
  private readonly leash: number[];
  private fresh = true;
  private readonly scratch = new Vector3();
  private readonly step = new Vector3();

  constructor(
    count: number,
    private readonly spec: StrandSpec,
  ) {
    this.points = Array.from({ length: count }, () => new Vector3());
    this.previous = Array.from({ length: count }, () => new Vector3());
    this.lengths = new Array<number>(count).fill(0);
    this.leash = new Array<number>(count).fill(0);
  }

  get count(): number {
    return this.points.length;
  }

  /** Puts every point on its rest place, at rest (a teleport, a first sight). */
  reset(targets: readonly Vector3[]): void {
    const { slack, slackRatio = Infinity } = this.spec;
    let along = 0;
    for (let i = 0; i < this.points.length; i++) {
      this.points[i].copyFrom(targets[i]);
      this.previous[i].copyFrom(targets[i]);
      this.lengths[i] = i ? Vector3.Distance(targets[i], targets[i - 1]) : 0;
      along += this.lengths[i];
      this.leash[i] = Math.min(slack[Math.min(i, slack.length - 1)], along * slackRatio);
    }
    this.fresh = false;
  }

  /** Advances one fixed step of `h` seconds; `targets` are the rest places now. */
  advance(h: number, time: number, targets: readonly Vector3[]): void {
    if (this.fresh) this.reset(targets);
    const { stiffness, drag, gravity, wind, seed } = this.spec;
    const keep = Math.exp(-drag * h);
    const n = this.points.length;
    this.points[0].copyFrom(targets[0]);
    this.previous[0].copyFrom(targets[0]);
    for (let i = 1; i < n; i++) {
      const p = this.points[i],
        q = this.previous[i];
      const k = stiffness[Math.min(i, stiffness.length - 1)];
      const tip = i / (n - 1);
      const a = wind * tip;
      // Gusts: a few slow, unrelated waves per axis, never a single clean sine.
      const gx =
        Math.sin(time * 1.3 + seed * 1.7 + i * 0.6) + 0.5 * Math.sin(time * 2.9 + seed * 0.4 - i);
      const gy = 0.45 * Math.sin(time * 1.1 + seed * 2.3 + i * 0.4);
      const gz =
        Math.sin(time * 1.7 + seed * 0.9 + i * 0.7) + 0.5 * Math.sin(time * 3.3 + seed * 1.1);
      this.step.copyFrom(p).subtractInPlace(q).scaleInPlace(keep);
      q.copyFrom(p);
      this.scratch.copyFrom(targets[i]).subtractInPlace(p).scaleInPlace(k);
      this.scratch.addInPlaceFromFloats(a * gx, a * gy - gravity, a * gz);
      p.addInPlace(this.step).addInPlace(this.scratch.scaleInPlace(h * h));
    }
    // Lengths, from the root out (the root does not give), then the leash.
    for (let i = 1; i < n; i++) {
      const p = this.points[i];
      this.scratch.copyFrom(p).subtractInPlace(this.points[i - 1]);
      const len = this.scratch.length();
      if (len > 1e-6)
        p.copyFrom(this.points[i - 1]).addInPlace(this.scratch.scaleInPlace(this.lengths[i] / len));
      this.scratch.copyFrom(p).subtractInPlace(targets[i]);
      const off = this.scratch.length(),
        max = this.leash[i];
      if (off > max) p.copyFrom(targets[i]).addInPlace(this.scratch.scaleInPlace(max / off));
    }
  }
}

/**
 * The flight itself, smoothed: a critically damped follow of the brain's point that
 * also tracks its velocity, so a steady glide has no lag, and every start, stop and turn
 * (the brain's patrol reverses, freezes when it sees Sora, bolts away) becomes an
 * acceleration a body could make: braking from a glide it drifts on a little (about
 * speed / (e * omega)) and settles back. Also gives that acceleration, which leans and
 * banks it.
 */
export class KrasueGlide {
  readonly position = new Vector3();
  readonly velocity = new Vector3();
  readonly acceleration = new Vector3();
  private readonly last = new Vector3();
  private readonly lead = new Vector3();
  private started = false;

  constructor(
    /** Response, rad/s: about how quickly it answers a change of course. */
    private readonly omega = 7,
  ) {}

  reset(at: Vector3): void {
    this.position.copyFrom(at);
    this.last.copyFrom(at);
    this.velocity.setAll(0);
    this.acceleration.setAll(0);
    this.lead.setAll(0);
    this.started = true;
  }

  /** `omega` overrides the response for this frame (a charge answers faster). */
  update(dt: number, target: Vector3, omega = this.omega): void {
    if (!this.started || dt <= 0 || Vector3.Distance(target, this.last) > 6) {
      this.reset(target);
      return;
    }
    // The brain's own velocity, lightly filtered (its steps are uneven frame to frame).
    const from = this.last.clone();
    const raw = target.subtract(from).scaleInPlace(1 / dt);
    this.lead.addInPlace(raw.subtractInPlace(this.lead).scaleInPlace(1 - Math.exp(-dt * 30)));
    this.last.copyFrom(target);
    const w = omega;
    const span = Math.min(dt, 0.1);
    let elapsed = 0;
    this.acceleration.setAll(0);
    let steps = 0;
    const goal = new Vector3();
    while (span - elapsed > 1e-6) {
      const h = Math.min(STRAND_STEP, span - elapsed);
      // Where the brain was at this moment of the frame, not only where it ended.
      Vector3.LerpToRef(from, target, elapsed / span, goal);
      elapsed += h;
      const ax = w * w * (goal.x - this.position.x) + 2 * w * (this.lead.x - this.velocity.x);
      const ay = w * w * (goal.y - this.position.y) + 2 * w * (this.lead.y - this.velocity.y);
      const az = w * w * (goal.z - this.position.z) + 2 * w * (this.lead.z - this.velocity.z);
      this.velocity.addInPlaceFromFloats(ax * h, ay * h, az * h);
      this.position.addInPlace(this.velocity.scale(h));
      this.acceleration.addInPlaceFromFloats(ax, ay, az);
      steps++;
    }
    if (steps) this.acceleration.scaleInPlace(1 / steps);
  }
}
