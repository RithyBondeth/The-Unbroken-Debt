import { describe, expect, it } from "vitest";
import { FrameFailures, MAX_LOGGED_ERRORS } from "../../src/render/renderLoop";

const FRAME = 1000 / 60;

/** Fails `count` frames with `error`, one frame apart, starting at `start` ms. */
function failFrames(f: FrameFailures, count: number, error: unknown, start = 0) {
  const results = [];
  for (let i = 0; i < count; i++) results.push(f.failed(error, start + i * FRAME));
  return results;
}

describe("FrameFailures", () => {
  it("logs an error the first time only", () => {
    const f = new FrameFailures();
    const results = failFrames(f, 5, new TypeError("createBindGroup failed"));
    expect(results.map((r) => r.log)).toEqual([true, false, false, false, false]);
  });

  it("logs each distinct error once", () => {
    const f = new FrameFailures();
    expect(f.failed(new TypeError("a"), 0).log).toBe(true);
    expect(f.failed(new TypeError("b"), FRAME).log).toBe(true);
    expect(f.failed(new RangeError("a"), 2 * FRAME).log).toBe(true);
    expect(f.failed(new TypeError("a"), 3 * FRAME).log).toBe(false);
    expect(f.failed("thrown string", 4 * FRAME).log).toBe(true);
    expect(f.failed("thrown string", 5 * FRAME).log).toBe(false);
  });

  it("doesn't log an error again after frames recovered in between", () => {
    const f = new FrameFailures();
    f.failed(new Error("x"), 0);
    f.rendered(FRAME);
    expect(f.failed(new Error("x"), 2 * FRAME).log).toBe(false);
  });

  it("stops logging new errors at the limit, and says so once", () => {
    const f = new FrameFailures();
    const results = Array.from({ length: MAX_LOGGED_ERRORS + 5 }, (_, i) =>
      f.failed(new Error(`frame ${i}`), i * FRAME),
    );
    expect(results.filter((r) => r.log)).toHaveLength(MAX_LOGGED_ERRORS);
    expect(results.filter((r) => r.limitReached)).toHaveLength(1);
    expect(results[MAX_LOGGED_ERRORS - 1].limitReached).toBe(true);
  });

  it("reports nothing for a frame that rendered after another that did", () => {
    const f = new FrameFailures();
    expect(f.rendered(0)).toBeNull();
    expect(f.rendered(FRAME)).toBeNull();
  });

  it("reports the failed streak when frames render again", () => {
    const f = new FrameFailures();
    failFrames(f, 3, new Error("x"));
    const streak = f.rendered(3 * FRAME);
    expect(streak).toEqual({ frames: 3, ms: 3 * FRAME, stalled: false });
    expect(f.frames).toBe(0);
    expect(f.rendered(4 * FRAME)).toBeNull();
  });

  it("treats a single failed frame as a hitch, not a stall", () => {
    const f = new FrameFailures(2000);
    expect(f.failed(new Error("x"), 0).stalled).toBe(false);
    expect(f.rendered(FRAME)?.stalled).toBe(false);
  });

  it("stalls once after failing for the stall time, then recovers", () => {
    const f = new FrameFailures(2000);
    const results = failFrames(f, 180, new Error("x"));
    const stalls = results.map((r, i) => (r.stalled ? i : -1)).filter((i) => i >= 0);
    // 2000 ms of failing time is reached on the 121st frame (120 gaps of 16.7 ms).
    expect(stalls).toEqual([120]);
    expect(f.rendered(180 * FRAME)).toMatchObject({ frames: 180, stalled: true });
  });

  it("starts a new streak after recovering", () => {
    const f = new FrameFailures(2000);
    failFrames(f, 150, new Error("x"));
    f.rendered(150 * FRAME);
    const again = failFrames(f, 10, new Error("x"), 151 * FRAME);
    expect(again.some((r) => r.stalled)).toBe(false);
    expect(f.rendered(161 * FRAME)).toMatchObject({ frames: 10, stalled: false });
  });

  it("doesn't count a hidden tab or debugger pause as failing time", () => {
    const f = new FrameFailures(2000);
    f.failed(new Error("x"), 0);
    // Ten seconds without frames, then one more failure: still a short streak.
    expect(f.failed(new Error("x"), 10_000).stalled).toBe(false);
    expect(f.rendered(10_000 + FRAME)?.ms).toBeLessThan(500);
  });
});
