import { describe, expect, it } from "vitest";
import {
  GAITS,
  gaitFor,
  headJerk,
  playbackRate,
  steppedOn,
  turnToward,
} from "../../src/episodes/ep2/ShroudedDead";

describe("how the hungry dead move", () => {
  it("drags on patrol, lurches at a sound, and stands to listen", () => {
    expect(gaitFor(true, "patrol")).toBe("walk");
    expect(gaitFor(true, "investigate")).toBe("lurch");
    expect(gaitFor(false, "listen")).toBe("listen");
    expect(gaitFor(false, "investigate")).toBe("listen");
  });
  it("plays each clip at the rate that keeps its feet with the ground", () => {
    expect(playbackRate("walk", GAITS.walk.speed)).toBe(1);
    expect(playbackRate("lurch", GAITS.lurch.speed * 2)).toBe(2);
  });
  it("hears a footfall when the loop passes a step, even across the wrap", () => {
    const steps = [0.2, 0.7];
    expect(steppedOn(0.1, 0.3, steps)).toBe(true);
    expect(steppedOn(0.3, 0.6, steps)).toBe(false);
    expect(steppedOn(0.95, 0.25, steps)).toBe(true);
    expect(steppedOn(0.95, 0.1, [0.97])).toBe(true);
    expect(steppedOn(0.95, 0.1, [0.5])).toBe(false);
  });
  it("turns the short way round and no faster than allowed", () => {
    expect(turnToward(0, 1, 0.25)).toBeCloseTo(0.25);
    expect(turnToward(3, -3, 0.1)).toBeCloseTo(3.1);
    expect(turnToward(0.5, 0.52, 1)).toBeCloseTo(0.52);
  });
  it("jerks the head over at once and lets it settle back", () => {
    expect(headJerk(0)).toBe(0);
    expect(headJerk(0.1)).toBeCloseTo(1);
    expect(headJerk(0.5)).toBeLessThan(1);
    expect(headJerk(5)).toBe(0);
  });
});
