import { afterEach, expect, it } from "vitest";
import { NullEngine } from "@babylonjs/core/Engines/nullEngine";
import { Scene } from "@babylonjs/core/scene";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { ShrineWoodwork } from "../../src/episodes/ep1/act1/ShrineWoodwork";
import { RelicCraft } from "../../src/episodes/ep1/act3/RelicCraft";
import { ShrineResponse } from "../../src/episodes/ep1/act1/ShrineResponse";
import { mapShrineGrain, ShrineAgeing } from "../../src/episodes/ep1/act1/ShrineAgeing";
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

it("keeps weathering and the plain timber support finite and within a small geometry budget", () => {
  const engine = new NullEngine();
  engines.push(engine);
  const scene = new Scene(engine),
    c = new RelicCraft(scene);
  const root = new TransformNode("shrine", scene),
    wood = new PBRMaterial("wood", scene);
  const ageing = new ShrineAgeing(c, root);
  ageing.pedestal(wood, wood, wood);
  ageing.dress(wood, wood, wood, wood, wood);
  let triangles = 0;
  for (const [i, mesh] of c.meshes.entries()) {
    mapShrineGrain(mesh, i);
    triangles += mesh.getTotalIndices() / 3;
    for (const kind of ["position", "normal", "uv"])
      expect(mesh.getVerticesData(kind)?.every(Number.isFinite)).toBe(true);
    mesh.computeWorldMatrix(true);
    const bounds = mesh.getBoundingInfo().boundingBox;
    expect(bounds.minimumWorld.y).toBeGreaterThan(0);
    expect(bounds.maximumWorld.x).toBeLessThan(0.75);
    expect(bounds.minimumWorld.x).toBeGreaterThan(-0.75);
  }
  expect(triangles).toBeLessThan(14000);
});

it("runs grain lengthwise on both upright posts and horizontal rails without stretching a full atlas onto each piece", () => {
  const engine = new NullEngine();
  engines.push(engine);
  const scene = new Scene(engine),
    c = new RelicCraft(scene);
  const root = new TransformNode("shrine", scene),
    wood = new PBRMaterial("wood", scene);
  for (const [size, axis] of [
    [[0.06, 0.72, 0.06], 1],
    [[0.72, 0.06, 0.06], 0],
  ] as const) {
    const mesh = c.box(root, "timber", size, [0, 1, 0], wood);
    mapShrineGrain(mesh, 1907);
    const positions = mesh.getVerticesData("position")!,
      normals = mesh.getVerticesData("normal")!,
      uvs = mesh.getVerticesData("uv")!;
    const front = Array.from({ length: positions.length / 3 }, (_, i) => i).filter(
      (i) => Math.abs(normals[i * 3 + 2]) > 0.9,
    );
    const u = front.map((i) => uvs[i * 2]),
      v = front.map((i) => uvs[i * 2 + 1]);
    expect(Math.max(...u) - Math.min(...u)).toBeCloseTo(0.8);
    expect(Math.max(...v) - Math.min(...v)).toBeCloseTo(0.06 / 0.9);
    const bottom = front.reduce((a, b) =>
      positions[a * 3 + axis] < positions[b * 3 + axis] ? a : b,
    );
    const top = front.reduce((a, b) => (positions[a * 3 + axis] > positions[b * 3 + axis] ? a : b));
    expect(uvs[top * 2] - uvs[bottom * 2]).toBeCloseTo(0.8);
  }
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

it("builds a plain household roof with finite normals within a small geometry budget", () => {
  const engine = new NullEngine();
  engines.push(engine);
  const scene = new Scene(engine),
    c = new RelicCraft(scene),
    root = new TransformNode("shrine", scene);
  const wood = new PBRMaterial("wood", scene);
  const details = new ShrineWoodwork(c, root);
  details.household(wood, wood, wood);
  for (const mesh of c.meshes) {
    mesh.computeWorldMatrix(true);
    expect(mesh.getBoundingInfo().boundingBox.maximumWorld.y).toBeLessThan(2.45);
  }
  let triangles = 0,
    valid = true;
  for (const mesh of c.meshes) {
    triangles += mesh.getTotalIndices() / 3;
    for (const kind of ["position", "normal", "uv"])
      for (const value of mesh.getVerticesData(kind) ?? []) valid &&= Number.isFinite(value);
  }
  expect(valid).toBe(true);
  expect(triangles).toBeLessThan(600);
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

it("faces the plain gable boards toward the approaching player", () => {
  const engine = new NullEngine();
  engines.push(engine);
  const scene = new Scene(engine),
    c = new RelicCraft(scene);
  const root = new TransformNode("shrine", scene),
    wood = new PBRMaterial("wood", scene);
  new ShrineWoodwork(c, root).household(wood, wood, wood);
  const panels = c.meshes.filter((mesh) => mesh.name === "phra_phum_plain_gable_board");
  expect(panels.length).toBeGreaterThan(0);
  for (const panel of panels) {
    const normals = panel.getVerticesData("normal")!;
    for (let i = 2; i < normals.length; i += 3) expect(normals[i]).toBeGreaterThan(0.99);
  }
});
