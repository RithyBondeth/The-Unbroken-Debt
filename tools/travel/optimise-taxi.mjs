#!/usr/bin/env node
// Run after build-taxi.py. Optional argument: cabin or roadside.
import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { NodeIO } from "@gltf-transform/core";
import { ALL_EXTENSIONS } from "@gltf-transform/extensions";
import { textureCompress } from "@gltf-transform/functions";
import sharp from "sharp";
const requested = process.argv[2];
if (requested && !["cabin", "roadside"].includes(requested))
  throw new Error("Expected cabin or roadside");
const PROPS =
  "{clay_*,weathered_planks_*,weathered_brown_planks_*,old_planks_*,rough_linen_*,dark_wood_*,wood_shutter_*,wood_table_worn_*,rusty_metal_*,bark_brown_02_N,effigy-painted-*,cotton-*,T_ep1_tingmong_*,T_ep1_offering_*,T_ep1_banana_*,T_ep1_flag_*,T_ep1_forest_leaf_*,T_ep1_hol_silk_*,T_ep1_krama_check_*,T_ep1_kantel_mat_*,T_ep1_paper_news_*,bamboo_wall_*,red_brick_*,yellow_plaster_*,painted_plaster_wall_*,concrete_floor_worn_001_*,thatch_roof_angled_*,shrub_02_*,fern_02_*,brown_mud_leaves_*,red_dirt_mud_*,clay_roof_*,muddy_tracks_N,red_laterite_soil_stones_N}";
const PROP_RELIEF =
  "{clay_*_N,weathered_planks_N,weathered_brown_planks_N,old_planks_02_N,rough_linen_N,dark_wood_N,wood_shutter_N,wood_table_worn_N,rusty_metal_N,bamboo_wall_N,red_brick_N,yellow_plaster_N,painted_plaster_wall_N,concrete_floor_worn_001_N,thatch_roof_angled_N,T_ep1_tingmong_weave_N,T_ep1_offering_leaf_N,T_ep1_forest_leaf_N,shrub_02_nor_gl_1k,fern_02_nor_gl_1k,brown_mud_leaves_01_N,red_dirt_mud_01_N}";
// The paddies' scans stand 15 m and more from the road: palm, stilt houses, bananas,
// ep1-refine scanned forest trees, sugar palms, roadside shop props, scarecrows, and the shrine's offerings.
const FAR_SCANS = [
  "Wash_*",
  "Wahs_*",
  "set1_*",
  "banana_leef*",
  "T_ep1_chicken_*",
  "ep1_flora_*",
  "shop_prop_*",
  "Cluster*",
  "Vines*",
  "BarkB*",
  "Cortex*",
  "Leaf*",
  "Stem*",
  "Cooking_pot*",
  "M_Broom*",
  "M_Jar*",
  "M_Bamboo_Basket*",
  "Traditionalbamboo*",
  "*_baseColor",
  "*_normal",
  "*_metallicRoughness",
];
// One pattern each: the CLI splits a brace list without wildcards into separate arguments.
const CAR_FAR = ["M_gardeboue_*", "M_detailled_*"];
const CAR_RELIEF = [
  "M_external_normal",
  "M_door_normal",
  "rough_linen_N",
  "dirty_carpet_N",
  "rusty_metal_N",
  "quatrefoil_jacquard_fabric_N",
  "rosewood_veneer1_N",
  "brown_leather_N",
  "red_dirt_mud_01_N",
];
// The people are seen at arm's length: the photoscanned driver (head, shirt, hands) and
// Sora's own legs keep 2048 px colour and relief; the driver's face keeps UASTC colour
// (ETC1S blocks smear pores and stubble).
// (The CLI's --pattern cannot exclude names, so the 1024 px cap runs through the API.)
// (A name is tested, and the empty URI must not pass: hence the trailing ".")
const NOT_PEOPLE = /^(?!rp_|T_taxi_driver_head_|T_taxi_sora_|T_taxi_khmer_posters)./;
const PEOPLE_2K = ["rp_*", "T_taxi_sora_*", "T_taxi_driver_head_BC"];
const FACE = "T_taxi_driver_head_BC";
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS);
// No tangents ship: with them the instanced trim needs more than WebGPU's eight vertex
// buffers, and the face's blend shapes lose their tangent frame (an older export had them).
async function noTangents(path) {
  const doc = await io.read(path);
  for (const mesh of doc.getRoot().listMeshes())
    for (const primitive of mesh.listPrimitives()) primitive.setAttribute("TANGENT", null);
  await io.write(path, doc);
}
async function capAt1024(path, kind) {
  const doc = await io.read(path);
  await doc.transform(
    textureCompress({ encoder: sharp, resize: [1024, 1024], pattern: NOT_PEOPLE }),
  );
  if (kind === "roadside") {
    // Distant flora & small passing veranda props keep crisp colour maps while trimming
    // UASTC normal relief to 128 px (~4x smaller with zero visible loss at driving distance).
    await doc.transform(
      textureCompress({
        encoder: sharp,
        resize: [128, 128],
        slots: /^normalTexture$/,
        pattern:
          /^(ep1_flora_|shop_prop_|Wash_|Wahs_|set1_|clay_roof_|red_brick_|thatch_roof_|bamboo_wall_|concrete_floor_|yellow_plaster_|wood_table_|weathered_brown_planks_)/,
      }),
    );
  }
  await io.write(path, doc);
}
const staging = mkdtempSync(join(tmpdir(), "unbroken-taxi-"));
const gltf = (...args) => execFileSync("npx", ["gltf-transform", ...args], { stdio: "inherit" });
try {
  for (const kind of requested ? [requested] : ["cabin", "roadside"]) {
    const name = `ep1_taxi_${kind}`,
      work = join(staging, `${name}.glb`);
    gltf("dedup", `art-export/ep1/${name}.glb`, work);
    gltf("weld", work, work);
    if (kind === "cabin") await noTangents(work);
    await capAt1024(work, kind);
    if (kind === "cabin") {
      for (const pattern of PEOPLE_2K)
        gltf("resize", work, work, "--width", "2048", "--height", "2048", "--pattern", pattern);
      gltf(
        "resize",
        work,
        work,
        "--width",
        "1024",
        "--height",
        "1024",
        "--pattern",
        "T_taxi_driver_head_[NR]",
      );
    }
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
      // The Rosalie's wings and badge are seen only past the bonnet; its tiled photo
      // linings repeat every few centimetres, so their relief keeps at 512.
      for (const pattern of CAR_FAR)
        gltf("resize", work, work, "--width", "256", "--height", "256", "--pattern", pattern);
      for (const pattern of CAR_RELIEF)
        gltf("resize", work, work, "--width", "512", "--height", "512", "--pattern", pattern);
    }
    // Roadside set dressing is seen in passing: its maps share a smaller budget.
    if (kind === "roadside") {
      gltf("resize", work, work, "--width", "512", "--height", "512", "--pattern", PROPS);
      gltf("resize", work, work, "--width", "256", "--height", "256", "--pattern", PROP_RELIEF);
      for (const pattern of FAR_SCANS)
        gltf("resize", work, work, "--width", "256", "--height", "256", "--pattern", pattern);
    }
    // The face first: already KTX2, the ETC1S pass then leaves it alone.
    if (kind === "cabin") gltf("uastc", work, work, "--pattern", FACE);
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
