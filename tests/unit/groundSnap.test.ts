import { describe, expect, it } from "vitest";
import { NullEngine } from "@babylonjs/core/Engines/nullEngine";
import { Scene } from "@babylonjs/core/scene";
import { AssetContainer } from "@babylonjs/core/assetContainer";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { CreateCylinder } from "@babylonjs/core/Meshes/Builders/cylinderBuilder";
import { CreateBox } from "@babylonjs/core/Meshes/Builders/boxBuilder";
import { GROUNDED, clearance, snapToGround } from "../../src/render/groundSnap";
import { inWalk, layoutBorder, pathDistance } from "../../src/episodes/ep1/data/forestBorder";

describe("ground snap", () => {
  it("measures the smallest gap between points and the ground under each", () => {
    const slope = (x: number) => x * 0.1;
    expect(clearance([0, 0.5, 0, 2, 0.3, 0], slope)).toBeCloseTo(0.1);
    expect(clearance([0, -0.2, 0], slope)).toBeCloseTo(-0.2);
  });

  it("knows what stands on the ground and what is built or hung", () => {
    for (const name of [
      "dead_1",
      "tree_301",
      "banana_144",
      "coco_307",
      "termite_4",
      "fern_02_a.008",
    ])
      expect(GROUNDED.test(name)).toBe(true);
    for (const name of [
      "well_0_beam",
      "crocodile_flag",
      "ridge_cap",
      "neakta_stone_watch",
      "tingmong_2",
    ])
      expect(GROUNDED.test(name)).toBe(false);
  });

  it("sets a hovering tree down on a dipping slope and leaves grounded or built things alone", () => {
    const engine = new NullEngine(),
      scene = new Scene(engine);
    try {
      const container = new AssetContainer(scene);
      const root = new TransformNode("__root__", scene);
      const make = (name: string, x: number, bottom: number) => {
        const node = new TransformNode(name, scene);
        node.parent = root;
        const mesh = CreateCylinder(`${name}_trunk`, { height: 4, diameter: 0.4 }, scene);
        mesh.parent = node;
        node.position.set(x, bottom + 2, 0);
        container.meshes.push(mesh);
        container.transformNodes.push(node);
        return node;
      };
      // The ground falls away towards +x.
      const ground = (x: number) => -0.05 * x;
      const floating = make("dead_1", 4, 0);
      const planted = make("tree_12", 0, -0.04);
      const beam = make("well_0_beam", 6, 1.5);
      const wall = CreateBox("wall_front_4", {}, scene);
      wall.parent = root;
      wall.position.y = 3;
      container.meshes.push(wall);
      const moved = snapToGround(container, ground);
      expect(moved.map((m) => m.name)).toEqual(["dead_1"]);
      const lowest = floating.getChildMeshes()[0].getBoundingInfo().boundingBox.minimumWorld.y;
      // Its downhill edge (x = 4.2) now just meets the ground.
      expect(lowest).toBeLessThan(ground(3.8) + 0.001);
      expect(lowest).toBeGreaterThan(ground(4.2) - 0.05);
      expect(planted.position.y).toBeCloseTo(1.96);
      expect(beam.position.y).toBeCloseTo(3.5);
      expect(wall.position.y).toBe(3);
    } finally {
      scene.dispose();
      engine.dispose();
    }
  });
});

describe("thick forest beside the walk", () => {
  it("grows off the trodden path, short of the road, clear of the first Neak Ta's patrol", () => {
    expect(inWalk(-12, 45)).toBe(true);
    expect(inWalk(-1.5, 45)).toBe(false); // the path
    expect(inWalk(0, 20)).toBe(false); // the patrol
    expect(inWalk(-12, 62)).toBe(false); // the road
    const layout = layoutBorder({ nearDepth: 14, farDepth: 44, density: 0.85, clear: () => true });
    const walk = layout.plants.filter((p) => inWalk(p.x, p.z));
    expect(walk.filter((p) => p.layer === "canopy").length).toBeGreaterThan(20);
    expect(walk.every((p) => pathDistance(p.x, p.z) > 3.4)).toBe(true);
    const thin = layoutBorder({
      nearDepth: 8,
      farDepth: 24,
      density: 0.55,
      walkCanopy: 0.45,
      clear: () => true,
    });
    const thinWalk = thin.plants.filter((p) => inWalk(p.x, p.z) && p.layer === "canopy");
    expect(thinWalk.length).toBeLessThan(walk.filter((p) => p.layer === "canopy").length);
  });
});
