// One-time focused correction for the first pagoda export. Full rebuilds author this root.
import { NodeIO } from "@gltf-transform/core";
import { ALL_EXTENSIONS } from "@gltf-transform/extensions";
import { MeshoptDecoder, MeshoptEncoder } from "meshoptimizer";
await Promise.all([MeshoptDecoder.ready, MeshoptEncoder.ready]);
const io = new NodeIO()
  .registerExtensions(ALL_EXTENSIONS)
  .registerDependencies({ "meshopt.decoder": MeshoptDecoder, "meshopt.encoder": MeshoptEncoder });
const file = "public/assets/ep2/ep2_area_pagoda.glb";
const doc = await io.read(file);
for (const scene of doc.getRoot().listScenes()) {
  if (scene.listChildren().some((n) => n.getName() === "pagoda_axes")) continue;
  const children = scene.listChildren();
  const root = doc.createNode("pagoda_axes").setScale([-1, 1, 1]);
  for (const node of children) {
    scene.removeChild(node);
    root.addChild(node);
  }
  scene.addChild(root);
}
for (const node of doc.getRoot().listNodes())
  if (node.getName().startsWith("col_")) node.setExtras({ surface: "stone", ...node.getExtras() });
await io.write(file, doc);
console.info("Pagoda world axes and collider surfaces corrected.");
