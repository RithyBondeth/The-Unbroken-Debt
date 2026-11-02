// Correct the first export's sculpt material while retaining its compressed geometry.
// Full area rebuilds use the same seamless library maps in ep2_area_pagoda.py.
import { NodeIO } from "@gltf-transform/core";
import { ALL_EXTENSIONS } from "@gltf-transform/extensions";
import { MeshoptDecoder, MeshoptEncoder } from "meshoptimizer";
await Promise.all([MeshoptDecoder.ready, MeshoptEncoder.ready]);
const io = new NodeIO()
  .registerExtensions(ALL_EXTENSIONS)
  .registerDependencies({ "meshopt.decoder": MeshoptDecoder, "meshopt.encoder": MeshoptEncoder });
const file = "public/assets/ep2/ep2_area_pagoda.glb",
  doc = await io.read(file);
const mats = doc.getRoot().listMaterials(),
  skin = mats.find((m) => m.getName() === "M_ep2_ancestor_skin"),
  stone = mats.find((m) => m.getName() === "M_ep2_stone");
if (!skin || !stone) throw new Error("Pagoda skin/stone material missing");
skin
  .setBaseColorTexture(stone.getBaseColorTexture())
  .setNormalTexture(stone.getNormalTexture())
  .setNormalScale(0.6)
  .setBaseColorFactor([0.65, 0.6, 0.5, 1])
  .setMetallicFactor(0)
  .setRoughnessFactor(0.9);
await io.write(file, doc);
console.info("Pret sculpt uses seamless weathered surface maps.");
