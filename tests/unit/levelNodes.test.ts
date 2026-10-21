import { describe, expect, it } from "vitest";
import { Matrix, Quaternion, Vector3 } from "@babylonjs/core/Maths/math.vector";
import { facingToGltf, isBoxShape, parseNodeName } from "../../src/core/levelNodes";
import { orientedBox } from "../../src/core/LevelBuilder";

describe("parseNodeName", () => {
  it("reads the prefix and id", () => {
    expect(parseNodeName("col_stairs_front")).toEqual({ kind: "col", id: "stairs_front" });
    expect(parseNodeName("ladder_granary")).toEqual({ kind: "ladder", id: "granary" });
    expect(parseNodeName("light_flame_altar")).toEqual({ kind: "light_flame", id: "altar" });
  });

  it("reads patrol routes and their order", () => {
    expect(parseNodeName("patrol_bot_03")).toEqual({ kind: "patrol", id: "bot", order: 3 });
    expect(parseNodeName("patrol_house_walker_12")).toEqual({
      kind: "patrol",
      id: "house_walker",
      order: 12,
    });
    expect(parseNodeName("patrol_bot")).toBeNull();
  });

  it("ignores render meshes, including ones that only contain a prefix word", () => {
    expect(parseNodeName("deck")).toBeNull();
    expect(parseNodeName("granary_ladder")).toBeNull();
    expect(parseNodeName("collar")).toBeNull();
  });
});

describe("facingToGltf", () => {
  it("converts Blender axes (Z up) to glTF axes (Y up)", () => {
    expect(facingToGltf("-x")).toEqual([-1, 0, 0]);
    expect(facingToGltf("+x")).toEqual([1, 0, 0]);
    expect(facingToGltf("+y")).toEqual([0, 0, -1]);
    expect(facingToGltf("-Y")).toEqual([0, 0, 1]);
  });

  it("rejects anything else", () => {
    expect(facingToGltf("north")).toBeNull();
    expect(facingToGltf(undefined)).toBeNull();
  });
});

describe("isBoxShape", () => {
  const corners = [0, 1].flatMap((x) =>
    [0, 1].flatMap((y) => [0, 1].flatMap((z) => [x * 2, y * 0.1, z * 3])),
  );

  it("accepts a box, with corners repeated for flat normals", () => {
    expect(isBoxShape(corners)).toBe(true);
    expect(isBoxShape([...corners, ...corners, ...corners])).toBe(true);
  });

  it("rejects a wedge and a flat quad", () => {
    const wedge = [-0.5, 0, -1, 0.5, 0, -1, 0, 0.08, -1, -0.5, 0, 1, 0.5, 0, 1, 0, 0.08, 1];
    expect(isBoxShape([...wedge, ...wedge, ...wedge, ...wedge])).toBe(false);
    const quad = [0, 0, 0, 1, 0, 0, 0, 0, 1, 1, 0, 1];
    expect(isBoxShape([...quad, ...quad])).toBe(false);
  });
});

describe("orientedBox", () => {
  const min = new Vector3(-1, -0.05, -2);
  const max = new Vector3(1, 0.05, 2);
  const signs = [-1, 1].flatMap((x) => [-1, 1].flatMap((y) => [-1, 1].map((z) => [x, y, z])));

  it("keeps an unrotated box as it is", () => {
    const [center, rotation, extents] = orientedBox(min, max, Matrix.Translation(0, 1, 0));
    expect(center.asArray()).toEqual([0, 1, 0]);
    expect(extents.x).toBeCloseTo(2);
    expect(extents.y).toBeCloseTo(0.1);
    expect(extents.z).toBeCloseTo(4);
    expect(Math.abs(rotation.w)).toBeCloseTo(1);
  });

  it("follows a tilted ramp under a mirrored parent, like a glTF root node", () => {
    const tilt = Quaternion.RotationAxis(Vector3.Right(), 0.66);
    const local = Matrix.Compose(Vector3.One(), tilt, new Vector3(0, 1, 0.5));
    // Babylon's glTF root: 180° about Y and Z scaled by -1.
    const root = Matrix.Compose(
      new Vector3(1, 1, -1),
      Quaternion.RotationAxis(Vector3.Up(), Math.PI),
      Vector3.Zero(),
    );
    const world = local.multiply(root);
    const [center, rotation, extents] = orientedBox(min, max, world);

    // Every corner of the transformed box must be a corner of the collider.
    const collider = signs.map(([x, y, z]) =>
      center.add(
        new Vector3(
          (x * extents.x) / 2,
          (y * extents.y) / 2,
          (z * extents.z) / 2,
        ).applyRotationQuaternion(rotation),
      ),
    );
    for (const [x, y, z] of signs) {
      const local = new Vector3(
        x > 0 ? max.x : min.x,
        y > 0 ? max.y : min.y,
        z > 0 ? max.z : min.z,
      );
      const expected = Vector3.TransformCoordinates(local, world);
      const nearest = Math.min(...collider.map((c) => Vector3.Distance(c, expected)));
      expect(nearest).toBeLessThan(1e-5);
    }
    expect(extents.z).toBeCloseTo(4);
  });
});
