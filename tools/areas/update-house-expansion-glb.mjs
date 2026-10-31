#!/usr/bin/env node
// Merge the focused house-expansion export (rebuild-house-expansion.py) without altering other village art.
// node tools/areas/update-house-expansion-glb.mjs village.glb house-expansion.glb manifest.json output.glb
import { readFileSync, renameSync, statSync } from "node:fs";
import { NodeIO } from "@gltf-transform/core";
import { ALL_EXTENSIONS } from "@gltf-transform/extensions";
import { copyToDocument, prune, unpartition } from "@gltf-transform/functions";
import { MeshoptDecoder, MeshoptEncoder } from "meshoptimizer";

const [previous, rebuilt, manifestPath, output] = process.argv.slice(2);
if (!output) throw new Error("Expected village.glb house-expansion.glb manifest.json output.glb");
const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
const previousStamp = statSync(previous).mtimeMs;
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
// Include new names so a focused export can be applied again safely.
const remove = new Set([...manifest.remove, ...manifest.required]);
const untouched = target
  .getRoot()
  .listNodes()
  .filter((n) => !remove.has(n.getName()));
const snapshot = new Map(
  untouched.map((n) => [
    n,
    JSON.stringify({
      name: n.getName(),
      matrix: n.getMatrix(),
      extras: n.getExtras(),
      mesh: n.getMesh()?.getName(),
    }),
  ]),
);
for (const node of target.getRoot().listNodes()) if (remove.has(node.getName())) node.dispose();
for (const ext of source.getRoot().listExtensionsUsed()) {
  if (
    !target
      .getRoot()
      .listExtensionsUsed()
      .some((e) => e.extensionName === ext.extensionName)
  )
    target.createExtension(ext.constructor).setRequired(ext.isRequired());
}
const nodes = source.getRoot().listNodes();
const existingNames = new Set(
  target
    .getRoot()
    .listNodes()
    .map((n) => n.getName()),
);
for (const node of nodes)
  if (existingNames.has(node.getName()))
    throw new Error(`Name collides with unrelated art: ${node.getName()}`);
const copied = copyToDocument(target, source, nodes);
for (const original of source.getRoot().listMeshes()) {
  const mesh = copied.get(original);
  if (!mesh) continue;
  for (const primitive of mesh.listPrimitives()) {
    const imported = primitive.getMaterial();
    if (!imported || imported.getName().startsWith("M_house_detail_")) continue;
    const existing = materials.get(canonical(imported.getName()));
    // The new rooms bring a few surfaces the village did not use yet; keep those as imported.
    if (existing) primitive.setMaterial(existing);
    else console.log(`New material: ${imported.getName()}`);
  }
}
const scene = target.getRoot().getDefaultScene() ?? target.getRoot().listScenes()[0];
for (const sourceScene of source.getRoot().listScenes())
  for (const child of sourceScene.listChildren()) scene.addChild(copied.get(child));
for (const [node, before] of snapshot) {
  const after = JSON.stringify({
    name: node.getName(),
    matrix: node.getMatrix(),
    extras: node.getExtras(),
    mesh: node.getMesh()?.getName(),
  });
  if (before !== after) throw new Error(`Unrelated art changed: ${node.getName()}`);
}
const finalNames = new Set(
  target
    .getRoot()
    .listNodes()
    .map((n) => n.getName()),
);
for (const name of manifest.required)
  if (!finalNames.has(name)) throw new Error(`Missing gameplay node: ${name}`);
await target.transform(prune({ keepLeaves: true }), unpartition());
const temporary = output + ".tmp.glb";
await io.write(temporary, target);
if (statSync(previous).mtimeMs !== previousStamp)
  throw new Error("Village changed during the merge; rerun against the latest file");
renameSync(temporary, output);
console.log(
  `Replaced ${remove.size} house-expansion nodes with ${nodes.length}; preserved ${snapshot.size} unrelated nodes.`,
);
