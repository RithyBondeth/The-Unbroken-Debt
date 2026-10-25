import { describe, expect, it } from "vitest";
import { restoreLightLimits, snapshotLightLimits } from "../../src/render/lightBudget";

describe("light budgets across glTF loads", () => {
  it("puts back each material's own limit after the loader raises them", () => {
    const village = { maxSimultaneousLights: 8 };
    const book = { maxSimultaneousLights: 4 };
    const before = snapshotLightLimits([village, book]);
    // What the glTF loader does when a later load is ready: every material to the light count.
    village.maxSimultaneousLights = book.maxSimultaneousLights = 23;
    restoreLightLimits([village, book], before, 8);
    expect(village.maxSimultaneousLights).toBe(8);
    expect(book.maxSimultaneousLights).toBe(4);
  });

  it("holds materials new since the snapshot to what the device supports", () => {
    const loaded = { maxSimultaneousLights: 23 };
    const modest = { maxSimultaneousLights: 4 };
    restoreLightLimits([loaded, modest], new Map(), 8);
    expect(loaded.maxSimultaneousLights).toBe(8);
    expect(modest.maxSimultaneousLights).toBe(4);
  });

  it("leaves materials without a light limit alone", () => {
    const unlit: { maxSimultaneousLights?: number } = {};
    restoreLightLimits([unlit], snapshotLightLimits([unlit]), 8);
    expect(unlit).toEqual({});
  });
});
