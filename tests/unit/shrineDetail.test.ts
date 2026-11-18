import { expect, it } from "vitest";
import { ShrineResponse } from "@/episodes/ep1/act1/ShrineResponse";
import {
  SAVE_SHRINE_POSITION,
  SAVE_SHRINE_APPROACH,
  SAVE_SHRINE_ROUTE,
  inSaveShrineClearing,
} from "@/episodes/ep1/data/saveShrine";
import { YARD, openGround } from "@/episodes/ep1/data/forestBorder";

it("puts the whole shrine and its approach outside both front-right fence lines", () => {
  expect(SAVE_SHRINE_POSITION.x + 0.75).toBeLessThan(YARD.minX - 1);
  expect(SAVE_SHRINE_POSITION.z - 0.55).toBeGreaterThan(YARD.maxZ + 1);
  expect(SAVE_SHRINE_APPROACH.z).toBeGreaterThan(YARD.maxZ);
  for (const at of SAVE_SHRINE_ROUTE) {
    expect(inSaveShrineClearing(at.x, at.z)).toBe(true);
    expect(openGround(at.x, at.z, 0.3)).toBe(false);
  }
});

it("plays each response cue once, turns the rigid head in darkness, and restores idle", () => {
  const r = new ShrineResponse();
  r.begin();
  expect(r.active).toBe(true);
  expect(r.update(10)).toEqual([]);
  r.settle(true);
  expect(r.update(1.55)).toEqual(["knock", "knock", "knock"]);
  expect(r.darkness).toBeCloseTo(1);
  expect(r.turn).toBeLessThan(1);
  expect(r.update(0.45)).toEqual(["breath"]);
  expect(r.turn).toBeGreaterThan(0.9);
  expect(r.update(1.1)).toEqual(["ring"]);
  expect(r.update(4)).toEqual([]);
  expect(r.active).toBe(false);
  expect(r.darkness).toBe(0);
  expect(r.turn).toBe(0);
  expect(r.turn).toBe(0);
});

it("failed writes and interrupted responses restore light and never emit later cues", () => {
  const r = new ShrineResponse();
  r.begin();
  r.settle(false);
  expect(r.update(5)).toEqual([]);
  expect(r.active).toBe(false);
  r.begin();
  r.settle(true);
  r.update(1.7);
  r.cancel();
  expect(r.update(5)).toEqual([]);
  expect(r.silence).toBe(0);
  expect(r.darkness).toBe(0);
  expect(r.turn).toBe(0);
});
