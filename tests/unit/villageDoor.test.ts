import { describe, expect, it, vi } from "vitest";
import { NullEngine } from "@babylonjs/core/Engines/nullEngine";
import { Scene } from "@babylonjs/core/scene";
import { CreateBox } from "@babylonjs/core/Meshes/Builders/boxBuilder";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { VillageDoor } from "../../src/episodes/ep1/act1/VillageDoor";

describe("village door under a mirrored glTF parent", () => {
  it("stays in place when rigged, swings into the room, and removes its collider and padlock", () => {
    const engine = new NullEngine();
    const scene = new Scene(engine);
    try {
      const root = new TransformNode("gltf_root", scene);
      root.scaling.z = -1;
      root.rotation.y = Math.PI;
      const leaf = CreateBox("interact_door_sok", { width: 0.06, height: 2.05, depth: 0.9 }, scene);
      leaf.position.set(2.99, 3.525, 13.45);
      leaf.parent = root;
      leaf.computeWorldMatrix(true);
      const before = leaf.getBoundingInfo().boundingBox.centerWorld.clone();
      const padlock = CreateBox("door_sok_padlock", {}, scene);
      const anchor = new TransformNode("col_door_sok_body", scene);
      const disposeBody = vi.fn(() => {
        anchor.physicsBody = null;
      });
      const disposeShape = vi.fn();
      Object.defineProperty(anchor, "physicsBody", {
        value: { dispose: disposeBody, shape: { dispose: disposeShape } },
        writable: true,
      });
      const door = new VillageDoor(
        scene,
        { name: leaf.name, position: before, yaw: 0, extras: {}, node: leaf },
        "col_door_sok",
        padlock.name,
      );
      leaf.computeWorldMatrix(true);
      expect(Vector3.Distance(before, leaf.getBoundingInfo().boundingBox.centerWorld)).toBeLessThan(
        1e-5,
      );
      door.open();
      for (let k = 0; k < 40; k++) door.update(0.1);
      leaf.computeWorldMatrix(true);
      const after = leaf.getBoundingInfo().boundingBox;
      expect(after.centerWorld.x).toBeLessThan(before.x - 0.3);
      expect(after.maximumWorld.z - after.minimumWorld.z).toBeLessThan(0.2);
      expect(padlock.isEnabled()).toBe(false);
      expect(scene.getTransformNodeByName(anchor.name)).toBeNull();
      door.open();
      expect(disposeBody).toHaveBeenCalledTimes(1);
      expect(disposeShape).toHaveBeenCalledTimes(1);
    } finally {
      scene.dispose();
      engine.dispose();
    }
  });
});
