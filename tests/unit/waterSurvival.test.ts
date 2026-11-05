import { describe, expect, it } from "vitest";
import { WaterSurvival } from "../../src/episodes/ep3/WaterSurvival";
import { DrownedBrain } from "../../src/episodes/ep3/DrownedBrain";
describe("Water, warmth and the drowned spirit", () => {
  it("gets wet and cold in water, recovers under a safe lamp, and never advances on pause", () => {
    const s = new WaterSurvival();
    for (let i = 0; i < 1200; i++)
      s.update(0.1, { depth: 0.4, rain: true, warm: false, sheltered: false });
    expect(s.wetness).toBe(1);
    expect(s.warmth).toBeLessThan(0.7);
    const saved = [s.wetness, s.warmth];
    s.update(0, { depth: 0.4, rain: true, warm: false, sheltered: false });
    expect([s.wetness, s.warmth]).toEqual(saved);
    for (let i = 0; i < 300; i++)
      s.update(0.1, { depth: 0, rain: false, warm: true, sheltered: true });
    expect(s.wetness).toBe(0);
    expect(s.warmth).toBe(1);
  });
  it("bounds hitches and rejects negative frame time", () => {
    const a = new WaterSurvival(),
      b = new WaterSurvival(),
      exposure = { depth: 1, rain: true, warm: false, sheltered: false };
    a.update(100, exposure);
    b.update(0.1, exposure);
    expect(a.wetness).toBe(b.wetness);
    a.update(-10, exposure);
    expect(a.wetness).toBe(b.wetness);
  });
  it("warns with ripples, cannot catch on dry boards or in lamplight, and withdraws immediately", () => {
    const b = new DrownedBrain(),
      at = { x: 5, z: -5 };
    b.update(0.1, at, true, false);
    expect(b.state).toBe("ripple");
    expect(b.catches(at, true, false)).toBe(false);
    for (let i = 0; i < 65; i++) b.update(0.1, at, true, false);
    expect(b.catches(at, true, false)).toBe(true);
    expect(b.catches(at, false, false)).toBe(false);
    expect(b.catches(at, true, true)).toBe(false);
    b.update(0.1, at, false, false);
    expect(b.state).toBe("withdrawn");
    expect(b.catches(at, true, false)).toBe(false);
  });
});
