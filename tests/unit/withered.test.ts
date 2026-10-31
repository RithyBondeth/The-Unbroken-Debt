import { describe, expect, it } from "vitest";
import { NullEngine } from "@babylonjs/core/Engines/nullEngine";
import { Scene } from "@babylonjs/core/scene";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { ShaderLanguage } from "@babylonjs/core/Materials/shaderLanguage";
import { WITHER, Withered, witherPlants } from "../../src/render/Withered";

describe("withered plants", () => {
  it("withers library plants once and leaves repainted forest surfaces and props alone", () => {
    const engine = new NullEngine(),
      scene = new Scene(engine);
    try {
      const make = (name: string) => new PBRMaterial(name, scene);
      const [shrub, forest, page, bark, banana] = [
        "shrub_03",
        "M_forest_leaf",
        "M_sketchbook_leaf_front",
        "M_wet_bark",
        "M_banana_leaf",
      ].map(make);
      const plugins = witherPlants([shrub, forest, page, bark, banana]);
      expect(plugins.map((p) => p.tint)).toEqual([WITHER.leaf, WITHER.bark, WITHER.frond]);
      expect(witherPlants([shrub])).toEqual([]);
      expect(forest.pluginManager?.getPlugin("Withered")).toBeFalsy();
      expect(page.pluginManager?.getPlugin("Withered")).toBeFalsy();
      // The taxi's roadside was painted green: all of it withers.
      expect(witherPlants([make("M_forest_leaf")], false)).toHaveLength(1);
    } finally {
      scene.dispose();
      engine.dispose();
    }
  });

  it("drains colour towards a tinted luminance in both shading languages", () => {
    const engine = new NullEngine(),
      scene = new Scene(engine);
    try {
      const plugin = new Withered(new PBRMaterial("leaf", scene));
      const wgsl = plugin.getCustomCode("fragment", ShaderLanguage.WGSL)!;
      const glsl = plugin.getCustomCode("fragment", ShaderLanguage.GLSL)!;
      expect(wgsl.CUSTOM_FRAGMENT_UPDATE_ALPHA).toContain("uniforms.witherTint");
      expect(glsl.CUSTOM_FRAGMENT_UPDATE_ALPHA).not.toContain("uniforms.");
      expect(plugin.getCustomCode("vertex", ShaderLanguage.WGSL)).toBeNull();
      // Dead leaves are brown, not green: red over green over blue, mostly drained.
      for (const kind of ["leaf", "frond", "grass"] as const) {
        const [r, g, b, amount] = WITHER[kind]!;
        expect(r).toBeGreaterThan(g);
        expect(g).toBeGreaterThan(b);
        expect(amount).toBeGreaterThan(0.85);
      }
    } finally {
      scene.dispose();
      engine.dispose();
    }
  });
});
