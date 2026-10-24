import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

type Accessor = {
  bufferView?: number;
  byteOffset?: number;
  count: number;
  componentType: number;
  type: string;
  sparse?: {
    count: number;
    indices: { bufferView: number; componentType: number; byteOffset?: number };
    values: { bufferView: number; byteOffset?: number };
  };
};
type Primitive = {
  attributes: Record<string, number>;
  indices: number;
  material?: number;
  targets?: { POSITION: number }[];
};
const file = readFileSync(new URL("../../public/assets/ep1/sok_corpse.glb", import.meta.url));
const jsonLength = file.readUInt32LE(12);
const asset = JSON.parse(file.subarray(20, 20 + jsonLength).toString()) as {
  accessors: Accessor[];
  bufferViews: { byteOffset?: number; byteStride?: number }[];
  meshes: {
    name: string;
    weights?: number[];
    primitives: Primitive[];
    extras?: { targetNames: string[] };
  }[];
  materials: {
    name: string;
    normalTexture?: unknown;
    pbrMetallicRoughness?: { baseColorTexture?: unknown };
  }[];
};
const binary = file.subarray(28 + jsonLength);
function positions(index: number): number[][] {
  const a = asset.accessors[index];
  const values = Array.from({ length: a.count }, () => [0, 0, 0]);
  if (a.bufferView !== undefined) {
    const view = asset.bufferViews[a.bufferView];
    const offset = (view.byteOffset ?? 0) + (a.byteOffset ?? 0);
    values.forEach((p, i) =>
      p.forEach((_, axis) => {
        p[axis] = binary.readFloatLE(offset + i * (view.byteStride ?? 12) + axis * 4);
      }),
    );
  }
  if (a.sparse) {
    const { count, indices, values: sparse } = a.sparse;
    const indexOffset =
      (asset.bufferViews[indices.bufferView].byteOffset ?? 0) + (indices.byteOffset ?? 0);
    const valueOffset =
      (asset.bufferViews[sparse.bufferView].byteOffset ?? 0) + (sparse.byteOffset ?? 0);
    for (let i = 0; i < count; i++) {
      const vertex =
        indices.componentType === 5125
          ? binary.readUInt32LE(indexOffset + i * 4)
          : indices.componentType === 5123
            ? binary.readUInt16LE(indexOffset + i * 2)
            : binary.readUInt8(indexOffset + i);
      for (let axis = 0; axis < 3; axis++)
        values[vertex][axis] = binary.readFloatLE(valueOffset + i * 12 + axis * 4);
    }
  }
  return values;
}
const body = asset.meshes.find((mesh) => mesh.name === "Sok_anatomical_surface")!;
describe("Sok's exported anatomical asset", () => {
  it("starts at rest instead of stacking all four baked pose deltas", () => {
    expect(body).toBeDefined();
    expect(body.weights).toEqual([0, 0, 0, 0]);
    expect(body.extras?.targetNames).toEqual([
      "Sok_pose_1",
      "Sok_pose_2",
      "Sok_pose_3",
      "Sok_pose_4",
    ]);
    expect(body.primitives[0].targets).toHaveLength(4);
  });
  it("ships the authored skin colour, UVs and micro normal texture", () => {
    const skin = asset.materials.find((material) => material.name === "sok_aged_skin")!;
    expect(skin.pbrMetallicRoughness?.baseColorTexture).toBeDefined();
    expect(skin.normalTexture).toBeDefined();
    expect(body.primitives[0].attributes.TEXCOORD_0).toBeDefined();
  });
  it("keeps the body, eyes and held lotus inside the guard in every saved pose", () => {
    for (const mesh of asset.meshes.filter((mesh) => mesh.extras?.targetNames?.length)) {
      for (const primitive of mesh.primitives) {
        const rest = positions(primitive.attributes.POSITION);
        for (const delta of [
          null,
          ...(primitive.targets ?? []).map((target) => positions(target.POSITION)),
        ]) {
          const points = rest.map((p, i) => p.map((v, axis) => v + (delta?.[i][axis] ?? 0)));
          const min = [0, 1, 2].map((axis) => Math.min(...points.map((p) => p[axis])));
          const max = [0, 1, 2].map((axis) => Math.max(...points.map((p) => p[axis])));
          // glTF is Y-up; Babylon's handedness conversion reflects X.
          expect(-max[0]).toBeGreaterThanOrEqual(-1.04);
          expect(-min[0]).toBeLessThanOrEqual(1.04);
          expect(min[1] + 0.725).toBeGreaterThanOrEqual(0.69);
          expect(max[1] + 0.725).toBeLessThanOrEqual(2.1);
          expect(min[2] - 5.9).toBeGreaterThanOrEqual(-6.4);
          expect(max[2] - 5.9).toBeLessThanOrEqual(-5.25);
        }
      }
    }
  });
  it("keeps the lotus stem in the cupped right hand through all five poses", () => {
    const lotus = asset.meshes.find((mesh) => mesh.name === "Sok_funeral_lotus_geometry")!;
    expect(lotus.weights).toEqual([0, 0, 0, 0]);
    expect(lotus.extras?.targetNames).toEqual(body.extras?.targetNames);
    const stem = lotus.primitives.find(
      (primitive) => asset.materials[primitive.material!].name === "lotus_stem_and_sepals",
    )!;
    const inBlender = (p: number[]) => [p[0], -p[2], p[1]];
    const bodyRest = positions(body.primitives[0].attributes.POSITION).map(inBlender);
    const stemRest = positions(stem.attributes.POSITION).map(inBlender);
    const palms = bodyRest
      .map((p, i) => ({ p, i }))
      .filter(
        ({ p }) =>
          p[0] > -0.1 && p[0] < 0.08 && p[1] > -0.14 && p[1] < 0.02 && p[2] > 0.24 && p[2] < 0.34,
      );
    const grip = stemRest
      .map((p, i) => ({ p, i }))
      .filter(({ p }) => Math.hypot(p[0] - 0.005, p[1], p[2] - 0.305) < 0.035);
    expect(grip.length).toBeGreaterThan(8);
    for (let pose = 0; pose < 5; pose++) {
      const handDelta = pose
        ? positions(body.primitives[0].targets![pose - 1].POSITION).map(inBlender)
        : null;
      const stemDelta = pose ? positions(stem.targets![pose - 1].POSITION).map(inBlender) : null;
      let closest = Infinity;
      for (const a of grip)
        for (const b of palms) {
          const distance = Math.hypot(
            ...a.p.map(
              (value, axis) =>
                value + (stemDelta?.[a.i][axis] ?? 0) - b.p[axis] - (handDelta?.[b.i][axis] ?? 0),
            ),
          );
          closest = Math.min(closest, distance);
        }
      expect(closest, `lotus grip in pose ${pose}`).toBeLessThan(0.014);
    }
  });
  it("keeps the anatomical surface facing outward for rendering and cloth collision", () => {
    const primitive = body.primitives[0],
      a = asset.accessors[primitive.indices];
    const offset = (asset.bufferViews[a.bufferView!].byteOffset ?? 0) + (a.byteOffset ?? 0);
    const points = positions(primitive.attributes.POSITION);
    const at = (i: number) =>
      points[
        a.componentType === 5125
          ? binary.readUInt32LE(offset + i * 4)
          : binary.readUInt16LE(offset + i * 2)
      ];
    let volume = 0;
    for (let i = 0; i < a.count; i += 3) {
      const [p, q, r] = [at(i), at(i + 1), at(i + 2)];
      volume +=
        p[0] * (q[1] * r[2] - q[2] * r[1]) +
        p[1] * (q[2] * r[0] - q[0] * r[2]) +
        p[2] * (q[0] * r[1] - q[1] * r[0]);
    }
    expect(volume / 6).toBeGreaterThan(0.025);
  });
  it("retains a full-length tucked shroud rather than a collapsed cloth pile", () => {
    const cloth = asset.meshes.find((mesh) => mesh.name === "Cotton_drape")!;
    const x = positions(cloth.primitives[0].attributes.POSITION).map((p) => p[0]);
    expect(Math.max(...x) - Math.min(...x)).toBeGreaterThan(1.4);
  });
});
