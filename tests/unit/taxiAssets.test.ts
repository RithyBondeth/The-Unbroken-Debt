import { beforeAll, describe, expect, it } from "vitest";
import { statSync } from "node:fs";
import { NodeIO, type Document } from "@gltf-transform/core";
import { ALL_EXTENSIONS } from "@gltf-transform/extensions";
import { getBounds } from "@gltf-transform/functions";
import { MeshoptDecoder } from "meshoptimizer";
import { Ray } from "@babylonjs/core/Culling/ray";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
let cabin: Document, road: Document;
beforeAll(async () => {
  await MeshoptDecoder.ready;
  const io = new NodeIO()
    .registerExtensions(ALL_EXTENSIONS)
    .registerDependencies({ "meshopt.decoder": MeshoptDecoder });
  [cabin, road] = await Promise.all([
    io.read("public/assets/ep1/ep1_taxi_cabin.glb"),
    io.read("public/assets/ep1/ep1_taxi_roadside.glb"),
  ]);
});
describe("authored taxi assets", () => {
  it("ships shaped trim, textured upholstery and an anatomical seated driver instead of primitive stand-ins", () => {
    const mats = cabin.getRoot().listMaterials();
    for (const name of ["M_taxi_worn_vinyl", "M_taxi_dashboard_walnut", "M_taxi_driver_cotton"]) {
      const material = mats.find((m) => m.getName() === name)!;
      expect(material).toBeDefined();
      expect(material.getNormalTexture()).toBeTruthy();
    }
    expect(
      mats.find((m) => m.getName() === "M_taxi_worn_vinyl")?.getBaseColorTexture(),
    ).toBeTruthy();
    const driver = cabin
      .getRoot()
      .listMeshes()
      .find((m) => m.getName().includes("driver_anatomy"))!;
    expect(driver).toBeDefined();
    expect(
      driver.listPrimitives().reduce((sum, p) => sum + p.getAttribute("POSITION")!.getCount(), 0),
    ).toBeGreaterThan(10_000);
    expect(cabin.getRoot().listSkins()).toHaveLength(0);
    const bounds = getBounds(cabin.getRoot().listScenes()[0]);
    expect(bounds.max[1]).toBeGreaterThan(1.75);
    expect(bounds.max[1]).toBeLessThan(2);
  });
  it("reuses the village’s actual foliage, bark and mud materials", () => {
    const mats = road.getRoot().listMaterials();
    expect(
      mats.some(
        (m) => m.getName() === "M_wet_mud" && m.getBaseColorTexture() && m.getNormalTexture(),
      ),
    ).toBe(true);
    expect(mats.some((m) => m.getName() === "M_wet_bark" && m.getBaseColorTexture())).toBe(true);
    expect(
      mats.some((m) => /forest_leaf|tree_leaves/.test(m.getName()) && m.getBaseColorTexture()),
    ).toBe(true);
  });
  it("keeps the driver's skin facing outward and supplies inset eyes", () => {
    const node = cabin
      .getRoot()
      .listNodes()
      .find((n) => n.getName().includes("driver_anatomy"))!;
    const w = node.getWorldMatrix(),
      samples: { p: number[]; n: number[] }[] = [];
    for (const primitive of node.getMesh()!.listPrimitives()) {
      if (primitive.getMaterial()?.getName() !== "M_taxi_driver_skin") continue;
      const positions = primitive.getAttribute("POSITION")!,
        normals = primitive.getAttribute("NORMAL")!;
      for (let i = 0; i < positions.getCount(); i++) {
        const v = positions.getElement(i, []),
          n = normals.getElement(i, []);
        const p = [
          v[0] * w[0] + v[1] * w[4] + v[2] * w[8] + w[12],
          v[0] * w[1] + v[1] * w[5] + v[2] * w[9] + w[13],
          v[0] * w[2] + v[1] * w[6] + v[2] * w[10] + w[14],
        ];
        if (p[1] < 1.22) continue;
        const normal = [
          n[0] * w[0] + n[1] * w[4] + n[2] * w[8],
          n[0] * w[1] + n[1] * w[5] + n[2] * w[9],
          n[0] * w[2] + n[1] * w[6] + n[2] * w[10],
        ];
        const length = Math.hypot(...normal);
        samples.push({ p, n: normal.map((x) => x / length) });
      }
    }
    const centre = [0, 1, 2].map(
      (j) => samples.reduce((sum, s) => sum + s.p[j], 0) / samples.length,
    );
    const outward =
      samples.reduce(
        (sum, s) => sum + s.n.reduce((dot, n, j) => dot + n * (s.p[j] - centre[j]), 0),
        0,
      ) / samples.length;
    expect(outward).toBeGreaterThan(0.015);
    expect(
      cabin
        .getRoot()
        .listNodes()
        .filter((m) => /driver_eye_[LR]/.test(m.getName())),
    ).toHaveLength(2);
  });
  it("keeps the road and standing-water normals facing the headlights", () => {
    const surfaces = road
      .getRoot()
      .listMeshes()
      .filter((m) => /muddy_track|road_ground|rut_water/.test(m.getName()));
    expect(surfaces.length).toBeGreaterThan(2);
    for (const mesh of surfaces)
      for (const p of mesh.listPrimitives()) {
        const n = p.getAttribute("NORMAL")!;
        for (let i = 0; i < n.getCount(); i++) expect(n.getElement(i, [])[1]).toBeGreaterThan(0.85);
      }
  });
  it("blocks downward and lower-body sight lines with an opaque cabin shell", () => {
    const panels = cabin
      .getRoot()
      .listNodes()
      .filter((n) => /taxi_(floorpan|firewall|rear_bulkhead|lower_body)_sealed/.test(n.getName()));
    expect(panels).toHaveLength(5);
    const triangles: Vector3[][] = [];
    for (const node of panels) {
      const w = node.getWorldMatrix();
      for (const primitive of node.getMesh()!.listPrimitives()) {
        expect(primitive.getMaterial()!.getAlphaMode()).toBe("OPAQUE");
        const positions = primitive.getAttribute("POSITION")!,
          indices = primitive.getIndices()!;
        const point = (i: number) => {
          const v = positions.getElement(i, []);
          return new Vector3(
            v[0] * w[0] + v[1] * w[4] + v[2] * w[8] + w[12],
            v[0] * w[1] + v[1] * w[5] + v[2] * w[9] + w[13],
            v[0] * w[2] + v[1] * w[6] + v[2] * w[10] + w[14],
          );
        };
        for (let i = 0; i < indices.getCount(); i += 3)
          triangles.push([
            point(indices.getScalar(i)),
            point(indices.getScalar(i + 1)),
            point(indices.getScalar(i + 2)),
          ]);
      }
    }
    // File coordinates reflect X relative to the left-handed game scene.
    const eye = new Vector3(-0.39, 1.31, -0.24),
      targets: Vector3[] = [];
    for (const x of [-0.65, 0, 0.65])
      for (const z of [-1.4, -0.3, 0.6, 1.05]) targets.push(new Vector3(x, -0.15, z));
    for (const side of [-1, 1])
      for (const y of [0.1, 0.45, 0.75])
        for (const z of [-1, 0.2, 0.85]) targets.push(new Vector3(side * 1.1, y, z));
    for (const x of [-0.65, 0, 0.65])
      for (const y of [0.15, 0.6]) {
        targets.push(new Vector3(x, y, 1.4));
        targets.push(new Vector3(x, y, -2));
      }
    for (const target of targets) {
      const ray = new Ray(eye, target.subtract(eye).normalize(), Vector3.Distance(eye, target));
      expect(
        triangles.some(([a, b, c]) => {
          const hit = ray.intersectsTriangle(a, b, c);
          return hit && hit.distance <= ray.length;
        }),
        `unsealed view towards ${target.toString()}`,
      ).toBe(true);
    }
  });
  it("keeps the fascia and instruments in front of the dashboard shell", () => {
    const nodes = cabin
      .getRoot()
      .listNodes()
      .filter((n) => /taxi_dashboard_sculpted|taxi_walnut_instrument_panel/.test(n.getName()));
    for (const x of [-0.65, -0.45, 0, 0.29, 0.49, 0.65]) {
      const ray = new Ray(new Vector3(x, 0.975, 0.9), new Vector3(0, 0, 1), 0.2);
      const hits: { distance: number; name: string }[] = [];
      for (const node of nodes) {
        const w = node.getWorldMatrix();
        for (const primitive of node.getMesh()!.listPrimitives()) {
          const p = primitive.getAttribute("POSITION")!,
            ix = primitive.getIndices()!;
          const point = (i: number) => {
            const v = p.getElement(i, []);
            return new Vector3(
              v[0] * w[0] + v[1] * w[4] + v[2] * w[8] + w[12],
              v[0] * w[1] + v[1] * w[5] + v[2] * w[9] + w[13],
              v[0] * w[2] + v[1] * w[6] + v[2] * w[10] + w[14],
            );
          };
          for (let i = 0; i < ix.getCount(); i += 3) {
            const hit = ray.intersectsTriangle(
              point(ix.getScalar(i)),
              point(ix.getScalar(i + 1)),
              point(ix.getScalar(i + 2)),
            );
            if (hit) hits.push({ distance: hit.distance, name: node.getName() });
          }
        }
      }
      expect(hits.sort((a, b) => a.distance - b.distance)[0]?.name).toContain(
        "taxi_walnut_instrument_panel",
      );
    }
  });
  it("covers the entire ride and visible horizon without recycled sectors", () => {
    const bounds = getBounds(road.getRoot().listScenes()[0]);
    expect(bounds.min[2]).toBeLessThan(-25);
    expect(bounds.max[2]).toBeGreaterThan(505);
  });
  it("seats Sora's anatomical legs and shoes inside the passenger footwell", () => {
    const nodes = cabin.getRoot().listNodes();
    const legs = nodes.find((n) => n.getName() === "taxi_sora_legs")!;
    expect(legs).toBeDefined();
    const bounds = getBounds(legs);
    expect(bounds.max[0] - bounds.min[0]).toBeLessThan(0.5);
    expect(bounds.min[1]).toBeGreaterThan(0.06);
    expect(bounds.max[1]).toBeLessThan(0.75);
    expect(
      legs
        .getMesh()!
        .listPrimitives()
        .reduce((sum, p) => sum + p.getAttribute("POSITION")!.getCount(), 0),
    ).toBeGreaterThan(1500);
    expect(nodes.some((n) => n.getName() === "taxi_sora_lap_fold")).toBe(true);
    for (const side of ["L", "R"]) {
      const sole = nodes.find((n) => n.getName() === `taxi_sora_shoe_sole_${side}`)!;
      const b = getBounds(sole);
      expect(b.min[1]).toBeGreaterThan(0.06);
      expect(b.min[1]).toBeLessThan(0.09);
    }
  });
  it("leaves both shoes visible from Sora's eyes rather than hidden under the lap cloth", () => {
    const nodes = cabin
      .getRoot()
      .listNodes()
      .filter((n) => n.getName().startsWith("taxi_sora_") && n.getMesh());
    for (const side of ["L", "R"]) {
      const shoe = nodes.find((n) => n.getName() === `taxi_sora_shoe_${side}`)!;
      const bounds = getBounds(shoe);
      const origin = new Vector3(-0.39, 1.31, -0.24),
        target = new Vector3(
          (bounds.min[0] + bounds.max[0]) / 2,
          bounds.min[1] + 0.025,
          bounds.max[2] - 0.03,
        );
      const ray = new Ray(
        origin,
        target.subtract(origin).normalize(),
        Vector3.Distance(origin, target) + 0.001,
      );
      const hits: { name: string; distance: number }[] = [];
      for (const node of nodes) {
        const w = node.getWorldMatrix();
        for (const primitive of node.getMesh()!.listPrimitives()) {
          const p = primitive.getAttribute("POSITION")!,
            indices = primitive.getIndices()!;
          const point = (i: number) => {
            const v = p.getElement(i, []);
            return new Vector3(
              v[0] * w[0] + v[1] * w[4] + v[2] * w[8] + w[12],
              v[0] * w[1] + v[1] * w[5] + v[2] * w[9] + w[13],
              v[0] * w[2] + v[1] * w[6] + v[2] * w[10] + w[14],
            );
          };
          for (let i = 0; i < indices.getCount(); i += 3) {
            const hit = ray.intersectsTriangle(
              point(indices.getScalar(i)),
              point(indices.getScalar(i + 1)),
              point(indices.getScalar(i + 2)),
            );
            if (hit && hit.distance <= ray.length)
              hits.push({ name: node.getName(), distance: hit.distance });
          }
        }
      }
      expect(hits.sort((a, b) => a.distance - b.distance)[0]?.name).toBe(`taxi_sora_shoe_${side}`);
    }
  });
  it("adds tactile driver details and a dense wall of trees along the route", () => {
    const names = cabin
      .getRoot()
      .listNodes()
      .map((n) => n.getName());
    for (const name of [
      "taxi_driver_cap_crown",
      "taxi_driver_chest_pocket",
      "taxi_driver_watch_face",
      "taxi_driver_rolled_cuff_L",
    ])
      expect(names).toContain(name);
    expect(
      cabin
        .getRoot()
        .listMaterials()
        .find((m) => m.getName() === "M_taxi_driver_skin")
        ?.getNormalTexture(),
    ).toBeTruthy();
    const trees = road
      .getRoot()
      .listNodes()
      .filter((n) => /taxi_road_(far_)?tree_/.test(n.getName()));
    expect(trees.length).toBeGreaterThanOrEqual(450);
    expect(
      road
        .getRoot()
        .listNodes()
        .filter((n) => n.getName().startsWith("taxi_road_")).length,
    ).toBeGreaterThan(1000);
  });
  it("keeps download and geometry costs bounded for the transition scene", () => {
    expect(statSync("public/assets/ep1/ep1_taxi_cabin.glb").size).toBeLessThan(6 * 1024 * 1024);
    expect(statSync("public/assets/ep1/ep1_taxi_roadside.glb").size).toBeLessThan(12 * 1024 * 1024);
    for (const asset of [cabin, road])
      expect(
        asset
          .getRoot()
          .listMeshes()
          .reduce(
            (sum, m) =>
              sum +
              m.listPrimitives().reduce((s, p) => s + (p.getIndices()?.getCount() ?? 0) / 3, 0),
            0,
          ),
      ).toBeLessThan(800_000);
  });
});
