import { describe, expect, it } from "vitest";
import { keyFor, stickVector } from "@/ui/html/TouchControls";

describe("stickVector", () => {
  it("ignores a thumb resting in the dead zone", () => {
    expect(stickVector(3, -2, 56)).toMatchObject({ x: 0, z: 0, hurry: false });
  });

  it("walks forward when pushed up and strafes when pushed sideways", () => {
    const up = stickVector(0, -56, 56);
    expect(up.z).toBeCloseTo(1, 9);
    expect(up.x).toBeCloseTo(0, 9);
    const right = stickVector(28, 0, 56);
    expect(right.x).toBeGreaterThan(0.3);
    expect(right.x).toBeLessThan(0.6);
  });

  it("keeps the knob on the rim and hurries only past it", () => {
    expect(stickVector(0, -60, 56).hurry).toBe(false);
    const far = stickVector(0, -90, 56);
    expect(far.hurry).toBe(true);
    expect(far.knobY).toBeCloseTo(-56, 9);
    expect(far.z).toBeCloseTo(1, 9);
  });
});

describe("keyFor", () => {
  it("gives the key a keyboard would send with each code", () => {
    expect(keyFor("KeyE")).toBe("e");
    expect(keyFor("Digit3")).toBe("3");
    expect(keyFor("Space")).toBe(" ");
    expect(keyFor("Escape")).toBe("Escape");
  });
});
