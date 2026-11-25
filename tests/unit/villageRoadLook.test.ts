import { describe, expect, it } from "vitest";
import { NullEngine } from "@babylonjs/core/Engines/nullEngine";
import { Scene } from "@babylonjs/core/scene";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { CreateBox } from "@babylonjs/core/Meshes/Builders/boxBuilder";
import { GROUNDED } from "@/render/groundSnap";
import {
  GOODS_DRAW_DISTANCE,
  ROAD_DRAW_DISTANCE,
  ROAD_NORTH_EDGE,
  cullVillageRoad,
  dressVillageRoad,
} from "@/episodes/ep1/act1/villageRoadLook";
import { PLAY, VILLAGE_ROAD } from "@/episodes/ep1/data/forestBorder";

describe("the village road outside the gate (Nov 25, 2026)", () => {
  it("dresses the shops' posters and props as the driving scene does, leaves the rest", () => {
    const scene = new Scene(new NullEngine());
    const posters = new PBRMaterial("M_vroad_khmer_posters", scene);
    const stool = new PBRMaterial("M_vroad_shop_ph_wooden_stool_01_0", scene);
    stool.albedoColor.set(1, 1, 1);
    const bulb = new PBRMaterial("M_vroad_shop_bulb", scene);
    bulb.albedoColor.set(1, 0.8, 0.4);
    const farm = new PBRMaterial("M_v2_track", scene);
    farm.albedoColor.set(1, 1, 1);
    expect(dressVillageRoad(scene.materials)).toBe(3);
    expect(posters.clearCoat.isEnabled).toBe(true);
    expect(stool.albedoColor.r).toBeCloseTo(0.66);
    expect(bulb.albedoColor.g).toBeCloseTo(0.8);
    expect(farm.albedoColor.r).toBe(1);
    scene.getEngine().dispose();
  });

  it("draws what lies past the farm's fence only when Sora is near the road", () => {
    const scene = new Scene(new NullEngine());
    const shop = CreateBox("batch_7", { size: 2 }, scene);
    shop.position.set(0, 1, VILLAGE_ROAD.z + 7);
    const goods = CreateBox("batch_9", { size: 1 }, scene);
    goods.position.set(3, 1, VILLAGE_ROAD.z + 8);
    goods.material = new PBRMaterial("M_vroad_goods_matte", scene);
    const house = CreateBox("batch_1", { size: 2 }, scene);
    house.position.set(0, 1, -12);
    expect(cullVillageRoad(scene.meshes)).toBe(2);
    expect(shop.getLODLevels()[0].distanceOrScreenCoverage).toBe(ROAD_DRAW_DISTANCE);
    expect(goods.getLODLevels()[0].distanceOrScreenCoverage).toBe(GOODS_DRAW_DISTANCE);
    expect(house.hasLODLevels).toBe(false);
    // From the gate the whole walkable stretch is drawn.
    expect(Math.hypot(VILLAGE_ROAD.walkX, VILLAGE_ROAD.z - 42.6)).toBeLessThan(ROAD_DRAW_DISTANCE);
    expect(ROAD_NORTH_EDGE).toBeGreaterThan(42.6);
    expect(PLAY.maxZ).toBeGreaterThan(VILLAGE_ROAD.z + 10);
    scene.getEngine().dispose();
  });

  it("keeps its verge grass and litter where it was set on the raised bank", () => {
    // Named vroad_* in the area: snapToGround would lower GROUNDED names to the forest floor.
    for (const name of [
      "vroad_grass_medium_01_a_n",
      "vroad_dry_branches_medium_01_b_n",
      "vroad_fern_02_a_n",
    ])
      expect(GROUNDED.test(name)).toBe(false);
  });
});
