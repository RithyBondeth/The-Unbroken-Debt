import { describe, expect, it } from "vitest";
import { KmaochDescent, type DescentEvent, type DescentScene } from "@/episodes/ep2/KmaochDescent";
import { measureTrunk, trunkAt, type ClimbTree } from "@/episodes/ep2/pagodaTrees";
import { PretBrain } from "@/episodes/ep2/PretBrain";
import type { Point } from "@/episodes/ep2/data/pagoda";

/** A trunk of radius `r` round (cx, cz), sampled as bark vertices up to 8 m. */
function cylinder(cx: number, cz: number, r: number): Float32Array {
  const out: number[] = [];
  for (let y = 0; y < 8; y += 0.1)
    for (let a = 0; a < 24; a++) {
      const t = (a / 24) * Math.PI * 2;
      out.push(cx + Math.cos(t) * r, y, cz + Math.sin(t) * r);
    }
  return Float32Array.from(out);
}

function tree(x: number, z: number, r = 0.4): ClimbTree {
  const points = cylinder(x, z, r);
  return { x, z, height: 12, trunk: measureTrunk(points, points.length / 3) };
}

function brain(at: Point): PretBrain {
  const b = new PretBrain([at, { x: at.x + 3, z: at.z }]);
  b.pathfinder = (_from, to) => [{ ...to }];
  return b;
}

function scene(over: Partial<DescentScene> = {}): DescentScene {
  return {
    feet: { x: 0, z: 0 },
    yaw: 0, // facing +Z
    safe: false,
    walkable: () => true,
    clear: () => true,
    ...over,
  };
}

const view = (s: DescentScene, brains: PretBrain[]) => (i: number) => {
  const p = brains[i].position;
  const dx = p.x - s.feet.x,
    dz = p.z - s.feet.z,
    d = Math.hypot(dx, dz) || 1;
  return { facing: (Math.sin(s.yaw) * dx + Math.cos(s.yaw) * dz) / d, distance: d };
};

function run(
  d: KmaochDescent,
  s: DescentScene,
  trees: ClimbTree[],
  brains: PretBrain[],
  seconds: number,
): DescentEvent[] {
  const events: DescentEvent[] = [];
  for (let t = 0; t < seconds; t += 1 / 30) {
    events.push(...d.update(1 / 30, s, trees, brains, () => true, view(s, brains)));
    brains.forEach((b) => b.update(1 / 30));
  }
  return events;
}

describe("trunks", () => {
  it("measures a trunk's middle and girth from its bark", () => {
    const t = tree(3, -2, 0.45);
    expect(t.trunk.length).toBeGreaterThan(4);
    expect(t.trunk[0].x).toBeCloseTo(3, 1);
    expect(t.trunk[0].z).toBeCloseTo(-2, 1);
    expect(t.trunk[0].r).toBeGreaterThan(0.4);
    expect(t.trunk[0].r).toBeLessThan(0.5);
    const mid = trunkAt(t, 2.7);
    expect(mid.y).toBe(2.7);
    expect(mid.r).toBeCloseTo(t.trunk[1].r, 1);
  });
});

describe("a kmaoch coming down a tree", () => {
  it("is put on a tree behind her, waits for her to look, comes down and comes at her", () => {
    const d = new KmaochDescent(() => 0);
    const trees = [tree(0, -7)]; // straight behind her
    const b = brain({ x: 0, z: -30 });
    const s = scene();
    // Turned away, nothing comes down; it scratches at the bark.
    let events = run(d, s, trees, [b], 40);
    expect(d.active).toBe(0);
    expect(b.catches(s.feet)).toBe(false);
    expect(events.some((e) => e.kind === "scratch")).toBe(true);
    expect(events.some((e) => e.kind === "down")).toBe(false);
    const pose = d.pose()!;
    expect(pose.y).toBeGreaterThan(5);
    expect(pose.flip).toBe(0);
    // On the bark facing her, not inside the trunk.
    expect(Math.hypot(pose.x - 0, pose.z + 7)).toBeGreaterThan(0.4);
    // She turns round.
    s.yaw = Math.PI;
    events = run(d, s, trees, [b], 4);
    expect(events.map((e) => e.kind)).toEqual(["down", "land", "charge"]);
    expect(b.mode).toBe("rush");
    expect(b.crawls).toBe(true);
    // It came down fast: from over five metres to the ground in about two seconds.
    expect(d.active).toBe(-1);
  });

  it("never uses a tree in front of her, where she would see it put there", () => {
    const d = new KmaochDescent(() => 0);
    const events = run(d, scene(), [tree(0, 7)], [brain({ x: 0, z: -30 })], 60);
    expect(events).toEqual([]);
    expect(d.active).toBe(-1);
  });

  it("goes back to its rounds unseen if she never looks", () => {
    const d = new KmaochDescent(() => 0);
    const b = brain({ x: 0, z: -30 });
    run(d, scene(), [tree(0, -7)], [b], 40);
    expect(d.active).toBe(0);
    run(d, scene(), [tree(0, -7)], [b], 20);
    expect(d.active).toBe(-1);
    expect(b.mode).not.toBe("loom");
  });
});
