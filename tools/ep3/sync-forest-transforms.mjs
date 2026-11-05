// Incremental transform-only repair; full exports already contain these values.
import { readFile, rename } from "node:fs/promises";
import { NodeIO } from "@gltf-transform/core";
import { ALL_EXTENSIONS } from "@gltf-transform/extensions";
import { MeshoptDecoder, MeshoptEncoder } from "meshoptimizer";

if (!process.argv[2]) throw new Error("Pass the transform JSON from finalize-dread.py");
const transforms = JSON.parse(await readFile(process.argv[2], "utf8"));
await Promise.all([MeshoptDecoder.ready, MeshoptEncoder.ready]);
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({
  "meshopt.decoder": MeshoptDecoder,
  "meshopt.encoder": MeshoptEncoder,
});
for (const path of [
  "art-export/ep3/ep3_area_village.glb",
  "public/assets/ep3/ep3_area_village.glb",
]) {
  const document = await io.read(path);
  let changed = 0;
  for (const node of document.getRoot().listNodes()) {
    const transform = transforms[node.getName()];
    if (!transform) continue;
    node.setTranslation(transform.translation).setScale(transform.scale);
    changed++;
  }
  if (changed !== Object.keys(transforms).length)
    throw new Error(`Forest roots missing in ${path}`);
  await io.write(path + ".tmp.glb", document);
  await rename(path + ".tmp.glb", path);
  console.info(`${path}: ${changed} rooted canopy transforms`);
}
