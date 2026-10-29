import { fileURLToPath } from "node:url";
import { expect, it } from "vitest";
import { NodeIO } from "@gltf-transform/core";
import { getBounds } from "@gltf-transform/functions";
import { ALL_EXTENSIONS } from "@gltf-transform/extensions";
import { MeshoptDecoder } from "meshoptimizer";

it("ships a miniature carved timber asset with a rigid neck pivot and complete PBR maps", async () => {
  await MeshoptDecoder.ready;
  const asset = await new NodeIO()
    .registerExtensions(ALL_EXTENSIONS)
    .registerDependencies({ "meshopt.decoder": MeshoptDecoder })
    .read(fileURLToPath(new URL("../../public/assets/ep1/phra_phum_effigy.glb", import.meta.url)));
  const root = asset.getRoot(),
    bounds = getBounds(root.listScenes()[0]);
  expect(bounds.min[1]).toBeCloseTo(0, 3);
  expect(bounds.max[1]).toBeGreaterThan(0.45);
  expect(bounds.max[1]).toBeLessThan(0.5);
  expect(bounds.max[0] - bounds.min[0]).toBeLessThan(0.3);
  const head = root.listNodes().find((n) => n.getName() === "effigy_head_joint")!;
  expect(head.getTranslation()[1]).toBeCloseTo(0.331, 3);
  expect(root.listSkins()).toHaveLength(0);
  expect(root.listMaterials()).toHaveLength(1);
  const wood = root.listMaterials()[0];
  expect(wood.getName()).toContain("split_wood");
  expect(wood.getBaseColorTexture()).toBeTruthy();
  expect(wood.getNormalTexture()).toBeTruthy();
  expect(wood.getMetallicFactor()).toBe(0);
  expect(wood.getRoughnessFactor()).toBeGreaterThan(0.8);
  let triangles = 0;
  for (const mesh of root.listMeshes())
    for (const p of mesh.listPrimitives()) {
      triangles += p.getIndices()!.getCount() / 3;
      expect(p.getMaterial()).toBe(wood);
      expect(p.getAttribute("NORMAL")).toBeTruthy();
      expect(p.getAttribute("TEXCOORD_0")).toBeTruthy();
    }
  expect(triangles).toBeLessThan(80000);
});
