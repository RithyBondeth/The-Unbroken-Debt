import { beforeAll, describe, expect, it } from "vitest";
import { statSync } from "node:fs";
import { NodeIO, type Document } from "@gltf-transform/core";
import { ALL_EXTENSIONS } from "@gltf-transform/extensions";
import { getBounds } from "@gltf-transform/functions";
import { MeshoptDecoder } from "meshoptimizer";
import { Ray } from "@babylonjs/core/Culling/ray";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
let cabin: Document, road: Document, spirit: Document;
beforeAll(async () => {
  await MeshoptDecoder.ready;
  const io = new NodeIO()
    .registerExtensions(ALL_EXTENSIONS)
    .registerDependencies({ "meshopt.decoder": MeshoptDecoder });
  [cabin, road, spirit] = await Promise.all([
    io.read("public/assets/ep1/ep1_taxi_cabin.glb"),
    io.read("public/assets/ep1/ep1_taxi_roadside.glb"),
    io.read("public/assets/ep1/neakta_roadside.glb"),
  ]);
});
describe("authored taxi assets", () => {
  it("ships shaped trim, textured upholstery and a photoscanned seated driver instead of primitive stand-ins", () => {
    const mats = cabin.getRoot().listMaterials();
    // The scanned Rosalie's own interior and door linings, the walnut fascia and the driver.
    for (const name of [
      "M_internal",
      "M_door",
      "M_taxi_dashboard_walnut",
      "M_taxi_driver_clothes_scan",
    ]) {
      const material = mats.find((m) => m.getName() === name)!;
      expect(material, name).toBeDefined();
      expect(material.getNormalTexture(), name).toBeTruthy();
      expect(material.getBaseColorTexture(), name).toBeTruthy();
    }
    // The whole scanned driver: body, cloth-simulated sleeves and photoscanned head.
    let vertices = 0;
    for (const part of [
      "taxi_driver_body_scan",
      "taxi_driver_sleeves_scan",
      "taxi_driver_head_scan",
    ]) {
      const mesh = cabin
        .getRoot()
        .listNodes()
        .find((n) => n.getName() === part)
        ?.getMesh();
      expect(mesh, part).toBeDefined();
      vertices += mesh!
        .listPrimitives()
        .reduce((sum, p) => sum + p.getAttribute("POSITION")!.getCount(), 0);
    }
    expect(vertices).toBeGreaterThan(40_000);
    expect(cabin.getRoot().listSkins()).toHaveLength(0);
    const bounds = getBounds(cabin.getRoot().listScenes()[0]);
    // A 1933 Rosalie's roof, about 1.3 m above its floorboards.
    expect(bounds.max[1]).toBeGreaterThan(1.2);
    expect(bounds.max[1]).toBeLessThan(1.5);
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
  it("keeps the driver's scanned face facing outward, with his glances, speech and blink", () => {
    const node = cabin
      .getRoot()
      .listNodes()
      .find((n) => n.getName() === "taxi_driver_head_scan")!;
    expect(node).toBeDefined();
    const w = node.getWorldMatrix(),
      samples: { p: number[]; n: number[] }[] = [];
    for (const primitive of node.getMesh()!.listPrimitives()) {
      const positions = primitive.getAttribute("POSITION")!,
        normals = primitive.getAttribute("NORMAL")!;
      for (let i = 0; i < positions.getCount(); i += 7) {
        const v = positions.getElement(i, []),
          n = normals.getElement(i, []);
        const p = [
          v[0] * w[0] + v[1] * w[4] + v[2] * w[8] + w[12],
          v[0] * w[1] + v[1] * w[5] + v[2] * w[9] + w[13],
          v[0] * w[2] + v[1] * w[6] + v[2] * w[10] + w[14],
        ];
        // The skull, above the neck carried down into the collar.
        if (p[1] < 1.08) continue;
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
    // A real photoscan: dense, with its own colour, relief and gloss maps.
    expect(
      node
        .getMesh()!
        .listPrimitives()
        .reduce((sum, p) => sum + p.getAttribute("POSITION")!.getCount(), 0),
    ).toBeGreaterThan(20_000);
    const face = cabin
      .getRoot()
      .listMaterials()
      .find((m) => m.getName() === "M_taxi_driver_head_scan")!;
    expect(face.getBaseColorTexture()).toBeTruthy();
    expect(face.getNormalTexture()).toBeTruthy();
    expect(face.getMetallicRoughnessTexture()).toBeTruthy();
    expect(face.getMetallicFactor()).toBe(0);
    // Shapes the runtime plays: glances, a nod, speech and blinking.
    expect((node.getMesh()!.getExtras() as { targetNames?: string[] }).targetNames).toEqual([
      "look_road",
      "look_sora",
      "nod",
      "talk",
      "blink",
    ]);
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
  it("blocks downward sight lines through the floorboards with an opaque cabin", () => {
    const triangles: Vector3[][] = [];
    for (const node of cabin.getRoot().listNodes()) {
      const mesh = node.getMesh();
      // Everything solid of the car (its glass, the people and the charm excepted).
      if (!mesh || /glass|taxi_(driver|sora)|charm/i.test(node.getName())) continue;
      const w = node.getWorldMatrix();
      for (const primitive of mesh.listPrimitives()) {
        if (primitive.getMaterial()?.getAlphaMode() === "BLEND") continue;
        const positions = primitive.getAttribute("POSITION")!,
          indices = primitive.getIndices();
        if (!indices) continue;
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
    // From Sora's eyes (file coordinates mirror X), down past the floor anywhere in the cabin.
    const eye = new Vector3(-0.27, 1.065, -0.06);
    for (const x of [-0.45, -0.2, 0.2, 0.45])
      for (const z of [-0.6, 0, 0.45]) {
        const target = new Vector3(x, -0.25, z);
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
  it("lines the dashboard with walnut and marks its dials for the runtime", () => {
    const nodes = cabin.getRoot().listNodes();
    expect(nodes.some((n) => n.getName() === "taxi_anchor_dials")).toBe(true);
    expect(
      nodes.some((n) =>
        n
          .getMesh()
          ?.listPrimitives()
          .some((p) => p.getMaterial()?.getName() === "M_taxi_dashboard_walnut"),
      ),
    ).toBe(true);
  });
  // Bounding the whole decoded road walks every vertex: over 5 s on a busy CI runner.
  it(
    "covers the entire ride and visible horizon without recycled sectors",
    { timeout: 30_000 },
    () => {
      const bounds = getBounds(road.getRoot().listScenes()[0]);
      expect(bounds.min[2]).toBeLessThan(-25);
      expect(bounds.max[2]).toBeGreaterThan(505);
    },
  );
  it("keeps low vegetation outside the widened road and exposes standing water above its crown", () => {
    const lateral = (x: number, z: number) => {
      let t = z;
      for (let i = 0; i < 5; i++) {
        const centre = 3.8 * Math.sin(t * 0.018) + 2.2 * Math.sin(t * 0.037),
          slope = 3.8 * 0.018 * Math.cos(t * 0.018) + 2.2 * 0.037 * Math.cos(t * 0.037);
        t += ((x - centre) * slope + z - t) / (1 + slope * slope);
      }
      const angle = Math.atan(
        3.8 * 0.018 * Math.cos(t * 0.018) + 2.2 * 0.037 * Math.cos(t * 0.037),
      );
      return (
        (x - 3.8 * Math.sin(t * 0.018) - 2.2 * Math.sin(t * 0.037)) * Math.cos(angle) -
        (z - t) * Math.sin(angle)
      );
    };
    let plants = 0,
      clearance = Infinity,
      halfWidth = 0,
      water = 0;
    for (const node of road.getRoot().listNodes()) {
      const name = node.getName(),
        plant =
          /^taxi_road_(?:(?:far_)?tree_|palm_|coco_|banana_|bamboo_|fern_|shrub_|forest_grass_)/.test(
            name,
          ),
        track = name === "taxi_muddy_track",
        pool = name.startsWith("taxi_rut_water");
      if (!plant && !track && !pool) continue;
      if (plant) plants++;
      if (pool) water++;
      const matrix = node.getWorldMatrix();
      for (const primitive of node.getMesh()!.listPrimitives()) {
        const positions = primitive.getAttribute("POSITION")!,
          v: number[] = [];
        for (let i = 0; i < positions.getCount(); i++) {
          positions.getElement(i, v);
          const x = -(v[0] * matrix[0] + v[1] * matrix[4] + v[2] * matrix[8] + matrix[12]),
            y = v[0] * matrix[1] + v[1] * matrix[5] + v[2] * matrix[9] + matrix[13],
            z = v[0] * matrix[2] + v[1] * matrix[6] + v[2] * matrix[10] + matrix[14];
          if (plant && y < 2.8) clearance = Math.min(clearance, Math.abs(lateral(x, z)));
          if (track) halfWidth = Math.max(halfWidth, Math.abs(lateral(x, z)));
          // The road sits 0.27 m lower (taxiMotion's TAXI_GROUND_DROP); pools just above its crown.
          if (pool) {
            expect(y).toBeGreaterThan(-0.27 - 0.062);
            expect(y).toBeLessThan(-0.27 - 0.054);
          }
        }
      }
    }
    expect(plants).toBeGreaterThan(1000);
    expect(clearance).toBeGreaterThan(3.2);
    expect(halfWidth).toBeGreaterThan(2.75);
    expect(halfWidth).toBeLessThan(2.85);
    expect(water).toBeGreaterThanOrEqual(218);
  });
  it("seats Sora's photoscanned legs and shoes inside the passenger footwell", () => {
    const nodes = cabin.getRoot().listNodes();
    const legs = nodes.find((n) => n.getName() === "taxi_sora_legs_scan")!;
    expect(legs).toBeDefined();
    const bounds = getBounds(legs);
    expect(bounds.max[0] - bounds.min[0]).toBeLessThan(0.5);
    // Her shoes rest on the floorboards (the carpet lies between -0.01 and 0.1 m; the tips of
    // her heels press into its pile).
    expect(bounds.min[1]).toBeGreaterThan(-0.03);
    expect(bounds.max[1]).toBeLessThan(0.75);
    const materials = legs
      .getMesh()!
      .listPrimitives()
      .map((p) => p.getMaterial()!.getName());
    for (const name of [
      "M_taxi_sora_trousers_scan",
      "M_taxi_sora_skin_scan",
      "M_taxi_sora_shoes_scan",
      "M_taxi_sora_blouse_scan",
    ])
      expect(materials).toContain(name);
    // The old flat cloth over her lap is gone: her own blouse closes the scan at the waist.
    expect(nodes.some((n) => n.getName() === "taxi_sora_lap_fold")).toBe(false);
  });
  it("leaves both shoes visible from Sora's eyes", () => {
    const node = cabin
      .getRoot()
      .listNodes()
      .find((n) => n.getName() === "taxi_sora_legs_scan")!;
    const w = node.getWorldMatrix();
    const world = (v: number[]) =>
      new Vector3(
        v[0] * w[0] + v[1] * w[4] + v[2] * w[8] + w[12],
        v[0] * w[1] + v[1] * w[5] + v[2] * w[9] + w[13],
        v[0] * w[2] + v[1] * w[6] + v[2] * w[10] + w[14],
      );
    const triangles: { shoe: boolean; t: Vector3[] }[] = [],
      shoePoints: Vector3[] = [];
    for (const primitive of node.getMesh()!.listPrimitives()) {
      const shoe = primitive.getMaterial()!.getName() === "M_taxi_sora_shoes_scan";
      const p = primitive.getAttribute("POSITION")!,
        ix = primitive.getIndices()!;
      for (let i = 0; i < ix.getCount(); i += 3) {
        const t = [0, 1, 2].map((k) => world(p.getElement(ix.getScalar(i + k), [])));
        triangles.push({ shoe, t });
        if (shoe) shoePoints.push(t[0]);
      }
    }
    // Her feet sit apart: one shoe each side of her centre line.
    const middle = shoePoints.reduce((sum, v) => sum + v.x, 0) / shoePoints.length;
    for (const side of [-1, 1]) {
      const own = shoePoints.filter((v) => (v.x - middle) * side > 0.03);
      expect(own.length).toBeGreaterThan(20);
      const toe = own.reduce((best, v) => (v.z > best.z ? v : best), own[0]);
      const origin = new Vector3(-0.27, 1.065, -0.06),
        target = toe.add(new Vector3(0, 0.01, -0.01));
      const ray = new Ray(
        origin,
        target.subtract(origin).normalize(),
        Vector3.Distance(origin, target) + 0.01,
      );
      const hits = triangles
        .map(({ shoe, t }) => ({ shoe, hit: ray.intersectsTriangle(t[0], t[1], t[2]) }))
        .filter((h) => h.hit && h.hit.distance <= ray.length)
        .sort((a, b) => a.hit!.distance - b.hit!.distance);
      expect(hits[0]?.shoe).toBe(true);
    }
  });
  it("adds tactile driver details and a dense wall of trees along the route", () => {
    const names = cabin
      .getRoot()
      .listNodes()
      .map((n) => n.getName());
    // The driver is photoscanned throughout: head, body, and cloth-simulated sleeves.
    for (const name of [
      "taxi_driver_head_scan",
      "taxi_driver_body_scan",
      "taxi_driver_sleeves_scan",
    ])
      expect(names).toContain(name);
    // The cabin is furnished like a working taxi, not a box.
    for (const piece of [
      /headliner/,
      /^taxi_meter_case/,
      /^taxi_rear_lotus_bud/,
      /^taxi_mirror_charm_pivot/,
      /^taxi_anchor_wiper_[lr]/,
      /^taxi_anchor_headlamp_[lr]/,
      /^taxi_anchor_mirror/,
      /^taxi_anchor_sora_eye/,
    ])
      expect(names.some((n) => piece.test(n))).toBe(true);
    expect(
      cabin
        .getRoot()
        .listMaterials()
        .find((m) => m.getName() === "M_taxi_driver_clothes_scan")
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
  it("dresses the road and the cabin for the dread pass, with no rite by the road", () => {
    const roadNames = road
      .getRoot()
      .listNodes()
      .map((n) => n.getName());
    const count = (pattern: RegExp, names: string[]) => names.filter((n) => pattern.test(n)).length;
    // A colonial telegraph line, gravel, centre grass and flooded ditches along the track.
    expect(count(/^taxi_telegraph_post/, roadNames)).toBeGreaterThan(10);
    expect(count(/^taxi_telegraph_wire/, roadNames)).toBeGreaterThan(20);
    expect(count(/^taxi_road_pebble/, roadNames)).toBeGreaterThan(500);
    expect(count(/^taxi_ditch_water/, roadNames)).toBeGreaterThan(20);
    expect(roadNames).toContain("taxi_median_grass");
    // The roadside rite was taken out: nothing of it is left along the road.
    expect(count(/(^|_)rite(_|$)|ritual/, roadNames)).toBe(0);
    // Old growth, not bamboo: tall broadleaf giants far outnumber the odd clump.
    const giants = count(/^taxi_road_(far_)?tree_/, roadNames),
      bamboo = count(/^taxi_road_bamboo/, roadNames);
    // (The first 140 m are open paddies; the forest closes in after them.)
    expect(giants).toBeGreaterThan(500);
    expect(bamboo).toBeLessThan(giants / 60);
    const cabinNames = cabin
      .getRoot()
      .listNodes()
      .map((n) => n.getName());
    // The mirror charm hangs from one pivot the runtime swings.
    const pivot = cabin
      .getRoot()
      .listNodes()
      .find((n) => n.getName() === "taxi_mirror_charm_pivot")!;
    expect(pivot.listChildren().length).toBeGreaterThan(40);
    for (const name of ["taxi_meter_case", "taxi_rear_lotus_bud"])
      expect(cabinNames).toContain(name);
  });
  it("ships the roadside Neak Ta rigged, with its three motion-captured clips", () => {
    const root = spirit.getRoot();
    expect(root.listSkins().length).toBeGreaterThan(0);
    expect(
      root
        .listAnimations()
        .map((a) => a.getName())
        .sort(),
    ).toEqual(["reach", "stand", "walk"]);
    const joints = root
      .listSkins()[0]
      .listJoints()
      .map((j) => j.getName());
    for (const bone of ["root", "head", "neck03", "upperleg01.L", "foot.R", "upperarm01.L"])
      expect(joints).toContain(bone);
    expect(statSync("public/assets/ep1/neakta_roadside.glb").size).toBeLessThan(8 * 1024 * 1024);
  });
  it("keeps download and geometry costs bounded for the transition scene", () => {
    // The photoscanned people keep 2K colour and relief (the face in UASTC): about half the cabin.
    expect(statSync("public/assets/ep1/ep1_taxi_cabin.glb").size).toBeLessThan(26 * 1024 * 1024);
    // Paddies, stilt houses, palms and scanned ruts as well as the forest.
    expect(statSync("public/assets/ep1/ep1_taxi_roadside.glb").size).toBeLessThan(17 * 1024 * 1024);
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
