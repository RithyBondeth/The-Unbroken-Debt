import { describe, expect, it } from "vitest";
import { shelterAt } from "@/render/skyShelter";
import { HOUSE_SHELTER } from "@/episodes/ep1/data/shelter";

/** Babylon coordinates from Blender's (x = -x, y = z, z = -y). */
const at = (x: number, y: number, z: number) => shelterAt(HOUSE_SHELTER, -x, z, -y);

describe("the farmstead house's shelter from the sky", () => {
  it("keeps the sky out of the rooms and the attic", () => {
    expect(at(0, 15, 3.5)).toBeCloseTo(0.04); // the hall
    expect(at(-5, 25, 3.5)).toBeCloseTo(0.04); // Sok's study
    expect(at(0, 16, 6.0)).toBeCloseTo(0.05); // the attic under the ridge
  });

  it("keeps the inner face of an outer wall sheltered and its outer face in the sky", () => {
    expect(at(-5.94, 15, 3.5)).toBeLessThan(0.1); // the west wall's lining
    expect(at(-6.0, 15, 3.5)).toBeGreaterThan(0.95); // its weatherboards
    expect(at(0, 11.44, 3.5)).toBeGreaterThan(0.95); // the front wall's outer face
    expect(at(-8.0, 28, 3.5)).toBeGreaterThan(0.95); // the back block's west wall
  });

  it("leaves the roof's outer surface in the sky", () => {
    // The roof rises 0.9 m for every metre in from the eaves; at the attic box's ends
    // its tiles stand above the box.
    const roof = (y: number, ridge: number) => 5.27 + (6 - Math.abs(y - ridge)) * 0.9 + 0.05;
    expect(at(0, 11.6, roof(11.6, 16))).toBeGreaterThan(0.95);
    expect(at(0, 23.6, roof(23.6, 28))).toBeGreaterThan(0.95);
  });

  it("darkens the funeral's ground and lets the sky back in past the stilts", () => {
    expect(at(1.5, 17.7, 0.5)).toBeCloseTo(0.08); // the coffin
    const edge = at(0, 10, 0.5); // the front stilts
    expect(edge).toBeGreaterThan(0.2);
    expect(edge).toBeLessThan(0.7);
    expect(at(0, 6, 0.5)).toBeCloseTo(1); // the yard
  });
});
