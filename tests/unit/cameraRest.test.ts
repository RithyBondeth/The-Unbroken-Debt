import { describe, expect, it } from "vitest";
import { approachExactly, followWithin, REST_DEADBAND, settleEye } from "@/player/cameraRest";

describe("followWithin: the camera at rest", () => {
  it("ignores sub-millimetre settling, so the camera stays exactly still", () => {
    const anchor = { x: 1, z: 2 };
    for (let i = 0; i < 600; i++) {
      const jitter = Math.sin(i * 1.7) * 0.0008;
      followWithin(anchor, 1 + jitter, 2 - jitter, REST_DEADBAND);
      expect(anchor).toEqual({ x: 1, z: 2 });
    }
  });

  it("follows a real push, one band behind", () => {
    const anchor = { x: 0, z: 0 };
    followWithin(anchor, 0.1, 0, REST_DEADBAND);
    expect(anchor.x).toBeCloseTo(0.1 - REST_DEADBAND, 9);
    expect(anchor.z).toBe(0);
  });
});

describe("approachExactly", () => {
  it("lands exactly on the target instead of creeping forever", () => {
    let value = 0.022;
    let frames = 0;
    while (value !== 0 && frames < 1000) {
      value = approachExactly(value, 0, 0.1, 1e-5);
      frames++;
    }
    expect(value).toBe(0);
    expect(frames).toBeLessThan(100);
  });
});

describe("settleEye", () => {
  it("holds the eye still at rest against small changes", () => {
    expect(settleEye(1.58, 1.581, 0.2, REST_DEADBAND, true)).toBe(1.58);
  });

  it("smooths as usual when moving, or for changes beyond the band", () => {
    expect(settleEye(1.58, 1.581, 0.5, REST_DEADBAND, false)).toBeCloseTo(1.5805, 9);
    expect(settleEye(1.58, 1.0, 0.5, REST_DEADBAND, true)).toBeCloseTo(1.29, 9);
  });
});
