#!/usr/bin/env node
// Merge only the focused forest, retaining the compressed village and gameplay.
import { readFileSync, renameSync } from "node:fs";
import { NodeIO } from "@gltf-transform/core";
import { ALL_EXTENSIONS } from "@gltf-transform/extensions";
import { copyToDocument, prune, unpartition } from "@gltf-transform/functions";
import { MeshoptDecoder, MeshoptEncoder } from "meshoptimizer";

const [previous, rebuilt, manifestPath, output] = process.argv.slice(2);
if (!output) throw new Error("Expected village.glb forest.glb manifest.json output.glb");
const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
if (!manifest.created.length || !manifest.required.length) throw new Error("Empty forest manifest");
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
const remove = new Set(manifest.remove);
const snapshot = new Map(
  target
    .getRoot()
    .listNodes()
    .filter((n) => !remove.has(n.getName()))
    .map((n) => [
      n,
      {
        matrix: JSON.stringify(n.getMatrix()),
        mesh: n.getMesh(),
        extras: JSON.stringify(n.getExtras()),
      },
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
const expected = new Set(manifest.created);
for (const node of nodes)
  if (!expected.has(node.getName())) throw new Error(`Unexpected forest node: ${node.getName()}`);
if (nodes.length !== expected.size) throw new Error("Focused export is missing forest nodes");
const oldTrunks = target
  .getRoot()
  .listNodes()
  .filter((n) => /^col_tree_\d+$/.test(n.getName()));
const trunkNames = manifest.treeColliders ? new Set(manifest.treeColliders) : null;
const newTrunks = nodes.filter((n) =>
  trunkNames ? trunkNames.has(n.getName()) : /^col_tree_6\d\d$/.test(n.getName()),
);
if (newTrunks.length !== (trunkNames?.size ?? 16))
  throw new Error(`Secondary tree collider count does not match the forest manifest`);
for (const trunk of newTrunks) {
  const a = trunk.getWorldTranslation();
  for (const other of [...oldTrunks, ...newTrunks]) {
    if (other === trunk) continue;
    const b = other.getWorldTranslation();
    if (Math.hypot(a[0] - b[0], a[2] - b[2]) < 4.48)
      throw new Error(`Trees overlap: ${trunk.getName()} / ${other.getName()}`);
  }
}
const existingNames = new Set(
  target
    .getRoot()
    .listNodes()
    .map((n) => n.getName()),
);
for (const node of nodes)
  if (existingNames.has(node.getName()))
    throw new Error(`Unrelated node collision: ${node.getName()}`);
const copied = copyToDocument(target, source, nodes);
for (const original of source.getRoot().listMeshes()) {
  const mesh = copied.get(original);
  if (!mesh) continue;
  for (const primitive of mesh.listPrimitives()) {
    const imported = primitive.getMaterial();
    if (!imported || (imported.getName().startsWith("M_forest_") && !manifest.reuseForestMaterials))
      continue;
    const existing = materials.get(canonical(imported.getName()));
    if (!existing) throw new Error(`Unexpected new material: ${imported.getName()}`);
    primitive.setMaterial(existing);
  }
}
const scene = target.getRoot().getDefaultScene() ?? target.getRoot().listScenes()[0];
for (const sourceScene of source.getRoot().listScenes())
  for (const child of sourceScene.listChildren()) scene.addChild(copied.get(child));
for (const [node, before] of snapshot)
  if (
    JSON.stringify(node.getMatrix()) !== before.matrix ||
    node.getMesh() !== before.mesh ||
    JSON.stringify(node.getExtras()) !== before.extras
  )
    throw new Error(`Unrelated village node changed: ${node.getName()}`);
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
renameSync(temporary, output);
console.log(`Merged ${nodes.length} forest nodes; preserved ${snapshot.size} unrelated nodes.`);
