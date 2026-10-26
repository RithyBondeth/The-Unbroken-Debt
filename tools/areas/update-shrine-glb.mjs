#!/usr/bin/env node
// Copy a focused shrine rebuild into the current village, keeping its compressed textures.
// node tools/areas/update-shrine-glb.mjs village.glb shrine-only.glb output.glb
import { renameSync } from "node:fs";
import { NodeIO } from "@gltf-transform/core";
import { ALL_EXTENSIONS } from "@gltf-transform/extensions";
import { copyToDocument, prune, unpartition } from "@gltf-transform/functions";
import { MeshoptDecoder, MeshoptEncoder } from "meshoptimizer";

const [previous, rebuilt, output] = process.argv.slice(2);
if (!previous || !rebuilt || !output)
  throw new Error("Expected village.glb shrine-only.glb output.glb");
await Promise.all([MeshoptDecoder.ready, MeshoptEncoder.ready]);
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({
  "meshopt.decoder": MeshoptDecoder,
  "meshopt.encoder": MeshoptEncoder,
});
const [target, source] = await Promise.all([io.read(previous), io.read(rebuilt)]);
const canonical = (name) => name.replace(/\.\d+$/, "");
const materials = new Map(
  target
    .getRoot()
    .listMaterials()
    .map((m) => [canonical(m.getName()), m]),
);
const names = new Set([
  "banyan_cloth",
  "neakta_shrine",
  "neakta_stone_watch",
  "spirit_house",
  "col_neakta_shrine",
  "col_spirit_house",
  "light_flame_shrine",
  "marker_neakta",
  "marker_flies",
  "ground_offering_0",
  "ground_offering_1",
]);
const nodes = source
  .getRoot()
  .listNodes()
  .filter((n) => names.has(n.getName()));
if (!nodes.length) throw new Error(`Expected ${names.size} focused nodes; got ${nodes.length}`);
const updates = new Map(nodes.map((n) => [n.getName(), n]));
const unchanged = new Map(
  target
    .getRoot()
    .listNodes()
    .filter((n) => !names.has(n.getName()))
    .map((n) => [
      n,
      {
        matrix: JSON.stringify(n.getMatrix()),
        mesh: n.getMesh(),
        extras: JSON.stringify(n.getExtras()),
      },
    ]),
);
for (const ext of source.getRoot().listExtensionsUsed()) {
  if (
    !target
      .getRoot()
      .listExtensionsUsed()
      .some((e) => e.extensionName === ext.extensionName)
  )
    target.createExtension(ext.constructor).setRequired(ext.isRequired());
}
const copied = copyToDocument(target, source, nodes.map((n) => n.getMesh()).filter(Boolean));
for (const original of nodes.map((n) => n.getMesh()).filter(Boolean)) {
  for (const primitive of copied.get(original).listPrimitives()) {
    const imported = primitive.getMaterial();
    if (!imported) continue;
    // Chicken skin owns its image maps; carry its newly authored textures through.
    if (/^M_(chicken|ancestor)_/.test(imported.getName())) continue;
    const existing = materials.get(canonical(imported.getName()));
    if (!existing && imported.getName().startsWith("M_shrine_")) continue;
    if (!existing) throw new Error(`Unexpected new material: ${imported.getName()}`);
    if (canonical(existing.getName()).startsWith("M_shrine_")) {
      existing.setBaseColorFactor(imported.getBaseColorFactor());
      existing.setRoughnessFactor(imported.getRoughnessFactor());
      existing.setMetallicFactor(imported.getMetallicFactor());
    }
    primitive.setMaterial(existing);
  }
}
let updated = 0;
for (const node of target.getRoot().listNodes()) {
  const replacement = updates.get(node.getName());
  if (!replacement) continue;
  if (replacement.getMesh()) node.setMesh(copied.get(replacement.getMesh()));
  node.setTranslation(replacement.getTranslation());
  node.setRotation(replacement.getRotation());
  node.setScale(replacement.getScale());
  node.setExtras(replacement.getExtras());
  updated++;
}
if (updated !== nodes.length) throw new Error(`Only updated ${updated} shrine nodes`);
for (const [node, before] of unchanged)
  if (
    JSON.stringify(node.getMatrix()) !== before.matrix ||
    node.getMesh() !== before.mesh ||
    JSON.stringify(node.getExtras()) !== before.extras
  )
    throw new Error(`Unrelated village node changed: ${node.getName()}`);
await target.transform(prune({ keepLeaves: true }), unpartition());
const temporary = output + ".tmp.glb";
await io.write(temporary, target);
renameSync(temporary, output);
console.log(
  `Updated ${updated} shrine nodes; reused compressed materials and preserved the rest of the village.`,
);
