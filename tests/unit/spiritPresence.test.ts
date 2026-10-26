import { describe, expect, it } from "vitest";
import { SpiritPresence } from "../../src/episodes/ep1/entities/SpiritPresence";

describe("spirit emergence", () => {
  it("emerges before settling, then recedes before being disabled", () => {
    const presence = new SpiritPresence();
    presence.show();
    expect(presence.value).toBe(0);
    expect(presence.visible).toBe(true);
    presence.update(0.325);
    expect(presence.value).toBeCloseTo(0.5);
    expect(presence.settled).toBe(false);
    presence.update(0.325);
    expect(presence.settled).toBe(true);
    presence.hide();
    presence.update(0.125);
    expect(presence.value).toBeCloseTo(0.5);
    expect(presence.visible).toBe(true);
    presence.update(0.125);
    expect(presence.value).toBe(0);
    expect(presence.visible).toBe(false);
  });

  it("keeps the same timing at different refresh rates and cancels a partial entrance", () => {
    const advance = (fps: number) => {
      const presence = new SpiritPresence();
      presence.show();
      for (let i = 0; i < fps / 2; i++) presence.update(1 / fps);
      return presence;
    };
    expect(advance(60).value).toBeCloseTo(advance(144).value, 6);
    const presence = advance(60);
    const before = presence.value;
    presence.hide();
    expect(presence.value).toBe(before);
    presence.update(0.05);
    expect(presence.value).toBeLessThan(before);
    presence.hide(true);
    expect(presence.visible).toBe(false);
    expect(presence.value).toBe(0);
  });
});
