import { describe, expect, it } from "vitest";
import { SnagDetector, type SnagSample } from "../../src/spikes/s1-movement/SnagDetector";

const sample = (speed: number, extra: Partial<SnagSample> = {}): SnagSample => ({
  dt: 1 / 60,
  supported: true,
  climbing: false,
  wishSpeed: 1.6,
  speed,
  blockedAhead: false,
  ...extra,
});

function run(detector: SnagDetector, seconds: number, s: SnagSample): void {
  for (let t = 0; t < seconds; t += s.dt) detector.update(s);
}

describe("SnagDetector", () => {
  it("ignores the slow start of a walk", () => {
    const d = new SnagDetector();
    run(d, 0.3, sample(0.2));
    expect(d.count).toBe(0);
  });

  it("counts a stall on open floor once", () => {
    const d = new SnagDetector();
    run(d, 0.5, sample(1.6));
    run(d, 1, sample(0.1));
    expect(d.count).toBe(1);
  });

  it("does not count stopping at a wall", () => {
    const d = new SnagDetector();
    run(d, 0.5, sample(1.6));
    run(d, 1, sample(0, { blockedAhead: true }));
    expect(d.count).toBe(0);
  });

  it("ignores ladders and the air", () => {
    const d = new SnagDetector();
    run(d, 1, sample(0, { climbing: true }));
    run(d, 1, sample(0, { supported: false }));
    expect(d.count).toBe(0);
  });
});
