import { describe, expect, it } from "vitest";
import { Breath, gardenClear, gardenPath, PretBrain } from "@/episodes/ep2/PretBrain";
import { ANCESTORS, GARDEN_OBSTACLES, PATROLS, STUPAS } from "@/episodes/ep2/data/pagoda";
import { Lamp } from "@/systems/lamp/Lamp";

describe("Pret hearing and navigation", () => {
  it("keeps the clustered cemetery connected to every offering and patrol waypoint", () => {
    const start = { x: -14, z: 12 };
    for (const goal of [...PATROLS.flat(), ...ANCESTORS.map((a) => ({ x: a.x, z: a.z + 2 }))]) {
      if (goal.x === start.x && goal.z === start.z) continue;
      const path = gardenPath(start, goal);
      expect(path.length, JSON.stringify(goal)).toBeGreaterThan(0);
      const end = path.at(-1)!;
      expect(Math.hypot(end.x - goal.x, end.z - goal.z)).toBeLessThan(1.5);
      for (const point of path)
        expect(
          GARDEN_OBSTACLES.some(
            (o) => Math.abs(o.x - point.x) < 1.05 && Math.abs(o.z - point.z) < 1.05,
          ),
        ).toBe(false);
    }
  });
  it("routes sound investigations around physical stupas", () => {
    const path = gardenPath({ x: -14, z: 10 }, { x: 14, z: -12 });
    expect(path.length).toBeGreaterThan(30);
    for (const p of path) {
      expect(gardenClear(p)).toBe(true);
      expect(STUPAS.some((s) => Math.abs(s.x - p.x) < 1.05 && Math.abs(s.z - p.z) < 1.05)).toBe(
        false,
      );
    }
    for (let i = 1; i < path.length; i++)
      expect(Math.abs(path[i].x - path[i - 1].x) + Math.abs(path[i].z - path[i - 1].z)).toBe(1);
  });
  it("hears loud footsteps further away, listens, and returns to its patrol", () => {
    const p = new PretBrain(PATROLS[0]);
    expect(p.hear({ x: -14, z: -1 }, 0.1)).toBe(false);
    expect(p.hear({ x: -14, z: -1 }, 1)).toBe(true);
    expect(p.mode).toBe("listen");
    p.update(0.8);
    expect(p.mode).toBe("investigate");
    for (let i = 0; i < 100; i++) p.update(0.1);
    expect(p.mode).toBe("patrol");
    expect(gardenClear(p.position)).toBe(true);
  });
  it("keeps approaching through repeated footsteps instead of restarting its listening pause", () => {
    // Steps on leaves, short of the loud sounds that set it running (see below).
    const p = new PretBrain(PATROLS[0]);
    p.hear({ x: -14, z: 1 }, 0.9);
    p.update(0.8);
    const before = p.position.z;
    for (let i = 0; i < 10; i++) {
      p.hear({ x: -14, z: 1 }, 0.9);
      p.update(0.1);
    }
    expect(p.mode).toBe("investigate");
    expect(before - p.position.z).toBeGreaterThan(1);
  });
  it("snaps round at a loud sound close by and comes at a run, then slows to a search", () => {
    const p = new PretBrain(PATROLS[0]);
    const near = { x: p.position.x + 6, z: p.position.z };
    p.hear(near, 1.3);
    expect(p.mode).toBe("listen");
    p.update(0.35);
    expect(p.mode).toBe("rush");
    const start = { ...p.position };
    for (let i = 0; i < 30; i++) p.update(1 / 30);
    expect(Math.hypot(p.position.x - start.x, p.position.z - start.z)).toBeGreaterThan(2);
    for (let i = 0; i < 40; i++) p.update(0.1);
    expect(p.mode).toBe("investigate");
  });
  it("only walks to a quiet sound, even close by", () => {
    const p = new PretBrain(PATROLS[0]);
    p.hear({ x: p.position.x + 5, z: p.position.z }, 0.35);
    p.update(1);
    expect(p.mode).toBe("investigate");
  });
  it("does not use visibility or the lantern to detect a quiet player", () => {
    const p = new PretBrain(PATROLS[0]);
    expect(p.hear({ x: p.position.x + 4, z: p.position.z }, 0)).toBe(false);
    expect(p.catches({ x: p.position.x + 0.5, z: p.position.z })).toBe(true);
    expect(p.catches({ x: p.position.x + 1.5, z: p.position.z })).toBe(false);
  });
  it("allows six seconds of silence, then one gasp until released and recovered", () => {
    const b = new Breath();
    expect(b.update(5, true)).toBe(false);
    expect(b.holding).toBe(true);
    expect(b.update(1, true)).toBe(true);
    expect(b.holding).toBe(false);
    expect(b.update(4, true)).toBe(false);
    b.update(4, false);
    expect(b.update(1, true)).toBe(false);
    expect(b.holding).toBe(true);
  });
  it("keeps shuttered oil consumption and does not relight an extinguished lamp", () => {
    const lamp = new Lamp(undefined, 1, "open");
    lamp.toggleShutter();
    expect(lamp.state).toBe("shuttered");
    lamp.update(72);
    expect(lamp.oil).toBeCloseTo(0.9);
    lamp.toggleShutter();
    expect(lamp.state).toBe("open");
    lamp.putOut();
    lamp.toggleShutter();
    expect(lamp.state).toBe("out");
  });
});
