import { describe, expect, it } from "vitest";
import { gradeColor, lerpGrade, NEUTRAL_GRADE } from "@/render/grade";
import { NIGHT_GRADE } from "@/render/nightGrade";
import { FUNERAL_GRADE, FUNERAL_LOOK, VILLAGE_NIGHT } from "@/episodes/ep1/data/villageLook";
import { inFuneralRoom, underFuneralFloor } from "@/episodes/ep1/data/funeral";

describe("lerpGrade", () => {
  it("is the first grade at 0 and the second at 1", () => {
    expect(lerpGrade(NIGHT_GRADE, FUNERAL_GRADE, 0)).toEqual(NIGHT_GRADE);
    expect(lerpGrade(NIGHT_GRADE, FUNERAL_GRADE, 1)).toEqual(FUNERAL_GRADE);
  });

  it("blends every value halfway at 0.5, and clamps outside 0-1", () => {
    const half = lerpGrade(NEUTRAL_GRADE, NIGHT_GRADE, 0.5);
    expect(half.saturation).toBeCloseTo(NIGHT_GRADE.saturation / 2, 6);
    expect(half.shadows.strength).toBeCloseTo(NIGHT_GRADE.shadows.strength / 2, 6);
    half.shadows.tint.forEach((v, i) =>
      expect(v).toBeCloseTo((1 + NIGHT_GRADE.shadows.tint[i]) / 2, 6),
    );
    expect(lerpGrade(NEUTRAL_GRADE, NIGHT_GRADE, 3)).toEqual(
      lerpGrade(NEUTRAL_GRADE, NIGHT_GRADE, 1),
    );
  });
});

describe("the funeral's look under the house", () => {
  it("warms the shadows the night grade cools", () => {
    const shadow: [number, number, number] = [0.06, 0.06, 0.06];
    const night = gradeColor(shadow, NIGHT_GRADE);
    const funeral = gradeColor(shadow, FUNERAL_GRADE);
    expect(night[2]).toBeGreaterThan(night[0]);
    expect(funeral[0]).toBeGreaterThan(funeral[2]);
  });

  it("holds the eye darker than the village's, with room left for night sight's maths", () => {
    expect(FUNERAL_LOOK.maxExposure).toBeLessThan(VILLAGE_NIGHT.maxExposure);
    // Atmosphere divides by log(max / base): they must never meet.
    expect(FUNERAL_LOOK.maxExposure).toBeGreaterThan(FUNERAL_LOOK.baseExposure);
  });

  it("reaches out to the front block's edge, where funeral_wide stands, and no further", () => {
    // Blender (2.4, 11.4) on the ground: outside the funeral room, under the floor.
    const wide = { x: -2.4, y: 0, z: -11.4 };
    expect(inFuneralRoom(wide)).toBe(false);
    expect(underFuneralFloor(wide)).toBe(true);
    // In the yard before the house, and up on the hall's floor above.
    expect(underFuneralFloor({ x: 0, y: 0, z: -8 })).toBe(false);
    expect(underFuneralFloor({ x: 0, y: 2.5, z: -15 })).toBe(false);
    // Under the back block, where the jars are.
    expect(underFuneralFloor({ x: 0, y: 0, z: -26 })).toBe(false);
  });
});
