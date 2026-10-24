import { describe, expect, it } from "vitest";
import { BOOK, paperHeight, roundedOutline } from "../../src/ui/diegetic/bookGeometry";

describe("bound sketchbook geometry", () => {
  it("has a recessed gutter and an arched page that fits within a physical binding", () => {
    const gutter = paperHeight(0, 0);
    const shoulder = paperHeight(0.025, 0);
    const foreEdge = paperHeight(BOOK.width, 0);
    expect(gutter).toBeLessThan(shoulder - 0.003);
    expect(foreEdge).toBeLessThan(shoulder);
    for (let i = 0; i <= 100; i++) {
      const height = paperHeight((BOOK.width * i) / 100, BOOK.height / 2);
      expect(Number.isFinite(height)).toBe(true);
      expect(height).toBeGreaterThanOrEqual(BOOK.pageY);
      expect(height).toBeLessThan(0.012);
    }
  });

  it("rounds corners while retaining the specified cover size", () => {
    const width = BOOK.width + 0.008,
      height = BOOK.height + 0.01;
    const outline = roundedOutline(width, height, 0.007);
    expect(Math.max(...outline.map(([x]) => x))).toBeCloseTo(width / 2);
    expect(Math.min(...outline.map(([x]) => x))).toBeCloseTo(-width / 2);
    expect(Math.max(...outline.map(([, z]) => z))).toBeCloseTo(height / 2);
    expect(
      outline.every(
        ([x, z]) => Math.abs(x) < width / 2 - 0.0001 || Math.abs(z) < height / 2 - 0.0001,
      ),
    ).toBe(true);
  });
});
