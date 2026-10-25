import { fileURLToPath } from "node:url";
import { beforeAll, describe, expect, it } from "vitest";
import { NodeIO, type Document } from "@gltf-transform/core";
import { getBounds } from "@gltf-transform/functions";
import { ALL_EXTENSIONS } from "@gltf-transform/extensions";
import { MeshoptDecoder } from "meshoptimizer";

let asset: Document;
beforeAll(async () => {
  await MeshoptDecoder.ready;
  asset = await new NodeIO()
    .registerExtensions(ALL_EXTENSIONS)
    .registerDependencies({ "meshopt.decoder": MeshoptDecoder })
    .read(fileURLToPath(new URL("../../public/assets/ep1/neakta_shadow.glb", import.meta.url)));
});
describe("authored ancestral effigy asset", () => {
  it("keeps the 2.5 metre foot origin required by all three encounters", () => {
    const bounds = getBounds(asset.getRoot().listScenes()[0]);
    expect(bounds.min[1]).toBeGreaterThan(-0.015);
    expect(bounds.min[1]).toBeLessThan(0.015);
    expect(bounds.max[1]).toBeCloseTo(2.5, 2);
    expect(bounds.max[2] - bounds.min[2]).toBeGreaterThan(0.3);
  });
  it("ships complete anatomical geometry and image-backed paint and cloth", () => {
    const meshes = asset.getRoot().listMeshes();
    const body = meshes.find((m) => m.getName().includes("anatomy"))!;
    expect(body).toBeDefined();
    const primitive = body.listPrimitives()[0];
    expect(primitive.getAttribute("POSITION")!.getCount()).toBeGreaterThan(20_000);
    expect(primitive.getAttribute("NORMAL")).toBeTruthy();
    expect(primitive.getAttribute("TEXCOORD_0")).toBeTruthy();
    const mats = asset.getRoot().listMaterials();
    for (const pattern of [/painted_mineral/, /saffron_cotton/, /earth_cotton/]) {
      const mat = mats.find((m) => pattern.test(m.getName()))!;
      expect(mat.getBaseColorTexture()).toBeTruthy();
      expect(mat.getNormalTexture()).toBeTruthy();
    }
    expect(
      asset
        .getRoot()
        .listNodes()
        .filter((n) => n.getName().includes("inset_eye")),
    ).toHaveLength(2);
  });
  it("uses baked poses and cloth without live skeleton or cloth simulation", () => {
    expect(asset.getRoot().listSkins()).toHaveLength(0);
    expect(asset.getRoot().listAnimations()).toHaveLength(0);
    expect(asset.getRoot().listMeshes().length).toBeLessThan(14);
    const triangles = asset
      .getRoot()
      .listMeshes()
      .reduce(
        (total, mesh) =>
          total +
          mesh
            .listPrimitives()
            .reduce((sum, primitive) => sum + primitive.getIndices()!.getCount() / 3, 0),
        0,
      );
    expect(triangles).toBeLessThanOrEqual(60_000);
  });
});
