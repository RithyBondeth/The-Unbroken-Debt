import { describe, expect, it } from "vitest";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import {
  KrasueGlide,
  STRAND_STEP,
  Strand,
  type StrandSpec,
} from "@/episodes/ep1/entities/krasueMotion";

const STILL: StrandSpec = {
  stiffness: [0, 40, 25, 15],
  drag: 2,
  gravity: 0,
  wind: 0,
  slack: [0, 0.1, 0.2, 0.3],
  seed: 1,
};
/** A lock streaming straight out sideways (+X) from a root that has moved `z` forward. */
const rest = (z: number) => [0, 0.1, 0.2, 0.3].map((d) => new Vector3(d, 1, z));

function run(strand: Strand, seconds: number, at: (t: number) => number, start = 0): number {
  let t = start;
  for (let i = 0; i < Math.round(seconds / STRAND_STEP); i++) {
    t += STRAND_STEP;
    strand.advance(STRAND_STEP, t, rest(at(t)));
  }
  return t;
}

describe("Krasue strands", () => {
  it("hold their rest shape when nothing moves them", () => {
    const s = new Strand(4, STILL);
    run(s, 2, () => 0);
    rest(0).forEach((p, i) => expect(Vector3.Distance(s.points[i], p)).toBeLessThan(1e-6));
  });

  it("trail behind a moving root at their own lengths, within their slack", () => {
    const s = new Strand(4, STILL);
    run(s, 0.5, () => 0);
    // The root glides off across the lock at 3 m/s.
    const t = run(s, 0.4, (t) => (t - 0.5) * 3, 0.5);
    const targets = rest((t - 0.5) * 3);
    expect(s.points[3].z).toBeLessThan(targets[3].z - 0.02);
    for (let i = 1; i < 4; i++) {
      expect(Vector3.Distance(s.points[i], s.points[i - 1])).toBeCloseTo(0.1, 4);
      expect(Vector3.Distance(s.points[i], targets[i])).toBeLessThanOrEqual(STILL.slack[i] + 1e-6);
    }
  });

  it("swing on after the root stops, then settle", () => {
    const s = new Strand(4, STILL);
    run(s, 0.3, () => 0);
    let t = run(s, 0.3, (t) => (t - 0.3) * 2, 0.3);
    const stop = (t - 0.3) * 2;
    const off: number[] = [];
    for (let i = 0; i < 120; i++) {
      t = run(s, STRAND_STEP * 2, () => stop, t);
      off.push(s.points[3].z - rest(stop)[3].z);
    }
    // It passes its rest place (it swings) ...
    expect(Math.max(...off)).toBeGreaterThan(0.002);
    expect(Math.min(...off)).toBeLessThan(-0.002);
    // ... and comes to rest.
    run(s, 4, () => stop, t);
    expect(Math.abs(s.points[3].z - rest(stop)[3].z)).toBeLessThan(0.003);
  });

  it("sway in the gusts and sag under their weight, but never come apart", () => {
    const s = new Strand(4, { ...STILL, wind: 2, gravity: 1.5 });
    const seen: number[] = [];
    let t = 0;
    for (let i = 0; i < 400; i++) {
      t = run(s, STRAND_STEP * 3, () => 0, t);
      seen.push(s.points[3].x + s.points[3].z);
      for (const p of s.points) expect(Number.isFinite(p.x + p.y + p.z)).toBe(true);
    }
    expect(Math.max(...seen) - Math.min(...seen)).toBeGreaterThan(0.01);
    expect(s.points[3].y).toBeLessThan(1);
  });
});

describe("Krasue glide", () => {
  it("follows a steady flight with no lag and smooths a dead stop", () => {
    const g = new KrasueGlide();
    const target = new Vector3();
    g.update(1 / 60, target);
    for (let i = 0; i < 120; i++) {
      target.x += 2 / 60;
      g.update(1 / 60, target);
    }
    expect(Math.abs(g.position.x - target.x)).toBeLessThan(0.01);
    expect(g.velocity.x).toBeCloseTo(2, 1);
    // The brain freezes as it sees Sora: the body brakes over a moment, not in a frame,
    // drifting on a hand's breadth before it settles back.
    let peak = 0,
      overshoot = 0;
    for (let i = 0; i < 90; i++) {
      g.update(1 / 60, target);
      peak = Math.max(peak, g.acceleration.length());
      overshoot = Math.max(overshoot, g.position.x - target.x);
    }
    expect(peak).toBeLessThan(40);
    expect(overshoot).toBeLessThan(0.16);
    expect(Math.abs(g.position.x - target.x)).toBeLessThan(0.02);
  });

  it("answers a charge faster, drifting less", () => {
    const drift = (omega: number) => {
      const g = new KrasueGlide();
      const target = new Vector3();
      g.update(1 / 60, target);
      for (let i = 0; i < 60; i++) {
        target.x += 6 / 60;
        g.update(1 / 60, target, omega);
      }
      let most = 0;
      for (let i = 0; i < 60; i++) {
        g.update(1 / 60, target, omega);
        most = Math.max(most, g.position.x - target.x);
      }
      return most;
    };
    expect(drift(13)).toBeLessThan(drift(7) * 0.65);
    expect(drift(13)).toBeLessThan(0.25);
  });

  it("jumps with a teleport instead of flying across the fields", () => {
    const g = new KrasueGlide();
    g.update(1 / 60, new Vector3());
    g.update(1 / 60, new Vector3(30, 7, 0));
    expect(g.position.x).toBe(30);
    expect(g.velocity.length()).toBe(0);
  });
});
