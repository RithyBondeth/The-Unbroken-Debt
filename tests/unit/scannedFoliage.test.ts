import { describe, expect, it } from "vitest";
import { foliageKind } from "@/render/FoliageWind";

describe("the village's scanned plants in the wind", () => {
  it("moves every scanned leaf, frond, trunk, grass blade and rice hill", () => {
    const kinds: Record<string, string> = {
      M_flora_forest_tree_gn_ClusterB: "leaf",
      M_flora_forest_tree_gn_VinesB: "leaf",
      M_flora_forest_tree_gn_BarkB: "bark",
      M_flora_forest_banyan_BanyanTreeLeaves_1: "leaf",
      M_flora_forest_banyan_BanyanTreeBark: "bark",
      M_flora_sugar_palm_Material_55: "frond",
      M_flora_sugar_palm_Material_49: "bark",
      M_flora_bamboo_clump_Leaves1: "leaf",
      M_flora_bamboo_clump_Trunks2: "bark",
      M_flora_banana_clump_M_banana_clump: "frond",
      M_flora_anthurium_botany_01_anthurium_botany_01: "leaf",
      M_flora_grass_medium_01_grass_medium_01: "grass",
      M_paddy_rice_green: "grass",
      M_paddy_rice_ripe: "grass",
    };
    for (const [name, kind] of Object.entries(kinds)) expect(foliageKind(name), name).toBe(kind);
  });

  it("leaves the scarecrows and the dead wood on the ground still", () => {
    expect(foliageKind("M_flora_scarecrow_material_0")).toBeNull();
    expect(foliageKind("M_flora_bark_debris_01_bark_debris_01")).toBeNull();
    expect(foliageKind("M_flora_dead_tree_trunk_dead_tree_trunk")).toBeNull();
  });
});
