import { describe, expect, it } from "vitest";
import { NullEngine } from "@babylonjs/core/Engines/nullEngine";
import { Scene } from "@babylonjs/core/scene";
import { AssetContainer } from "@babylonjs/core/assetContainer";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { CreateBox } from "@babylonjs/core/Meshes/Builders/boxBuilder";
import { StandardMaterial } from "@babylonjs/core/Materials/standardMaterial";
import { buildTaxiRoadside } from "../../src/episodes/ep1/travel/TaxiRoadside";

describe("taxi landscape batching", () => {
  it("preserves every shared plant and moves its bounds with the road sector", () => {
    const engine = new NullEngine(),
      scene = new Scene(engine);
    try {
      const source = new AssetContainer(scene),
        root = new TransformNode("root", scene);
      const tree = CreateBox("tree", {}, scene);
      tree.material = new StandardMaterial("leaves", scene);
      tree.parent = root;
      source.meshes.push(tree);
      source.transformNodes.push(root);
      for (let i = 1; i <= 3; i++) {
        const instance = tree.createInstance(`tree_${i}`);
        instance.parent = root;
        instance.position.set(i * 3, 0, i * 6);
        source.meshes.push(instance);
      }
      source.removeAllFromScene();
      const { root: route, landscape } = buildTaxiRoadside(source, scene);
      expect(landscape.reduce((sum, mesh) => sum + mesh.getTotalVertices(), 0)).toBe(4 * 24);
      expect(
        landscape.every((mesh) => !mesh.isDisposed() && mesh.isEnabled() && mesh.parent === route),
      ).toBe(true);
      const maximumZ = () =>
        Math.max(
          ...landscape.map((mesh) => {
            mesh.computeWorldMatrix(true);
            return mesh.getBoundingInfo().boundingBox.maximumWorld.z;
          }),
        );
      expect(maximumZ()).toBeCloseTo(18.5);
      route.position.z = -7;
      expect(maximumZ()).toBeCloseTo(11.5);
    } finally {
      scene.dispose();
      engine.dispose();
    }
  });
});
