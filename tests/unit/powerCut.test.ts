import { expect, it } from "vitest";
import {
  POWER_CUT,
  POWER_RETURN,
  POWER_RETURN_LENGTH,
  powerAt,
} from "@/episodes/ep1/data/powerCut";

it("puts every light out at once, stutters them back and holds them on", () => {
  expect(powerAt(-0.1)).toBe(1);
  expect(powerAt(0)).toBe(0);
  expect(powerAt(1.0)).toBe(0);
  // The stutter: on, nearly off, most of the way, off, on.
  expect(powerAt(1.3)).toBe(1);
  expect(powerAt(1.4)).toBeLessThan(0.2);
  expect(powerAt(1.5)).toBeGreaterThan(0.5);
  expect(powerAt(1.6)).toBe(0);
  expect(powerAt(POWER_CUT.length)).toBe(1);
  expect(powerAt(10)).toBe(1);
});

it("starts coming back at POWER_RETURN, where the lights' catching sound is played from", () => {
  expect(powerAt(POWER_RETURN - 0.01)).toBe(0);
  expect(POWER_RETURN_LENGTH).toBeCloseTo(POWER_CUT.length - POWER_RETURN);
  expect(powerAt(POWER_RETURN + POWER_RETURN_LENGTH)).toBe(1);
});
