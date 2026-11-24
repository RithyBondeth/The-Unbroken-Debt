import { describe, expect, it } from "vitest";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { WalkerBrain } from "@/episodes/ep1/act2/WalkerBrain";
import {
  doorwayPath,
  hearingRadius,
  throughDoorways,
  WALKER_ROUTE,
} from "@/episodes/ep1/data/walker";

const distant = new Vector3(25, 2.5, 25);
describe("hallway walker", () => {
  it("walks the actual stair route and pauses four seconds at Sok’s door", () => {
    const walker = new WalkerBrain();
    walker.start();
    let travel = 0;
    for (let k = 1; k <= 5; k++)
      travel += Vector3.Distance(WALKER_ROUTE[k - 1].at, WALKER_ROUTE[k].at);
    walker.update(travel + 0.15, distant, false);
    expect(walker.position.equalsWithEpsilon(WALKER_ROUTE[5].at, 0.02)).toBe(true);
    expect(walker.waiting).toBe(true);
    walker.update(3.5, distant, false);
    expect(walker.position.equalsWithEpsilon(WALKER_ROUTE[5].at, 0.02)).toBe(true);
    walker.update(1, distant, false);
    expect(walker.position.x).toBeGreaterThan(-2.49);
    walker.update(30, distant, false);
    expect(walker.state).toBe("complete");
  });
  it("ignores a quiet player beyond reach, regardless of where they look", () => {
    const walker = new WalkerBrain();
    walker.start();
    walker.update(60, distant, false);
    expect(walker.state).toBe("complete");
  });
  it("catches an exposed Sora and resets to a fresh approach", () => {
    const walker = new WalkerBrain();
    walker.start();
    walker.update(0.1, walker.position.clone(), false);
    expect(walker.state).toBe("caught");
    walker.reset();
    expect(walker.active).toBe(false);
    walker.start();
    expect(walker.elapsed).toBe(0);
    expect(walker.state).toBe("walking");
  });
  it("protects a closed, dark wardrobe unless the walker physically touches it", () => {
    const walker = new WalkerBrain();
    walker.start();
    walker.update(0.1, walker.position.add(new Vector3(0.8, 0, 0)), true);
    expect(walker.active).toBe(true);
    walker.update(0.1, walker.position.clone(), true);
    expect(walker.state).toBe("caught");
  });
  it("hears normal and crouched steps at different ranges, but never a concealed player", () => {
    expect(hearingRadius(0.12)).toBe(2);
    expect(hearingRadius(0.35)).toBe(6);
    expect(hearingRadius(1)).toBe(10);
    const walker = new WalkerBrain();
    walker.start();
    walker.position.set(0, 2.5, -13.45);
    expect(walker.hear(new Vector3(2.5, 2.5, -13.45), 0.12, false)).toBe(false);
    expect(walker.hear(new Vector3(2.5, 2.5, -13.45), 0.35, true)).toBe(false);
    expect(walker.hear(new Vector3(2.5, 0, -13.45), 0.35, false)).toBe(false);
    expect(walker.hear(new Vector3(2.5, 2.5, -13.45), 0.35, false)).toBe(true);
    expect(walker.state).toBe("investigating");
  });
  it("investigates side-room sounds through the doorway, then rejoins its route", () => {
    const walker = new WalkerBrain();
    walker.start();
    // In the hall; a sound in the parlour, east of it, behind the partition.
    walker.position.set(-1, 2.5, -13.45);
    expect(walker.hear(new Vector3(-4.5, 2.5, -12.4), 0.35, false)).toBe(true);
    // Through the parlour's door (z -15.5 .. -14.6), not the wall.
    const into = doorwayPath(new Vector3(-1, 2.5, -13.45), new Vector3(-4.5, 2.5, -12.4));
    expect(into[0].z).toBeCloseTo(-15.05);
    expect(into[into.length - 1].equalsWithEpsilon(new Vector3(-4.5, 2.5, -12.4), 1e-6)).toBe(true);
    walker.update(1, distant, false);
    expect(walker.position.z).toBeLessThan(-13.45);
    walker.update(120, distant, false);
    expect(walker.state).toBe("complete");
  });
  it("does not catch through a solid partition", () => {
    // The hall-parlour partition (x = -2.97): solid but for its door at z -15.5 .. -14.6.
    expect(throughDoorways(new Vector3(-2.7, 2.5, -13), new Vector3(-3.5, 2.5, -13))).toBe(false);
    expect(throughDoorways(new Vector3(-2.7, 2.5, -15.05), new Vector3(-3.5, 2.5, -15.05))).toBe(
      true,
    );
    // The long corridor and Sok's study through its door; his bedroom through the wall.
    expect(throughDoorways(new Vector3(0, 2.5, -25.05), new Vector3(2.5, 2.5, -25.05))).toBe(true);
    expect(throughDoorways(new Vector3(0, 2.5, -27), new Vector3(2.5, 2.5, -27))).toBe(false);
    // The nailed back door and the padlocked logs room are walls.
    expect(throughDoorways(new Vector3(0, 2.5, -33.5), new Vector3(0, 2.5, -34.5))).toBe(false);
    expect(throughDoorways(new Vector3(0, 2.5, -32.25), new Vector3(2.5, 2.5, -32.25))).toBe(false);
    // Floors don't see each other.
    expect(throughDoorways(new Vector3(0, 2.5, -15), new Vector3(0, 0, -15))).toBe(false);
  });
  it("reaches Kanha's room from Sok's study by the long corridor", () => {
    const across = doorwayPath(new Vector3(4, 2.5, -25.5), new Vector3(-4, 2.5, -25.5));
    expect(across.length).toBeGreaterThanOrEqual(2);
    for (let k = 1; k < across.length; k++)
      expect(throughDoorways(across[k - 1], across[k])).toBe(true);
    // By the corridor's doorways (its walls at x = +-0.7).
    expect(across.some((p) => Math.abs(p.x) < 1.2)).toBe(true);
    expect(throughDoorways(new Vector3(4, 2.5, -25.5), new Vector3(-4, 2.5, -25.5))).toBe(false);
  });
});
