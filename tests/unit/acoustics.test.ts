import { describe, expect, it } from "vitest";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { SPACES, impulseResponse, type SpaceName } from "../../src/audio/acoustics";
import { rms, seededRandom } from "../../src/audio/synth";
import { spaceAt } from "../../src/episodes/ep1/act1/Soundscape";

const RATE = 22050;

describe("room acoustics", () => {
  for (const [name, space] of Object.entries(SPACES) as [SpaceName, (typeof SPACES)[SpaceName]][]) {
    it(`${name}'s reverb is finite, decays and surrounds the listener`, () => {
      const [left, right] = impulseResponse(RATE, seededRandom(3), space);
      expect(left.length).toBe(right.length);
      expect(left.every(Number.isFinite) && right.every(Number.isFinite)).toBe(true);
      const tenth = Math.floor(left.length / 10);
      // The tail dies away: the last tenth is at least 30 dB under the first.
      expect(rms(left, left.length - tenth)).toBeLessThan(rms(left, 0, tenth) * 0.03);
      // The ears hear different reflections: correlation well under 1.
      let lr = 0,
        ll = 0,
        rr = 0;
      for (let i = 0; i < left.length; i++) {
        lr += left[i] * right[i];
        ll += left[i] ** 2;
        rr += right[i] ** 2;
      }
      expect(Math.abs(lr / Math.sqrt(ll * rr))).toBeLessThan(0.5);
    });
  }

  it("rings longer outdoors than under the house", () => {
    const length = (name: SpaceName) =>
      impulseResponse(RATE, seededRandom(1), SPACES[name])[0].length;
    expect(length("outdoors")).toBeGreaterThan(length("underHouse") * 2);
  });

  it("muffles the open air most in the closed rooms", () => {
    expect(SPACES.wardrobe.occlusion[0]).toBeLessThan(SPACES.house.occlusion[0]);
    expect(SPACES.house.occlusion[0]).toBeLessThan(SPACES.underHouse.occlusion[0]);
    expect(SPACES.outdoors.occlusion).toEqual([20000, 1]);
  });

  it("knows where Sora is", () => {
    expect(spaceAt(new Vector3(-4.15, 2.5, -13.55))).toBe("house"); // CP3, the upper hall
    expect(spaceAt(new Vector3(1.5, 0, -16.5))).toBe("underHouse"); // beside jar J2
    expect(spaceAt(new Vector3(0, 0, -2.5))).toBe("tent"); // CP6, at the coffin
    expect(spaceAt(new Vector3(-8.6, 0, -10.75))).toBe("outdoors"); // the foot of the stairs
    expect(spaceAt(new Vector3(20, 3, 30))).toBe("outdoors"); // high ground, not the house
  });
});
