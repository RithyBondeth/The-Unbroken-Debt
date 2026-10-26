#!/usr/bin/env node
// Point the shipped house-post material at the weathered teak maps the village already
// holds (M_wet_rough_posts), with the tint authored in ep1_area_village.py.
// node tools/areas/update-house-posts-glb.mjs village.glb output.glb
import { renameSync } from "node:fs";
import { NodeIO } from "@gltf-transform/core";
import { ALL_EXTENSIONS } from "@gltf-transform/extensions";
import { prune } from "@gltf-transform/functions";
import { MeshoptDecoder, MeshoptEncoder } from "meshoptimizer";

const [input, output] = process.argv.slice(2);
if (!output) throw new Error("Expected village.glb output.glb");
await Promise.all([MeshoptDecoder.ready, MeshoptEncoder.ready]);
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({
  "meshopt.decoder": MeshoptDecoder,
  "meshopt.encoder": MeshoptEncoder,
});
const doc = await io.read(input);
const materials = doc.getRoot().listMaterials();
const target = materials.find((m) => m.getName() === "M_house_posts");
const donor = materials.find((m) => m.getName() === "M_wet_rough_posts");
if (!target || !donor) throw new Error("M_house_posts or M_wet_rough_posts missing");
target
  .setBaseColorTexture(donor.getBaseColorTexture())
  .setNormalTexture(donor.getNormalTexture())
  .setOcclusionTexture(donor.getOcclusionTexture())
  .setMetallicRoughnessTexture(donor.getMetallicRoughnessTexture())
  .setBaseColorFactor([0.66, 0.6, 0.54, 1])
  .setRoughnessFactor(donor.getRoughnessFactor())
  .setMetallicFactor(donor.getMetallicFactor());
for (const [slot, info] of [
  [target.getBaseColorTextureInfo(), donor.getBaseColorTextureInfo()],
  [target.getNormalTextureInfo(), donor.getNormalTextureInfo()],
  [target.getOcclusionTextureInfo(), donor.getOcclusionTextureInfo()],
  [target.getMetallicRoughnessTextureInfo(), donor.getMetallicRoughnessTextureInfo()],
])
  if (slot && info) slot.copy(info);
await doc.transform(prune({ keepLeaves: true }));
const temporary = output + ".tmp.glb";
await io.write(temporary, doc);
renameSync(temporary, output);
console.log("M_house_posts now uses the weathered teak maps.");
