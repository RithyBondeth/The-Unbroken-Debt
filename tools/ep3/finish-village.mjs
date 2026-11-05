// Idempotent corrections for older incremental exports.
import { NodeIO } from "@gltf-transform/core";
import { ALL_EXTENSIONS } from "@gltf-transform/extensions";
import { prune } from "@gltf-transform/functions";
import { MeshoptDecoder, MeshoptEncoder } from "meshoptimizer";
await Promise.all([MeshoptDecoder.ready, MeshoptEncoder.ready]);
const io = new NodeIO()
  .registerExtensions(ALL_EXTENSIONS)
  .registerDependencies({ "meshopt.decoder": MeshoptDecoder, "meshopt.encoder": MeshoptEncoder });
const path = "public/assets/ep3/ep3_area_village.glb",
  doc = await io.read(path);
let changed = 0;
let obsoleteHair = 0;
for (const node of doc.getRoot().listNodes()) {
  if (node.getName().startsWith("ep3_finish_kanha_hair")) {
    node.dispose();
    obsoleteHair++;
    continue;
  }
  if (
    !/^(clinic_facade|ward_sign|attic_sign|pump_label|safe_numerals|debt_name|tin_cross(?:\.\d+)?)$/.test(
      node.getName(),
    ) ||
    node.getExtras().ep3_lettering_corrected
  )
    continue;
  const scale = node.getScale();
  node.setScale([-scale[0], scale[1], scale[2]]);
  node.setExtras({ ...node.getExtras(), ep3_lettering_corrected: true });
  changed++;
}
if (obsoleteHair) await doc.transform(prune({ keepLeaves: true }));
if (changed || obsoleteHair) await io.write(path, doc);
console.info(`Episode 3 lettering: ${changed} corrected signs.`);
console.info(`Episode 3 hair: ${obsoleteHair} obsolete curtains removed.`);
