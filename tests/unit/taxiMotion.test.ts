import { expect, it } from "vitest";
import {
  taxiDistance,
  taxiRoadX,
  taxiRoadHeading,
  taxiRoadPose,
  taxiRouteChunkVisible,
  taxiSpeed,
  taxiWiperAngle,
} from "../../src/episodes/ep1/travel/taxiMotion";
it("uses a continuous distance integral and brakes to a stop without a jump on reload", () => {
  expect(taxiDistance(0)).toBe(0);
  expect(taxiSpeed(72)).toBe(0);
  for (const t of [0, 12, 32, 61.9, 62, 66, 70, 71.9]) {
    expect(taxiDistance(t + 0.001)).toBeGreaterThanOrEqual(taxiDistance(t));
    expect((taxiDistance(t + 0.001) - taxiDistance(t)) / 0.001).toBeCloseTo(taxiSpeed(t), 1);
  }
  expect(taxiDistance(100)).toBe(taxiDistance(72));
});
it("follows a continuous curve with the road beneath the car and its tangent facing forward", () => {
  for (let t = 0; t <= 72; t += 0.07) {
    const d = taxiDistance(t),
      pose = taxiRoadPose(d),
      c = Math.cos(pose.yaw),
      s = Math.sin(pose.yaw);
    const x = taxiRoadX(d);
    expect(c * x + s * d + pose.x).toBeCloseTo(0, 8);
    expect(-s * x + c * d + pose.z).toBeCloseTo(0, 8);
    const tangent = (taxiRoadX(d + 0.001) - taxiRoadX(d - 0.001)) / 0.002;
    expect(c * tangent + s).toBeCloseTo(0, 6);
    expect(Math.abs(taxiRoadHeading(d + 0.01) - taxiRoadHeading(d))).toBeLessThan(0.0001);
    expect(Math.abs(taxiRoadPose(d + 0.01).x - pose.x)).toBeLessThan(0.04);
  }
  expect(Math.abs(taxiRoadX(50) - taxiRoadX(150))).toBeGreaterThan(1);
});
it("synchronizes the water sweep to a smooth repeating wiper stroke", () => {
  for (let t = 0; t < 20; t += 0.033) {
    expect(taxiWiperAngle(t)).toBeCloseTo(taxiWiperAngle(t + 1.8), 10);
    expect(Math.abs(taxiWiperAngle(t))).toBeLessThanOrEqual(0.9);
    expect(Math.abs(taxiWiperAngle(t + 0.001) - taxiWiperAngle(t))).toBeLessThan(0.004);
  }
});

it("keeps both visible horizons active while culling only distant forest chunks", () => {
  for (let t = 0; t <= 72; t += 0.5) {
    const distance = taxiDistance(t);
    for (const offset of [-65, -60, -30, 0, 30, 60, 65])
      expect(taxiRouteChunkVisible(distance + offset - 8, distance + offset + 8, distance)).toBe(
        true,
      );
    expect(taxiRouteChunkVisible(distance + 100, distance + 118, distance)).toBe(false);
    expect(taxiRouteChunkVisible(distance - 118, distance - 100, distance)).toBe(false);
  }
});
