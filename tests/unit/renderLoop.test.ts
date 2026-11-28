import { describe, expect, it } from "vitest";
import {
  FrameFailures,
  FramePacer,
  MAX_LOGGED_ERRORS,
  refreshesPerFrame,
} from "@/render/renderLoop";

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

describe("refreshesPerFrame", () => {
  it("renders every refresh up to about 75 Hz and every second refresh on 120-165 Hz panels", () => {
    expect(refreshesPerFrame(1000 / 60)).toBe(1);
    expect(refreshesPerFrame(1000 / 75)).toBe(1);
    expect(refreshesPerFrame(1000 / 90)).toBe(1);
    expect(refreshesPerFrame(1000 / 120)).toBe(2);
    expect(refreshesPerFrame(1000 / 144)).toBe(2);
    expect(refreshesPerFrame(1000 / 165)).toBe(2);
    expect(refreshesPerFrame(1000 / 240)).toBe(4);
  });

  it("falls back to every refresh when the interval is unknown", () => {
    expect(refreshesPerFrame(0)).toBe(1);
    expect(refreshesPerFrame(Number.NaN)).toBe(1);
  });
});

describe("FramePacer", () => {
  /**
   * Drives the pacer with display refreshes at `times` (ms); returns when frames
   * rendered. With `slowAfter`, a frame rendered past that time overruns the next
   * refresh, which then brings no callback (as in a browser).
   */
  function drive(targetFps: number, times: number[], slowAfter = Infinity): number[] {
    const queue: FrameRequestCallback[] = [];
    const g = globalThis as unknown as { window?: unknown };
    const previous = g.window;
    g.window = {
      requestAnimationFrame: (cb: FrameRequestCallback) => queue.push(cb),
      cancelAnimationFrame: () => undefined,
    };
    try {
      const pacer = new FramePacer(targetFps);
      const rendered: number[] = [];
      const render = (now: number) => {
        rendered.push(now);
        pacer.requestAnimationFrame(render);
      };
      pacer.requestAnimationFrame(render);
      let overran = false;
      for (const t of times) {
        if (overran) {
          overran = false;
          continue;
        }
        const before = rendered.length;
        queue.shift()?.(t);
        overran = rendered.length > before && t > slowAfter;
      }
      return rendered;
    } finally {
      g.window = previous;
    }
  }

  const refreshes = (hz: number, count: number) =>
    Array.from({ length: count }, (_, i) => (i * 1000) / hz);

  it("renders every refresh while it measures, then holds the cap", () => {
    const rendered = drive(30, refreshes(60, 181));
    const after = rendered.filter((t) => t > 1100);
    const gaps = after.slice(1).map((t, i) => t - after[i]);
    expect(Math.min(...gaps)).toBeCloseTo(1000 / 30, 6);
    expect(Math.max(...gaps)).toBeCloseTo(1000 / 30, 6);
  });

  it("keeps 30 fps when each frame overruns a refresh (no callback for the missed one)", () => {
    const rendered = drive(30, refreshes(60, 400), 1100).filter((t) => t > 1300);
    const span = rendered[rendered.length - 1] - rendered[0];
    const fps = ((rendered.length - 1) * 1000) / span;
    expect(fps).toBeGreaterThan(28);
  });

  it("renders every refresh with no cap", () => {
    expect(drive(0, refreshes(120, 300)).length).toBe(300);
  });

  it("paces a 120 Hz display at 60 fps", () => {
    const rendered = drive(60, refreshes(120, 300)).filter((t) => t > 1000);
    const gaps = rendered.slice(1).map((t, i) => t - rendered[i]);
    expect(Math.min(...gaps)).toBeCloseTo(1000 / 60, 6);
  });
});
