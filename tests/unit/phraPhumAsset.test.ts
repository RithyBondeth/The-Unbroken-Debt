import { fileURLToPath } from "node:url";
import { expect, it } from "vitest";
import { NodeIO } from "@gltf-transform/core";
import { getBounds } from "@gltf-transform/functions";
import { ALL_EXTENSIONS } from "@gltf-transform/extensions";
import { MeshoptDecoder } from "meshoptimizer";

/** glTF is Y up with the doorway toward +Z (the game's +Z); Blender built it facing -Y. */
it("ships the carved spirit house with its three candle wicks where the save point lights them", async () => {
  await MeshoptDecoder.ready;
  const asset = await new NodeIO()
    .registerExtensions(ALL_EXTENSIONS)
    .registerDependencies({ "meshopt.decoder": MeshoptDecoder })
    .read(fileURLToPath(new URL("../../public/assets/ep1/phra_phum.glb", import.meta.url)));
  const root = asset.getRoot();
  const bounds = getBounds(root.listScenes()[0]);
  // The laterite block is sunk a few centimetres into the earth; the horn finials
  // stop below 2.8 m; the tray fits inside the 1.34 x 1.05 m collider.
  expect(bounds.min[1]).toBeLessThan(0);
  expect(bounds.min[1]).toBeGreaterThan(-0.12);
  expect(bounds.max[1]).toBeLessThan(2.8);
  expect(bounds.max[0] - bounds.min[0]).toBeLessThan(1.5);
  const wick = (name: string) =>
    root
      .listNodes()
      .find((n) => n.getName() === `phra_phum_wick_${name}`)!
      .getTranslation();
  const [lx, ly, lz] = wick("left"),
    [rx, ry, rz] = wick("right"),
    [ix, iy, iz] = wick("inner");
  for (const [x, y, z] of [
    [lx, ly, lz],
    [rx, ry, rz],
  ]) {
    expect(Math.abs(Math.abs(x) - 0.44)).toBeLessThan(0.01);
    expect(Math.abs(y - 1.278)).toBeLessThan(0.012);
    expect(Math.abs(z - 0.35)).toBeLessThan(0.012);
  }
  expect(lx * rx).toBeLessThan(0);
  // The chamber is empty but for one candle, on the 1.29 m floor behind the doorway.
  expect(Math.abs(ix)).toBeLessThan(0.02);
  expect(iy).toBeGreaterThan(1.33);
  expect(iy).toBeLessThan(1.45);
  expect(iz).toBeLessThan(0);
  const names = root.listMaterials().map((m) => m.getName());
  expect(names).toContain("M_phra_phum_offering_clay");
  expect(names).toContain("M_phra_phum_red_lacquer_teak");
  const gilt = root.listMaterials().find((m) => m.getName() === "M_phra_phum_gilt_carving")!;
  expect(gilt.getBaseColorTexture()).toBeTruthy();
  expect(gilt.getNormalTexture()).toBeTruthy();
  expect(gilt.getMetallicRoughnessTexture()).toBeTruthy();
  // A few dozen draw calls and a focal object's triangle budget.
  let primitives = 0,
    triangles = 0;
  for (const mesh of root.listMeshes())
    for (const p of mesh.listPrimitives()) {
      primitives++;
      triangles += p.getIndices()!.getCount() / 3;
      expect(p.getAttribute("NORMAL")).toBeTruthy();
      if (p.getMaterial()?.getBaseColorTexture()) expect(p.getAttribute("TEXCOORD_0")).toBeTruthy();
    }
  expect(primitives).toBeLessThan(30);
  expect(triangles).toBeLessThan(130000);
  expect(root.listMaterials().every((m) => m.getName() !== "effigy")).toBe(true);
});
