#!/usr/bin/env node
// Keep the existing compressed scenery while copying newly built guardians.
// Usage: node tools/areas/update-guardian-glb.mjs previous.glb rebuilt.glb output.glb
// Both inputs must describe the same village. Concurrent prop relocations are
// retained from the rebuilt file; all unrelated mesh and texture data stays intact.
import { NodeIO } from "@gltf-transform/core";
import { ALL_EXTENSIONS } from "@gltf-transform/extensions";
import { copyToDocument, prune, unpartition } from "@gltf-transform/functions";
import { MeshoptDecoder, MeshoptEncoder } from "meshoptimizer";

const [previous, rebuilt, output] = process.argv.slice(2);
if (!previous || !rebuilt || !output)
  throw new Error("Expected previous.glb rebuilt.glb output.glb");
await Promise.all([MeshoptDecoder.ready, MeshoptEncoder.ready]);
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({
  "meshopt.decoder": MeshoptDecoder,
  "meshopt.encoder": MeshoptEncoder,
});
const [target, source] = await Promise.all([io.read(previous), io.read(rebuilt)]);
for (const ext of source.getRoot().listExtensionsUsed()) {
  target.createExtension(ext.constructor).setRequired(ext.isRequired());
}
const nodes = new Map(
  source
    .getRoot()
    .listNodes()
    .map((node) => [node.getName(), node]),
);
const guardians = source
  .getRoot()
  .listNodes()
  .filter((node) => /^tingmong_\d+$/.test(node.getName()));
if (guardians.length !== 5) throw new Error(`Expected five guardians; got ${guardians.length}`);
const meshes = guardians.map((node) => node.getMesh());
if (meshes.some((mesh) => !mesh)) throw new Error("Guardian mesh missing");
const copied = copyToDocument(target, source, meshes);
let replaced = 0;
for (const node of target.getRoot().listNodes()) {
  const updated = nodes.get(node.getName());
  if (!updated) continue;
  if (/^tingmong_\d+$/.test(node.getName())) {
    node.setMesh(copied.get(updated.getMesh()));
    node.setTranslation(updated.getTranslation());
    node.setRotation(updated.getRotation());
    node.setScale(updated.getScale());
    node.setExtras(updated.getExtras());
    replaced++;
  } else if (/^ground_offering_\d+$/.test(node.getName())) {
    // These props may be moved by a separate path-clearance edit in the workspace.
    node.setTranslation(updated.getTranslation());
    node.setRotation(updated.getRotation());
    node.setScale(updated.getScale());
  }
}
if (replaced !== 5) throw new Error(`Only replaced ${replaced} guardian nodes`);
await target.transform(prune({ keepLeaves: true }), unpartition());
await io.write(output, target);
console.log(`Updated ${replaced} guardians; retained existing compressed scenery.`);
