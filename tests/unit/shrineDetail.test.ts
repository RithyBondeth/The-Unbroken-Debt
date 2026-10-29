import { afterEach, expect, it } from "vitest";
import { NullEngine } from "@babylonjs/core/Engines/nullEngine";
import { Scene } from "@babylonjs/core/scene";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { ShrineWoodwork } from "../../src/episodes/ep1/act1/ShrineWoodwork";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { RelicCraft } from "../../src/episodes/ep1/act3/RelicCraft";
import { ShrineResponse } from "../../src/episodes/ep1/act1/ShrineResponse";
import {
  SAVE_SHRINE_POSITION,
  SAVE_SHRINE_APPROACH,
  SAVE_SHRINE_ROUTE,
  inSaveShrineClearing,
} from "../../src/episodes/ep1/data/saveShrine";
import { YARD, openGround } from "../../src/episodes/ep1/data/forestBorder";

const engines: NullEngine[] = [];
afterEach(() => {
  for (const e of engines.splice(0)) e.dispose();
});

it("puts the whole shrine and its approach outside both front-right fence lines", () => {
  expect(SAVE_SHRINE_POSITION.x + 0.75).toBeLessThan(YARD.minX - 1);
  expect(SAVE_SHRINE_POSITION.z - 0.55).toBeGreaterThan(YARD.maxZ + 1);
  expect(SAVE_SHRINE_APPROACH.z).toBeGreaterThan(YARD.maxZ);
  for (const at of SAVE_SHRINE_ROUTE) {
    expect(inSaveShrineClearing(at.x, at.z)).toBe(true);
    expect(openGround(at.x, at.z, 0.3)).toBe(false);
  }
});

it("authors solid shingles and raised leaf relief with finite normals within a prop-sized budget", () => {
  const engine = new NullEngine();
  engines.push(engine);
  const scene = new Scene(engine),
    c = new RelicCraft(scene),
    root = new TransformNode("shrine", scene);
  const wood = new PBRMaterial("wood", scene);
  const details = new ShrineWoodwork(c, root);
  details.roof(0.66, 1.04, 1.98, 0.62, wood, wood, wood, wood);
  const tiles = c.meshes.filter((mesh) => mesh.name.includes("overlapping_roof_shingle"));
  expect(tiles.length).toBe(120);
  expect(c.meshes.filter((mesh) => mesh.name === "phra_phum_carved_flame_blade")).toHaveLength(5);
  expect(c.meshes.some((mesh) => mesh.name === "phra_phum_solid_carved_pediment")).toBe(true);
  const leaf = c.meshes.find((mesh) => mesh.name.includes("chiselled_leaf_relief"))!;
  const leafDepth = leaf.getBoundingInfo().boundingBox.extendSize.z * 2;
  expect(leafDepth).toBeGreaterThan(0.015);
  let triangles = 0,
    valid = true;
  for (const mesh of c.meshes) {
    triangles += mesh.getTotalIndices() / 3;
    for (const kind of ["position", "normal", "uv"])
      for (const value of mesh.getVerticesData(kind) ?? []) valid &&= Number.isFinite(value);
  }
  expect(valid).toBe(true);
  expect(triangles).toBeLessThan(30000);
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

it("lights both mirrored front arch bands from outside the doorway", () => {
  const engine = new NullEngine();
  engines.push(engine);
  const scene = new Scene(engine),
    c = new RelicCraft(scene);
  const root = new TransformNode("shrine", scene),
    wood = new PBRMaterial("wood", scene);
  new ShrineWoodwork(c, root).entrance(wood, wood, wood, wood);
  const bands = c.meshes.filter((m) => m.name === "phra_phum_bevelled_timber_door_arch");
  expect(bands).toHaveLength(2);
  for (const band of bands) {
    const p = band.getVerticesData("position")!,
      indices = band.getIndices()!;
    // The broad, flat front of the first arch segment, between profile points 2 and 3.
    const i = 12;
    const a = Vector3.FromArray(p, indices[i] * 3),
      b = Vector3.FromArray(p, indices[i + 1] * 3),
      d = Vector3.FromArray(p, indices[i + 2] * 3);
    // Babylon computes left-handed surface normals from reversed cross products.
    const n = Vector3.Cross(d.subtract(a), b.subtract(a)).normalize();
    expect(n.z).toBeGreaterThan(0.99);
  }
});
