import { describe, expect, it } from "vitest";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Flags } from "@/core/Flags";
import { Inventory } from "@/systems/inventory/Inventory";
import { HuntProgress } from "@/episodes/ep1/act3/HuntProgress";
import { HuntNavigation } from "@/episodes/ep1/act3/HuntNavigation";
import { RoamerBrain } from "@/episodes/ep1/act3/RoamerBrain";
import {
  JARS,
  ROAMER_ROUTE,
  FRAGMENT_IDS,
  CP5_FEET,
  BARN_ARENA,
  BARN_FLOOR,
  BARN_ROUTE,
  ROAMER_FOLLOWS_AFTER,
  arenaAt,
} from "@/episodes/ep1/data/hunt";

function setup() {
  const flags = new Flags(),
    inventory = new Inventory();
  flags.set("ep1.act3.started", true);
  flags.set("ep1.hunt.started", true);
  return { flags, inventory, p: new HuntProgress(flags, inventory) };
}
describe("under-house durable progress", () => {
  it("requires Act III and an opened jar, grants each authored content once", () => {
    const { flags, inventory, p } = setup();
    flags.set("ep1.act3.started", false);
    expect(p.open("J1")).toBe(false);
    flags.set("ep1.act3.started", true);
    expect(p.take("J2")).toBe(false);
    expect(p.open("missing")).toBe(false);
    for (const j of JARS) {
      expect(p.open(j.id)).toBe(true);
      expect(p.open(j.id)).toBe(false);
      expect(p.take(j.id)).toBe(true);
      expect(p.take(j.id)).toBe(false);
    }
    expect(p.pieces).toBe(3);
    expect(inventory.count("oil")).toBe(1);
    expect(inventory.has("barn_gate_key")).toBe(true);
    expect(flags.get("ep1.lore", 0)).toBe(1);
    expect(flags.get("ep1.fragments.3", false)).toBe(true);
  });
  it("restores partial jar searches and assembles exactly once without consuming incomplete pieces", () => {
    const original = setup();
    original.p.open("J2");
    original.p.take("J2");
    original.p.open("J4");
    const { flags, inventory, p } = setup();
    flags.load(original.flags.toJSON());
    inventory.load(original.inventory.toJSON());
    expect(p.take("J2")).toBe(false);
    expect(p.pieces).toBe(1);
    expect(p.assemble()).toBe(false);
    expect(p.pieces).toBe(1);
    expect(p.take("J4")).toBe(true);
    p.open("J6");
    p.take("J6");
    expect(p.assemble()).toBe(true);
    expect(p.assemble()).toBe(false);
    expect(inventory.count("brass_key")).toBe(1);
    for (const id of FRAGMENT_IDS) expect(inventory.has(id)).toBe(false);
    expect(p.take("J6")).toBe(false);
    const restored = setup();
    restored.flags.load(flags.toJSON());
    restored.inventory.load(inventory.toJSON());
    expect(restored.p.assembled).toBe(true);
    expect(restored.p.assemble()).toBe(false);
  });
});
describe("under-house obstacle navigation", () => {
  const nav = new HuntNavigation();
  it("routes every patrol leg and jar approach around posts, jars and storage", () => {
    for (const from of ROAMER_ROUTE) {
      expect(nav.walkable(from), String(from)).toBe(true);
      // The jars under the house (the barn's two are reached by its own ground).
      for (const to of [...ROAMER_ROUTE, ...JARS.filter((j) => j.at.y < 0.5).map((j) => j.at)]) {
        const path = nav.path(from, to);
        expect(path.length, `${String(from)} → ${String(to)}`).toBeGreaterThan(0);
        let last = from;
        for (const point of path) {
          expect(nav.clear(last, point), `${String(last)} → ${String(point)}`).toBe(true);
          last = point;
        }
        expect(Vector3.Distance(last, to)).toBeLessThan(1);
      }
    }
  });
  it("blocks direct shortcuts through a stilt", () => {
    expect(nav.clear(new Vector3(-4.35, 0, -25), new Vector3(-4.35, 0, -27))).toBe(false);
  });
});
describe("under-house roamer senses", () => {
  it("hears crouch within 3m, walk within 8m, hurry within 10m and jars within 7m", () => {
    for (const [noise, jar, distance, heard] of [
      [0.12, false, 2.9, true],
      [0.12, false, 3.1, false],
      [0.35, false, 7.9, true],
      [0.35, false, 8.1, false],
      [1, false, 9, true],
      [0.6, true, 6.9, true],
      [0.6, true, 7.1, false],
    ] as const) {
      const b = new RoamerBrain();
      b.start();
      b.position.set(-6, 0, -28);
      expect(b.hear(new Vector3(-6 + distance, 0, -28), noise, jar)).toBe(heard);
    }
    const b = new RoamerBrain();
    b.start();
    expect(b.hear(new Vector3(0, 2.5, -28), 1)).toBe(false);
  });
  it("tracks exposed lamplight, loses an occluded target and returns from a blocked jar center", () => {
    const b = new RoamerBrain();
    b.start();
    b.position.set(-2.5, 0, -28);
    const sora = new Vector3(2.5, 0, -28);
    b.update(0.1, sora, false, true);
    expect(b.state).toBe("patrol");
    b.update(0.1, sora, true, false);
    expect(b.state).toBe("patrol");
    b.update(0.1, sora, true, true);
    expect(b.state).toBe("chasing");
    b.update(3, CP5_FEET, false, false);
    expect(b.state).toBe("investigating");
    b.start();
    expect(b.hear(JARS[2].at, 1, true)).toBe(true);
    b.update(30, CP5_FEET, false, false);
    expect(b.state).toBe("patrol");
  });
  it("does not catch through a jar, upstairs or outside the hunt; catches nearby ground targets", () => {
    const b = new RoamerBrain();
    b.start();
    // Either side of jar J2 (2.6, -28.2).
    b.position.set(2.6, 0, -28.9);
    b.update(0.05, new Vector3(2.6, 0, -27.5), false, false);
    expect(b.state).not.toBe("caught");
    b.position.set(1, 0, -28);
    b.update(0.05, new Vector3(1, 2.5, -28), true, true);
    expect(b.state).not.toBe("caught");
    b.position.set(-1, 0, -22.2);
    b.update(0.05, CP5_FEET, true, true);
    expect(b.state).not.toBe("caught");
    b.position.set(-2, 0, -28);
    b.update(0.05, new Vector3(-1.7, 0, -28), false, false);
    expect(b.state).toBe("caught");
  });
  it("patrols continuously without entering obstacles, independent of frame size", () => {
    const a = new RoamerBrain(),
      b = new RoamerBrain();
    a.start();
    b.start();
    for (let i = 0; i < 1200; i++) {
      a.update(0.05, CP5_FEET, false, false);
      expect(a.navigation.walkable(a.position)).toBe(true);
    }
    for (let i = 0; i < 300; i++) b.update(0.2, CP5_FEET, false, false);
    expect(Vector3.Distance(a.position, b.position)).toBeLessThan(0.01);
    expect(Vector3.Distance(a.position, ROAMER_ROUTE[0])).toBeGreaterThan(1);
  });
});

describe("the rice barn's part of the hunt", () => {
  const barnFloor = (x: number, z: number) => new Vector3(x, BARN_FLOOR, z);
  it("routes every barn patrol leg and jar approach round the bins, sacks and ladder", () => {
    const nav = new HuntNavigation(BARN_ARENA);
    for (const p of BARN_ROUTE) expect(nav.walkable(p)).toBe(true);
    for (const from of BARN_ROUTE)
      for (const to of [...BARN_ROUTE, ...JARS.filter((j) => j.at.y > 0.5).map((j) => j.at)]) {
        const path = nav.path(from, to);
        expect(path.length).toBeGreaterThan(0);
        let at = from;
        for (const next of path) {
          expect(nav.clear(at, next, 0.3)).toBe(true);
          at = next;
        }
      }
  });
  it("puts the barn's floor and the ground under the back block in their own arenas", () => {
    expect(arenaAt(new Vector3(0, 0, -27))?.id).toBe("house");
    expect(arenaAt(CP5_FEET)).toBeNull(); // CP5: at the funeral's edge, outside
    expect(arenaAt(barnFloor(-25, -22.5))?.id).toBe("barn");
    expect(arenaAt(new Vector3(-25, 0, -22.5))).toBeNull(); // under the barn's floor
    expect(arenaAt(new Vector3(-16, 0, -22.5))).toBeNull(); // the barn yard
  });
  it("comes after Sora into the barn, neither hearing nor catching across arenas", () => {
    const b = new RoamerBrain();
    b.start();
    const sora = barnFloor(-24.5, -22.3);
    expect(b.hear(sora, 1)).toBe(false);
    b.update(ROAMER_FOLLOWS_AFTER - 0.5, sora, true, true);
    expect(b.arena.id).toBe("house");
    expect(b.state).not.toBe("caught");
    b.update(1, sora, false, false);
    expect(b.arena.id).toBe("barn");
    expect(b.position.y).toBeCloseTo(BARN_FLOOR);
    expect(b.hear(sora, 1)).toBe(true);
    for (let i = 0; i < 400 && b.state !== "caught"; i++) b.update(0.05, sora, true, true);
    expect(b.state).toBe("caught");
  });
});
