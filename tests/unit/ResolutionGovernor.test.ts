import { describe, expect, it } from "vitest";
import { ResolutionGovernor } from "@/render/ResolutionGovernor";

const TARGET = 1000 / 60;

function run(
  g: ResolutionGovernor,
  seconds: number,
  frameMs: number,
  gpuMs: number | null,
): number {
  for (let t = 0; t < seconds * 1000; t += frameMs) g.update(frameMs, gpuMs);
  return g.scale;
}

describe("ResolutionGovernor with GPU timing", () => {
  it("lowers resolution when the GPU is over budget, down to the floor", () => {
    const g = new ResolutionGovernor({ targetMs: TARGET, minScale: 0.6 });
    expect(run(g, 5, TARGET, 22)).toBe(0.6);
  });

  it("ignores a single hitch", () => {
    const g = new ResolutionGovernor({ targetMs: TARGET, minScale: 0.6 });
    run(g, 1, TARGET, 12);
    g.update(60, 60);
    expect(run(g, 1, TARGET, 12)).toBe(1);
  });

  it("ignores very long frames from a hidden tab", () => {
    const g = new ResolutionGovernor({ targetMs: TARGET, minScale: 0.6 });
    expect(run(g, 10, 1000, null)).toBe(1);
  });

  it("raises resolution again when there is headroom", () => {
    const g = new ResolutionGovernor({ targetMs: TARGET, minScale: 0.6 });
    run(g, 5, TARGET, 22);
    expect(run(g, 10, TARGET, 8)).toBe(1);
  });

  it("holds steady inside the comfortable band", () => {
    const g = new ResolutionGovernor({ targetMs: TARGET, minScale: 0.6 });
    run(g, 5, TARGET, 22);
    const scale = run(g, 2, TARGET, 14);
    expect(run(g, 5, TARGET, 14)).toBe(scale);
  });
});

describe("ResolutionGovernor without GPU timing", () => {
  it("drops on missed frames", () => {
    const g = new ResolutionGovernor({ targetMs: TARGET, minScale: 0.75 });
    expect(run(g, 3, 25, null)).toBe(0.75);
  });

  it("probes back up while frames stay on time", () => {
    const g = new ResolutionGovernor({ targetMs: TARGET, minScale: 0.75 });
    run(g, 3, 25, null);
    expect(run(g, 20, TARGET, null)).toBe(1);
  });
});

describe("ResolutionGovernor floor (sketchbook open)", () => {
  it("jumps up to the floor and stays there under load", () => {
    const g = new ResolutionGovernor({ targetMs: TARGET, minScale: 0.6 });
    expect(run(g, 5, TARGET, 22)).toBe(0.6);
    g.setFloor(0.85);
    expect(g.scale).toBe(0.85);
    expect(run(g, 5, TARGET, 22)).toBe(0.85);
  });

  it("lowers again once released", () => {
    const g = new ResolutionGovernor({ targetMs: TARGET, minScale: 0.6 });
    g.setFloor(0.85);
    run(g, 5, TARGET, 22);
    g.setFloor(null);
    expect(run(g, 5, TARGET, 22)).toBe(0.6);
  });
});

describe("ResolutionGovernor: changing as rarely as it can", () => {
  /** Counts the scale changes while a GPU cost follows the scale (cost ∝ pixels). */
  function changes(g: ResolutionGovernor, seconds: number, fullScaleGpuMs: number): number {
    let count = 0;
    let last = g.scale;
    for (let t = 0; t < seconds * 1000; t += TARGET) {
      g.update(TARGET, fullScaleGpuMs * g.scale * g.scale);
      if (g.scale !== last) count++;
      last = g.scale;
    }
    return count;
  }

  it("drops straight to a scale that fits, instead of step after step", () => {
    const g = new ResolutionGovernor({ targetMs: TARGET, minScale: 0.5 });
    const count = changes(g, 3, 26);
    expect(count).toBeLessThanOrEqual(3);
    expect(26 * g.scale * g.scale).toBeLessThan(TARGET * 0.95);
  });

  it("settles instead of oscillating when the load follows the scale", () => {
    const g = new ResolutionGovernor({ targetMs: TARGET, minScale: 0.5 });
    changes(g, 5, 24);
    expect(changes(g, 60, 24)).toBe(0);
  });

  it("respects the player's resolution setting and a 30 fps budget", () => {
    const g = new ResolutionGovernor({ targetMs: 1000 / 30, minScale: 0.5, maxScale: 0.75 });
    expect(g.scale).toBe(0.75);
    // 25 ms frames are fine at 30 fps: no reason to drop.
    expect(run(g, 5, 1000 / 30, 25)).toBe(0.75);
    g.setMaxScale(1);
    expect(g.scale).toBe(0.75);
  });

  it("starts over at the top after a reset", () => {
    const g = new ResolutionGovernor({ targetMs: TARGET, minScale: 0.6 });
    run(g, 5, TARGET, 22);
    g.reset();
    expect(g.scale).toBe(1);
  });
});
