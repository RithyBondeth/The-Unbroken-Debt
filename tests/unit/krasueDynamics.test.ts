import { describe, expect, it } from "vitest";
import { KrasueDynamics, type KrasueJoint } from "../../src/episodes/ep1/entities/KrasueDynamics";

const joints: KrasueJoint[] = [
  { kind: "hair", index: 0, joint: 0 },
  { kind: "hair", index: 0, joint: 3 },
  { kind: "gut", index: 1, joint: 4 },
  { kind: "organ", index: 0, joint: 1 },
];
const setup = () => {
  const d = new KrasueDynamics(joints);
  d.update(1 / 60, { x: 0, y: 4, z: 0 }, 0, 0, false);
  return d;
};

describe("Krasue weighted secondary motion", () => {
  it("trails more strongly in a rush regardless of compass heading", () => {
    const travel = (speed: number, yaw: number) => {
      const d = new KrasueDynamics(joints);
      d.update(1 / 60, { x: 0, y: 4, z: 0 }, yaw, 0, false);
      for (let i = 1; i <= 45; i++)
        d.update(
          1 / 60,
          {
            x: (Math.sin(yaw) * speed * i) / 60,
            y: 4,
            z: (Math.cos(yaw) * speed * i) / 60,
          },
          yaw,
          i / 60,
          false,
        );
      return d.angles;
    };
    const patrol = travel(0.7, 0),
      rush = travel(6.2, 0);
    expect(rush[1].pitch).toBeGreaterThan(patrol[1].pitch * 4);
    expect(rush[2].pitch).toBeGreaterThan(0.07);
    for (const yaw of [Math.PI / 2, Math.PI, -Math.PI / 2]) {
      const turned = travel(6.2, yaw);
      expect(turned[1].pitch).toBeCloseTo(rush[1].pitch, 5);
      expect(Math.abs(turned[1].roll)).toBeLessThan(0.0001);
    }
  });
  it("keeps roots anchored while light hair reacts before the heavier gut", () => {
    const d = setup();
    for (let i = 1; i <= 12; i++)
      d.update(1 / 60, { x: 0, y: 4, z: (i / 60) * 4 }, 0, i / 60, false);
    expect(d.angles[1].pitch).toBeGreaterThan(0.025);
    expect(d.angles[1].pitch).toBeGreaterThan(d.angles[2].pitch * 2);
    expect(d.angles[0].pitch).toBeLessThan(d.angles[1].pitch * 0.15);
    expect(d.angles[3].pitch).toBeLessThan(d.angles[2].pitch);
  });
  it("carries momentum through braking and settles instead of looping forever", () => {
    const d = setup();
    for (let i = 1; i <= 60; i++)
      d.update(1 / 60, { x: 0, y: 4, z: (i / 60) * 4 }, 0, i / 60, false);
    const moving = d.angles[1].pitch;
    d.update(1 / 60, { x: 0, y: 4, z: 4 }, 0, 61 / 60, false);
    expect(d.angles[1].pitch).toBeGreaterThan(moving * 0.8);
    for (let i = 62; i < 480; i++) d.update(1 / 60, { x: 0, y: 4, z: 4 }, 0, i / 60, false);
    for (const a of d.angles) {
      expect(Math.abs(a.pitch)).toBeLessThan(0.0001);
      expect(Math.abs(a.pitchSpeed)).toBeLessThan(0.0001);
    }
  });
  it("reacts gradually to a turn without flipping its angles", () => {
    const d = setup();
    d.update(1 / 60, { x: 0, y: 4, z: 0 }, 0.8, 1 / 60, false);
    expect(Math.abs(d.angles[1].roll)).toBeGreaterThan(0);
    expect(Math.abs(d.angles[1].roll)).toBeLessThan(0.01);
    const first = Math.abs(d.angles[1].roll);
    for (let i = 2; i <= 12; i++) d.update(1 / 60, { x: 0, y: 4, z: 0 }, 0.8, i / 60, false);
    expect(Math.abs(d.angles[1].roll)).toBeGreaterThan(first);
  });
  it("gives consistent settled drag at 30 and 120 fps", () => {
    const simulate = (fps: number) => {
      const d = setup();
      for (let i = 1; i <= fps * 3; i++)
        d.update(1 / fps, { x: 0, y: 4, z: (i / fps) * 4 }, 0, i / fps, false);
      return d.angles;
    };
    const slow = simulate(30),
      fast = simulate(120);
    for (let i = 0; i < slow.length; i++) expect(slow[i].pitch).toBeCloseTo(fast[i].pitch, 3);
  });
  it("resets teleport and background-stall energy, and freezes on zero delta", () => {
    const d = setup();
    d.update(0.1, { x: 0, y: 4, z: 0.4 }, 0, 0.1, false);
    expect(d.angles[1].pitch).toBeGreaterThan(0);
    const pitch = d.angles[1].pitch;
    d.update(0, { x: 0, y: 4, z: 0.4 }, 0, 0.1, false);
    expect(d.angles[1].pitch).toBe(pitch);
    d.update(120, { x: 0, y: 4, z: 0.4 }, 0, 120, false);
    expect(d.angles.every((a) => a.pitch === 0 && a.roll === 0)).toBe(true);
    d.update(0.1, { x: 0, y: 4, z: 0.8 }, 0, 120.1, false);
    d.update(0.01, { x: 30, y: 4, z: 20 }, 1, 120.11, false);
    expect(d.angles.every((a) => a.pitch === 0 && a.roll === 0)).toBe(true);
  });
});
