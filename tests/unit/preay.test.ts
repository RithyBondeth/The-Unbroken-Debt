import { describe, expect, it } from "vitest";
import { PREAY_CLIPS } from "@/episodes/ep1/data/preayClips";
import { ROAMER_CHASE_SPEED, ROAMER_PATROL_SPEED } from "@/episodes/ep1/data/hunt";
import { WALKER_SPEED } from "@/episodes/ep1/data/walker";
import { SPIRIT_WALK_SPEED } from "@/episodes/ep1/travel/taxiApparitions";

/** The most any of her clips is ever sped up (Preay.ts MAX_RATE). */
const MAX_RATE = 1.6;

describe("the Preay moves as a person moves", () => {
  it("walks at an ordinary human pace, with two steps a cycle per foot", () => {
    expect(PREAY_CLIPS.walk.speed).toBeGreaterThan(0.6);
    expect(PREAY_CLIPS.walk.speed).toBeLessThan(1.4);
    expect(PREAY_CLIPS.walk.strikes).toHaveLength(4);
    for (const s of PREAY_CLIPS.walk.strikes) expect(s).toBeLessThan(PREAY_CLIPS.walk.seconds);
  });

  it("is never driven faster than her clips can step", () => {
    expect(WALKER_SPEED).toBeLessThanOrEqual(PREAY_CLIPS.walk.speed * MAX_RATE);
    expect(ROAMER_PATROL_SPEED).toBeLessThanOrEqual(PREAY_CLIPS.walk.speed * MAX_RATE);
    expect(ROAMER_CHASE_SPEED).toBeLessThanOrEqual(PREAY_CLIPS.hurry.speed * MAX_RATE);
    expect(SPIRIT_WALK_SPEED).toBe(PREAY_CLIPS.walk.speed);
  });
});
