import { describe, expect, it } from "vitest";
import { NullEngine } from "@babylonjs/core/Engines/nullEngine";
import { Scene } from "@babylonjs/core/scene";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { JUNGLE_TINT, gradeJungle } from "../../src/episodes/ep1/act1/jungleGrade";

describe("jungle grade", () => {
  it("cools library plants once, leaves repainted forest surfaces and props alone", () => {
    const engine = new NullEngine(),
      scene = new Scene(engine);
    try {
      const make = (name: string) => {
        const m = new PBRMaterial(name, scene);
        m.albedoColor = new Color3(1, 1, 1);
        return m;
      };
      const shrub = make("shrub_03"),
        forest = make("M_forest_leaf"),
        page = make("M_sketchbook_leaf_front"),
        bark = make("M_wet_bark");
      expect(gradeJungle([shrub, forest, page, bark])).toBe(2);
      expect(gradeJungle([shrub])).toBe(0);
      expect(shrub.albedoColor.g).toBeCloseTo(JUNGLE_TINT.leaf![1]);
      expect(shrub.albedoColor.g).toBeGreaterThan(shrub.albedoColor.r);
      expect(forest.albedoColor.g).toBe(1);
      expect(page.albedoColor.g).toBe(1);
      expect(bark.albedoColor.r).toBeCloseTo(JUNGLE_TINT.bark![0]);
      // The taxi's roadside was never repainted: everything there is graded.
      const roadside = make("M_forest_leaf");
      expect(gradeJungle([roadside], false)).toBe(1);
    } finally {
      scene.dispose();
      engine.dispose();
    }
  });
});
