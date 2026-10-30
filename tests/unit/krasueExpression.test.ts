import { describe, expect, it } from "vitest";
import { krasueScreamMouth } from "../../src/episodes/ep1/entities/KrasueExpression";

describe("Krasue scream articulation", () => {
  it("opens with the scream, holds through the rush, then closes on its audio tail", () => {
    expect(krasueScreamMouth(-1)).toBe(0);
    expect(krasueScreamMouth(0)).toBe(0);
    expect(krasueScreamMouth(0.025)).toBeGreaterThan(0.2);
    for (const age of [0.075, 0.38, 1, 1.9]) expect(krasueScreamMouth(age)).toBeGreaterThan(0.93);
    expect(krasueScreamMouth(2.2)).toBeLessThan(0.5);
    expect(krasueScreamMouth(2.4)).toBe(0);
    expect(krasueScreamMouth(Infinity)).toBe(0);
    expect(krasueScreamMouth(NaN)).toBe(0);
  });
});
