import { describe, expect, it } from "vitest";
import { cloudDeck, cloudScud, elevation } from "../../src/episodes/ep1/act1/stormClouds";
import { DAWN_LOOK, NIGHT_LOOK } from "../../src/episodes/ep1/data/nightLook";

const W = 256,
  H = 128;
const luma = (data: Uint8Array, x: number, y: number) => {
  const i = (y * W + x) * 4;
  return (data[i] + data[i + 1] + data[i + 2]) / 3;
};
const rowMean = (data: Uint8Array, y: number) => {
  let sum = 0;
  for (let x = 0; x < W; x++) sum += luma(data, x, y);
  return sum / W;
};

describe("storm clouds", () => {
  const deck = cloudDeck(W, H);
  const scud = cloudScud(W, H);

  it("maps rows from zenith to nadir", () => {
    expect(elevation(0)).toBeCloseTo(Math.PI / 2);
    expect(elevation(0.5)).toBeCloseTo(0);
  });

  it("is deterministic and wraps round the dome", () => {
    expect(cloudDeck(W, H).data).toEqual(deck.data);
    for (const y of [20, 50, 60])
      expect(Math.abs(luma(deck.data, 0, y) - luma(deck.data, W - 1, y))).toBeLessThan(40);
  });

  it("has real cloud structure, not a flat dome", () => {
    const y = Math.round(H * 0.35);
    const values = Array.from({ length: W }, (_, x) => luma(deck.data, x, y));
    expect(Math.max(...values) - Math.min(...values)).toBeGreaterThan(40);
  });

  it("is lighter towards the horizon than overhead, and dark below it", () => {
    expect(rowMean(deck.data, Math.round(H * 0.45))).toBeGreaterThan(rowMean(deck.data, 2));
    expect(rowMean(deck.data, Math.round(H * 0.8))).toBeLessThan(5);
  });

  it("keeps the low scud near the horizon", () => {
    const near = rowMean(scud.data, Math.round(H * 0.45));
    const zenith = rowMean(scud.data, 1);
    expect(near).toBeLessThan(zenith);
    expect(zenith).toBeGreaterThan(250);
  });
});

describe("night look", () => {
  it("is moonlit enough to read the forest, still night, and lifts at dawn", () => {
    expect(NIGHT_LOOK.baseExposure).toBeLessThan(1.85);
    expect(NIGHT_LOOK.nightSightIntensity).toBeLessThan(2.8);
    expect(NIGHT_LOOK.moonIntensity).toBeGreaterThanOrEqual(0.5);
    expect(NIGHT_LOOK.skyIntensity).toBeGreaterThanOrEqual(0.4);
    expect(NIGHT_LOOK.fogAmbient[2]).toBeGreaterThan(NIGHT_LOOK.fogAmbient[0]);
    expect(DAWN_LOOK.skyIntensity).toBeGreaterThan(NIGHT_LOOK.skyIntensity * 2);
    expect(DAWN_LOOK.fogAmbient[0]).toBeGreaterThan(NIGHT_LOOK.fogAmbient[0] * 3);
    expect(DAWN_LOOK.clearColor[1]).toBeGreaterThan(NIGHT_LOOK.clearColor[1] * 10);
  });
});
