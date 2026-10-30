import { fileURLToPath } from "node:url";
import { beforeAll, describe, expect, it } from "vitest";
import { NodeIO, type Document } from "@gltf-transform/core";
import { getBounds } from "@gltf-transform/functions";
import { ALL_EXTENSIONS } from "@gltf-transform/extensions";

let asset: Document;
beforeAll(async () => {
  asset = await new NodeIO()
    .registerExtensions(ALL_EXTENSIONS)
    .read(
      fileURLToPath(new URL("../../public/assets/ep1/krasue/krasue-creature.glb", import.meta.url)),
    );
});

describe("Krasue is a volumetric, articulated character", () => {
  it("exports a moving jaw, mouth rim and rigid upper/lower teeth", () => {
    const meshes = asset.getRoot().listMeshes();
    for (const name of ["krasue_sculpted_head", "krasue_lip_rims", "krasue_teeth"]) {
      let max = 0;
      for (const p of meshes.find((m) => m.getName() === name)!.listPrimitives()) {
        const target = p.listTargets()[0];
        expect(target).toBeTruthy();
        const delta = target.getAttribute("POSITION")!;
        const v: number[] = [];
        for (let i = 0; i < delta.getCount(); i++) {
          delta.getElement(i, v);
          max = Math.max(max, Math.abs(v[1]));
        }
        if (name === "krasue_teeth") {
          const indices = p.getIndices()!.getArray()!,
            a: number[] = [],
            b: number[] = [];
          for (let i = 0; i < indices.length; i += 3) {
            delta.getElement(indices[i], a);
            delta.getElement(indices[i + 1], b);
            for (let axis = 0; axis < 3; axis++) expect(a[axis]).toBeCloseTo(b[axis], 6);
          }
        }
      }
      // glTF up is Y. Lower jaw opens visibly in genuine 3D geometry.
      expect(max).toBeGreaterThan(name === "krasue_teeth" ? 0.03 : 0.06);
    }
  });
  it("has a closed sculpted skull with real profile depth and no alpha silhouette", () => {
    const head = asset
      .getRoot()
      .listMeshes()
      .find((m) => m.getName() === "krasue_sculpted_head")!;
    expect(head).toBeDefined();
    const positions = head.listPrimitives().map((p) => p.getAttribute("POSITION")!);
    let minX = Infinity,
      maxX = -Infinity,
      minZ = Infinity,
      maxZ = -Infinity;
    const point: number[] = [];
    for (const data of positions)
      for (let i = 0; i < data.getCount(); i++) {
        data.getElement(i, point);
        minX = Math.min(minX, point[0]);
        maxX = Math.max(maxX, point[0]);
        minZ = Math.min(minZ, point[2]);
        maxZ = Math.max(maxZ, point[2]);
      }
    expect(maxX - minX).toBeGreaterThan(0.28);
    expect(maxZ - minZ).toBeGreaterThan(0.28);
    expect(maxZ - minZ).toBeLessThan(0.5);
    for (const m of asset.getRoot().listMaterials()) expect(m.getAlphaMode()).toBe("OPAQUE");
    const face = asset
      .getRoot()
      .listMaterials()
      .find((m) => m.getName() === "M_krasue_face")!;
    expect(face.getBaseColorTexture()).toBeTruthy();
    expect(face.getNormalTexture()).toBeTruthy();
  });
  it("skins the hair and each hanging intestine to independent bone chains", () => {
    const joints = asset
      .getRoot()
      .listSkins()
      .flatMap((s) => s.listJoints().map((j) => j.getName()));
    for (const name of [
      "krasue_hair_00_0",
      "krasue_hair_17_3",
      "krasue_gut_0_0",
      "krasue_gut_4_4",
      "krasue_organs_1",
    ])
      expect(joints).toContain(name);
    for (const m of asset.getRoot().listMeshes())
      for (const p of m.listPrimitives()) {
        expect(p.getAttribute("JOINTS_0")).toBeTruthy();
        const weights = p.getAttribute("WEIGHTS_0")!;
        expect(weights).toBeTruthy();
        const sample: number[] = [];
        for (let i = 0; i < weights.getCount(); i += 17) {
          weights.getElement(i, sample);
          expect(sample.reduce((sum, v) => sum + v, 0)).toBeCloseTo(1, 3);
        }
      }
  });
  it("closes the head geometry rather than presenting a two-sided sheet", () => {
    const head = asset
      .getRoot()
      .listMeshes()
      .find((m) => m.getName() === "krasue_sculpted_head")!;
    const welded = new Map<string, number>(),
      edges = new Map<string, number>();
    const point: number[] = [];
    for (const primitive of head.listPrimitives()) {
      const positions = primitive.getAttribute("POSITION")!;
      const vertices: number[] = [];
      for (let i = 0; i < positions.getCount(); i++) {
        positions.getElement(i, point);
        const key = point.map((v) => Math.round(v * 1e6)).join(",");
        if (!welded.has(key)) welded.set(key, welded.size);
        vertices.push(welded.get(key)!);
      }
      const indices = primitive.getIndices()!.getArray()!;
      for (let i = 0; i < indices.length; i += 3) {
        const triangle = [vertices[indices[i]], vertices[indices[i + 1]], vertices[indices[i + 2]]];
        for (let e = 0; e < 3; e++) {
          const a = triangle[e],
            b = triangle[(e + 1) % 3];
          const key = a < b ? `${a}:${b}` : `${b}:${a}`;
          edges.set(key, (edges.get(key) ?? 0) + 1);
        }
      }
    }
    expect([...edges.values()].every((count) => count === 2)).toBe(true);
  });
  it("includes separate real organs and bounds its geometry budget", () => {
    const meshes = asset.getRoot().listMeshes();
    for (const name of [
      "krasue_heart",
      "krasue_lung_-1",
      "krasue_lung_1",
      "krasue_liver",
      "krasue_stomach",
      "krasue_intestine_4",
    ])
      expect(meshes.some((m) => m.getName() === name)).toBe(true);
    const triangles = meshes.reduce(
      (sum, m) => sum + m.listPrimitives().reduce((n, p) => n + p.getIndices()!.getCount() / 3, 0),
      0,
    );
    expect(triangles).toBeGreaterThan(80_000);
    expect(triangles).toBeLessThan(250_000);
    const bounds = getBounds(asset.getRoot().listScenes()[0]);
    expect(bounds.max[1] - bounds.min[1]).toBeGreaterThan(1.7);
    expect(bounds.max[2] - bounds.min[2]).toBeGreaterThan(0.3);
  });
  it("exports mottled tissue, wet surface material, folded membranes and coiled loops", () => {
    const meshes = asset.getRoot().listMeshes();
    for (const name of ["krasue_mesenteric_folds", "krasue_tracheal_ridges"])
      expect(meshes.some((m) => m.getName() === name)).toBe(true);
    const heart = meshes.find((m) => m.getName() === "krasue_heart")!.listPrimitives()[0];
    const colors = heart.getAttribute("COLOR_0")!;
    expect(colors).toBeTruthy();
    const color: number[] = [],
      reds: number[] = [];
    for (let i = 0; i < colors.getCount(); i += 11) {
      colors.getElement(i, color);
      reds.push(color[0]);
    }
    expect(Math.max(...reds) - Math.min(...reds)).toBeGreaterThan(0.01);
    expect(heart.getMaterial()!.getNormalTexture()).toBeTruthy();
    expect(heart.getMaterial()!.getRoughnessFactor()).toBeGreaterThan(0.45);
    const loop = meshes
      .find((m) => m.getName() === "krasue_intestine_0")!
      .listPrimitives()[0]
      .getAttribute("POSITION")!;
    const p: number[] = [],
      ys: number[] = [];
    for (let i = 0; i < loop.getCount(); i++) {
      loop.getElement(i, p);
      ys.push(p[1]);
    }
    expect(Math.max(...ys) - Math.min(...ys)).toBeLessThan(0.35);
  });
});
