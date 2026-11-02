#!/usr/bin/env node
// Run after build-taxi.py. Optional argument: cabin or roadside.
import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
const requested = process.argv[2];
if (requested && !["cabin", "roadside"].includes(requested))
  throw new Error("Expected cabin or roadside");
const PROPS =
  "{clay_*,weathered_planks_*,old_planks_*,rough_linen_*,dark_wood_*,T_ep1_tingmong_*,T_ep1_offering_*,T_ep1_banana_*,T_ep1_flag_*,shrub_02_*,fern_02_*,brown_mud_leaves_*,red_dirt_mud_*,clay_roof_*}";
const PROP_RELIEF =
  "{clay_*_N,weathered_planks_N,old_planks_02_N,rough_linen_N,dark_wood_N,T_ep1_tingmong_weave_N,T_ep1_offering_leaf_N,shrub_02_nor_gl_1k,fern_02_nor_gl_1k,brown_mud_leaves_01_N,red_dirt_mud_01_N}";
const staging = mkdtempSync(join(tmpdir(), "unbroken-taxi-"));
const gltf = (...args) => execFileSync("npx", ["gltf-transform", ...args], { stdio: "inherit" });
try {
  for (const kind of requested ? [requested] : ["cabin", "roadside"]) {
    const name = `ep1_taxi_${kind}`,
      work = join(staging, `${name}.glb`);
    gltf("dedup", `art-export/ep1/${name}.glb`, work);
    gltf("weld", work, work);
    gltf("resize", work, work, "--width", "1024", "--height", "1024");
    // The driver's shirt folds and combed hair read at 512 and 256 px; their relief
    // maps are the cabin's heaviest.
    if (kind === "cabin") {
      gltf(
        "resize",
        work,
        work,
        "--width",
        "512",
        "--height",
        "512",
        "--pattern",
        "male_casualsuit01_normal",
      );
      gltf(
        "resize",
        work,
        work,
        "--width",
        "256",
        "--height",
        "256",
        "--pattern",
        "short02_normal",
      );
    }
    // Roadside set dressing is seen in passing: its maps share a smaller budget.
    if (kind === "roadside") {
      gltf("resize", work, work, "--width", "512", "--height", "512", "--pattern", PROPS);
      gltf("resize", work, work, "--width", "256", "--height", "256", "--pattern", PROP_RELIEF);
    }
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
