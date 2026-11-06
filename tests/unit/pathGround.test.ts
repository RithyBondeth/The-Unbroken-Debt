import { describe, expect, it } from "vitest";
import { bakeGroundMask, groundMix, MASK_RESOLUTION } from "@/episodes/ep1/data/pathGround";
import { PATH, TERRAIN } from "@/episodes/ep1/data/forestBorder";

describe("village path ground", () => {
  it("is mud down the middle of the path and litter well off it", () => {
    // In the grove: the road bank (z > 59) is mud from edge to edge.
    for (const [x, z] of PATH.slice(1, -1)) {
      expect(groundMix(x, z).mud).toBeGreaterThan(0.45);
      expect(groundMix(x + 6, z).mud).toBe(0);
    }
  });

  it("has a soft, uneven edge instead of a ruled line", () => {
    // Along the path the edge sits at different distances from the centre line...
    const edges = [44, 36, 26, 16].map((z) => {
      const [x] = PATH.reduce((a, b) => (Math.abs(b[1] - z) < Math.abs(a[1] - z) ? b : a));
      let d = 0;
      while (groundMix(x + d, z).mud > 0.5 && d < 4) d += 0.05;
      return d;
    });
    expect(Math.max(...edges) - Math.min(...edges)).toBeGreaterThan(0.2);
    // ...and across it the mud fades out over more than a texel.
    const [x, z] = PATH[2];
    const steps = Array.from({ length: 60 }, (_, i) => groundMix(x + i * 0.05, z).mud);
    expect(steps.filter((m) => m > 0.05 && m < 0.95).length).toBeGreaterThan(3);
  });

  it("bakes the whole authored terrain", () => {
    const mask = bakeGroundMask();
    expect(mask.width).toBe((TERRAIN.maxX - TERRAIN.minX) * MASK_RESOLUTION);
    expect(mask.height).toBe((TERRAIN.maxZ - TERRAIN.minZ) * MASK_RESOLUTION);
    expect(mask.data.length).toBe(mask.width * mask.height * 4);
  });
});
