import { describe, expect, it } from "vitest";
import { along, overhead, sighting, type KrasueScene } from "@/episodes/ep2/PagodaKrasue";

const s: KrasueScene = {
  stage: "garden",
  feet: { x: 2, z: -14 },
  yaw: Math.PI,
  offerings: 2,
  inKuti: false,
  nearestPret: 20,
};

describe("Episode 2's Krasue", () => {
  it("goes low over Sora's head once, out of the trees behind and into those ahead", () => {
    const f = overhead(s);
    expect(f.close).toBe(true);
    const low = along(f, 0.5);
    expect(Math.hypot(low.x - s.feet.x, low.z - s.feet.z)).toBeLessThan(1.5);
    expect(low.y).toBeGreaterThan(2.8);
    expect(low.y).toBeLessThan(4.2);
    // Starts behind her (she faces -Z here) and ends ahead, both high over the trees.
    expect(f.from.z).toBeGreaterThan(s.feet.z + 20);
    expect(f.to.z).toBeLessThan(s.feet.z - 20);
    expect(f.from.y).toBeGreaterThan(7);
  });
  it("is seen far off, drifting across what Sora faces, high over the trees", () => {
    let k = 0;
    const rand = () => [0.2, 0.7, 0.4, 0.9, 0.1][k++ % 5];
    const f = sighting(s, rand);
    for (const u of [0, 0.5, 1]) {
      const p = along(f, u);
      const d = Math.hypot(p.x - s.feet.x, p.z - s.feet.z);
      expect(d).toBeGreaterThan(14);
      expect(p.y).toBeGreaterThan(4);
    }
    const mid = along(f, 0.5);
    // In front of her: she faces -Z.
    expect(mid.z).toBeLessThan(s.feet.z);
    expect(f.seconds).toBeGreaterThan(8);
  });
});
