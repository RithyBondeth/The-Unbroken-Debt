#!/usr/bin/env node
// Run after build-taxi.py. Optional argument: cabin or roadside.
import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
const requested = process.argv[2];
if (requested && !["cabin", "roadside"].includes(requested))
  throw new Error("Expected cabin or roadside");
const staging = mkdtempSync(join(tmpdir(), "unbroken-taxi-"));
const gltf = (...args) => execFileSync("npx", ["gltf-transform", ...args], { stdio: "inherit" });
try {
  for (const kind of requested ? [requested] : ["cabin", "roadside"]) {
    const name = `ep1_taxi_${kind}`,
      work = join(staging, `${name}.glb`);
    gltf("dedup", `art-export/ep1/${name}.glb`, work);
    gltf("weld", work, work);
    gltf("resize", work, work, "--width", "1024", "--height", "1024");
    gltf(
      "etc1s",
      work,
      work,
      "--slots",
      "@(baseColorTexture|emissiveTexture|occlusionTexture|metallicRoughnessTexture)",
    );
    gltf("uastc", work, work, "--slots", "normalTexture");
    gltf("meshopt", work, `public/assets/ep1/${name}.glb`);
  }
} finally {
  rmSync(staging, { recursive: true, force: true });
}
