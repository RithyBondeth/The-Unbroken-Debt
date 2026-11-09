import { describe, expect, it } from "vitest";
import {
  KmaochHaunts,
  behind,
  type HauntEvent,
  type HauntScene,
} from "@/episodes/ep2/KmaochHaunts";
import { PretBrain, speedFor } from "@/episodes/ep2/PretBrain";
import { gaitFor } from "@/episodes/ep2/ShroudedDead";
import { PAGODA_BALANCE as B } from "@/episodes/ep2/data/balance";
import type { Point } from "@/episodes/ep2/data/pagoda";

/** A straight line to anywhere: open ground. */
const straight = (_from: Point, to: Point) => [{ ...to }];

function brain(at: Point, crawls = false): PretBrain {
  const b = new PretBrain([at, { x: at.x + 4, z: at.z }], 0, crawls);
  b.pathfinder = straight;
  return b;
}

function scene(over: Partial<HauntScene> = {}): HauntScene {
  return {
    feet: { x: 0, z: 0 },
    yaw: 0, // facing +Z
    still: 0,
    safe: false,
    walkable: () => true,
    clear: () => true,
    ...over,
  };
}

/** How Sora at `s` sees `b`. */
function viewer(s: HauntScene, brains: PretBrain[]) {
  return (i: number) => {
    const p = brains[i].position;
    const dx = p.x - s.feet.x,
      dz = p.z - s.feet.z,
      distance = Math.hypot(dx, dz) || 1;
    return { facing: (Math.sin(s.yaw) * dx + Math.cos(s.yaw) * dz) / distance, distance };
  };
}

function run(
  h: KmaochHaunts,
  s: HauntScene,
  brains: PretBrain[],
  seconds: number,
  step = (dt: number) => brains.forEach((b) => b.update(dt)),
): HauntEvent[] {
  const events: HauntEvent[] = [];
  for (let t = 0; t < seconds; t += 1 / 30) {
    events.push(...h.update(1 / 30, s, brains, () => true, viewer(s, brains)));
    step(1 / 30);
  }
  return events;
}

describe("kmaoch hauntings", () => {
  it("puts a point straight behind her", () => {
    const p = behind({ x: 1, z: 1 }, 0, 3);
    expect(p.x).toBeCloseTo(1);
    expect(p.z).toBeCloseTo(-2);
  });

  it("sends one she cannot see after her, and it closes to the gap behind her", () => {
    const h = new KmaochHaunts(() => 0);
    const b = brain({ x: 0, z: -18 }); // straight behind her
    const s = scene();
    const events = run(h, s, [b], 45);
    expect(events.some((e) => e.kind === "stalk")).toBe(true);
    expect(h.following).toBe(0);
    expect(Math.hypot(b.position.x, b.position.z)).toBeLessThan(B.stalkGap + 1);
    expect(b.catches(s.feet)).toBe(false);
  });

  it("holds the one following her still while she looks at it", () => {
    const h = new KmaochHaunts(() => 0);
    const b = brain({ x: 0, z: -18 });
    const s = scene();
    run(h, s, [b], 50.5);
    expect(h.following).toBe(0);
    s.yaw = Math.PI; // she turns round
    const before = { ...b.position };
    run(h, s, [b], 2);
    expect(Math.hypot(b.position.x - before.x, b.position.z - before.z)).toBeLessThan(0.05);
  });

  it("lets a vanished follower go home", () => {
    const h = new KmaochHaunts(() => 0);
    const b = brain({ x: 0, z: -18 });
    const s = scene();
    run(h, s, [b], 40);
    h.vanished(0, [b]);
    expect(h.following).toBe(-1);
    expect(b.mode).toBe("patrol");
    expect(b.position.z).toBeCloseTo(-18);
  });

  it("puts one just behind her when she stands still, gone when she turns", () => {
    const h = new KmaochHaunts(() => 0);
    const b = brain({ x: 20, z: -20 });
    const s = scene({ still: 10 });
    const freeze = () => {};
    let events = run(h, s, [b], 45, freeze);
    const loom = events.find((e) => e.kind === "loom");
    expect(loom).toBeDefined();
    expect(h.looming).toBe(0);
    expect(b.mode).toBe("loom");
    expect(b.position.z).toBeCloseTo(-2.3);
    expect(b.catches(s.feet)).toBe(false);
    // She turns: its neck goes, it lunges (never into a catch) and it is gone.
    s.yaw = Math.PI;
    let nearest = 99;
    events = [];
    for (let t = 0; t < 1.2; t += 1 / 30) {
      events.push(...h.update(1 / 30, s, [b], () => true, viewer(s, [b])));
      if (h.looming === 0) nearest = Math.min(nearest, Math.hypot(b.position.x, b.position.z));
    }
    expect(events.map((e) => e.kind)).toEqual(["turn", "gone"]);
    expect(events[1]).toMatchObject({ seen: true });
    expect(nearest).toBeGreaterThan(B.catchRadius);
    expect(nearest).toBeLessThan(2.2);
    expect(h.looming).toBe(-1);
    expect(b.position).toMatchObject({ x: 20, z: -20 });
  });

  it("never puts one behind her in the kuti, or where it could not stand", () => {
    const b = brain({ x: 20, z: -20 });
    expect(
      run(new KmaochHaunts(() => 0), scene({ still: 10, safe: true }), [b], 90, () => {}),
    ).toEqual([]);
    expect(
      run(
        new KmaochHaunts(() => 0),
        scene({ still: 10, walkable: () => false }),
        [b],
        90,
        () => {},
      ).some((e) => e.kind === "loom"),
    ).toBe(false);
  });

  it("crawls slower about and scuttles when it hears", () => {
    expect(speedFor("patrol", true)).toBeLessThan(speedFor("patrol", false));
    expect(speedFor("rush", true)).toBeGreaterThan(speedFor("patrol", true) * 3);
    expect(gaitFor(true, "patrol", true)).toBe("crawl");
    expect(gaitFor(false, "listen", true)).toBe("low");
    expect(gaitFor(true, "stalk")).toBe("lurch");
    expect(gaitFor(true, "patrol")).toBe("walk");
  });
});
