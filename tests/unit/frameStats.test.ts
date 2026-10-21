import { describe, expect, it } from "vitest";
import { checkSixtyFps, summarizeFrames } from "../../src/debug/frameStats";

describe("summarizeFrames", () => {
  it("summarises a steady 60 fps run", () => {
    const s = summarizeFrames(Array.from({ length: 600 }, () => 1000 / 60));
    expect(s.frames).toBe(600);
    expect(s.avgFps).toBeCloseTo(60);
    expect(s.low1Fps).toBeCloseTo(60);
  });

  it("reports hitches in the 1% low and p99", () => {
    const frames = Array.from({ length: 1000 }, (_, i) => (i % 100 === 0 ? 50 : 16));
    const s = summarizeFrames(frames);
    expect(s.p99Ms).toBe(16);
    expect(s.low1Fps).toBeCloseTo(20);
    expect(s.maxMs).toBe(50);
  });

  it("handles an empty run", () => {
    expect(summarizeFrames([]).frames).toBe(0);
  });
});

describe("checkSixtyFps", () => {
  const steady = summarizeFrames(Array.from({ length: 600 }, () => 1000 / 60));

  it("passes a steady run within the GPU budget", () => {
    expect(checkSixtyFps(steady, 12).pass).toBe(true);
    expect(checkSixtyFps(steady, null).pass).toBe(true);
  });

  it("fails when the GPU is over 16.6 ms even if the display caps fps", () => {
    const result = checkSixtyFps(steady, 18);
    expect(result.pass).toBe(false);
    expect(result.reasons[0]).toMatch(/GPU time/);
  });

  it("fails a slow run", () => {
    expect(checkSixtyFps(summarizeFrames(Array.from({ length: 600 }, () => 25)), null).pass).toBe(
      false,
    );
  });
});
