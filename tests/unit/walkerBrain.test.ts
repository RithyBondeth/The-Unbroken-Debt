import { describe, expect, it } from "vitest";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { WalkerBrain } from "../../src/episodes/ep1/act2/WalkerBrain";
import {
  doorwayPath,
  hearingRadius,
  throughDoorways,
  WALKER_ROUTE,
} from "../../src/episodes/ep1/data/walker";

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
    walker.position.set(-1, 2.5, -13.45);
    expect(walker.hear(new Vector3(-4.5, 2.5, -15.2), 0.35, false)).toBe(true);
    walker.update(1, distant, false);
    expect(walker.position.z).toBeCloseTo(-13.45);
    expect(doorwayPath(new Vector3(-4.5, 2.5, -15.2), new Vector3(-1, 2.5, -15))[0].z).toBe(-13.45);
    walker.update(90, distant, false);
    expect(walker.state).toBe("complete");
  });
  it("does not catch through a solid partition", () => {
    expect(throughDoorways(new Vector3(-2.7, 2.5, -15), new Vector3(-3.5, 2.5, -15))).toBe(false);
    expect(throughDoorways(new Vector3(-2.7, 2.5, -13.45), new Vector3(-3.5, 2.5, -13.45))).toBe(
      true,
    );
  });
});
