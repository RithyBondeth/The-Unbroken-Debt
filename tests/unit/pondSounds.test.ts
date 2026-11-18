import { describe, expect, it } from "vitest";
import { seededRandom } from "@/audio/synth";
import { pondSplash } from "@/episodes/ep1/audio/pondSounds";

describe("pond splash", () => {
  it("lands hard and dies away into bubbles", () => {
    const rate = 22050;
    const s = pondSplash(rate, seededRandom(1931));
    expect(s.length).toBe(Math.round(4.2 * rate));
    const peak = (a: number, b: number) => Math.max(...s.slice(a * rate, b * rate).map(Math.abs));
    expect(peak(0, 0.3)).toBeGreaterThan(0.5);
    expect(peak(3.8, 4.2)).toBeLessThan(peak(0, 0.3) * 0.3);
    expect(s.every(Number.isFinite)).toBe(true);
  });
});
