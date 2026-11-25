import { describe, expect, it } from "vitest";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import {
  BACK_DOOR,
  HOUSE_FLOOR,
  KITCHEN_DOOR,
  LOFT_FLOOR,
  SCARES,
  backDoorTrigger,
  facing,
  kitchenTrigger,
  loftTrigger,
  scareFlag,
} from "@/episodes/ep1/data/scares";
import { JARS } from "@/episodes/ep1/data/hunt";
import { SCARE_JAR } from "@/episodes/ep1/data/scares";

/** Sora's look from `from` toward `to`, on the ground. */
const look = (from: Vector3, to: Vector3) => ({ x: to.x - from.x, z: to.z - from.z });

describe("jump scares", () => {
  it("are four (J2 taken out, Nov 25), each remembered by its own flag", () => {
    expect(SCARES).toHaveLength(4);
    expect(SCARES).not.toContain("washing");
    expect(new Set(SCARES.map(scareFlag)).size).toBe(4);
  });

  it("measure how squarely Sora faces a place", () => {
    const o = new Vector3(0, 0, 0);
    expect(facing({ x: 0, z: 1 }, o, new Vector3(0, 0, 5))).toBeCloseTo(1, 6);
    expect(facing({ x: 0, z: 1 }, o, new Vector3(0, 0, -5))).toBeCloseTo(-1, 6);
    expect(facing({ x: 1, z: 0 }, o, new Vector3(0, 0, 5))).toBeCloseTo(0, 6);
  });

  it("J1: only once the betel leaves are taken, inside the kitchen house, facing its door", () => {
    const feet = new Vector3(24.25, HOUSE_FLOOR, -16.9);
    const toDoor = look(feet, KITCHEN_DOOR);
    expect(kitchenTrigger(feet, toDoor, true)).toBe(true);
    expect(kitchenTrigger(feet, toDoor, false)).toBe(false);
    expect(kitchenTrigger(feet, { x: -toDoor.x, z: -toDoor.z }, true)).toBe(false);
    // On the walkway outside, or under the kitchen house, nothing.
    expect(kitchenTrigger(new Vector3(15, HOUSE_FLOOR, -19.15), { x: 1, z: 0 }, true)).toBe(false);
    expect(kitchenTrigger(new Vector3(24.25, 0, -16.9), toDoor, true)).toBe(false);
  });

  it("J3: Act II, at the end of the long corridor facing the nailed door", () => {
    const feet = new Vector3(0.1, HOUSE_FLOOR, -33.0);
    expect(backDoorTrigger(feet, look(feet, BACK_DOOR), true)).toBe(true);
    expect(backDoorTrigger(feet, look(feet, BACK_DOOR), false)).toBe(false);
    expect(backDoorTrigger(feet, { x: 0, z: 1 }, true)).toBe(false);
    // Halfway up the corridor it waits.
    expect(backDoorTrigger(new Vector3(0, HOUSE_FLOOR, -29), { x: 0, z: -1 }, true)).toBe(false);
  });

  it("J4 is the jar that holds the first key piece", () => {
    const jar = JARS.find((j) => j.id === SCARE_JAR);
    expect(jar?.contents).toBe("key");
    expect(jar?.at.y).toBeLessThan(0.5); // under the house, not in the barn
  });

  it("J5: Act III, climbing, once the head is over the loft's edge in the barn", () => {
    const eye = new Vector3(-25.55, LOFT_FLOOR + 0.38, -22.5);
    expect(loftTrigger(eye, true, true)).toBe(true);
    expect(loftTrigger(eye, false, true)).toBe(false);
    expect(loftTrigger(eye, true, false)).toBe(false);
    expect(loftTrigger(new Vector3(-25.55, LOFT_FLOOR - 0.4, -22.5), true, true)).toBe(false);
    // Another ladder (the kitchen house's) does not count.
    expect(loftTrigger(new Vector3(29, 4.0, -19), true, true)).toBe(false);
  });
});
