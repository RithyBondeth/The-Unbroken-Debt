import { beforeAll, describe, expect, it } from "vitest";
import { NodeIO, type Document } from "@gltf-transform/core";
import { ALL_EXTENSIONS } from "@gltf-transform/extensions";
import { getBounds } from "@gltf-transform/functions";
import { MeshoptDecoder } from "meshoptimizer";
import { isLfsPointer } from "./lfsAsset";

const path = "public/assets/ep3/ep3_area_village.glb";
describe.skipIf(isLfsPointer(path))("Episode 3 physical art", () => {
  let document: Document;
  beforeAll(async () => {
    await MeshoptDecoder.ready;
    document = await new NodeIO()
      .registerExtensions(ALL_EXTENSIONS)
      .registerDependencies({ "meshopt.decoder": MeshoptDecoder })
      .read(path);
  });
  it("places imported props on their recorded supporting surfaces", () => {
    const props = document
      .getRoot()
      .listNodes()
      .filter((n) => typeof n.getExtras().ep3_support_height === "number");
    expect(props.length).toBeGreaterThan(250);
    for (const prop of props) {
      const gap = getBounds(prop).min[1] - Number(prop.getExtras().ep3_support_height);
      expect(Math.abs(gap), prop.getName()).toBeLessThan(0.012);
    }
  });
  it("plants the near forest below the floodline with a full canopy", () => {
    const trees = document
      .getRoot()
      .listNodes()
      .filter((n) => n.getExtras().ep3_forest_tree);
    expect(trees.length).toBeGreaterThan(50);
    for (const tree of trees) {
      const bounds = getBounds(tree);
      expect(bounds.min[1], tree.getName()).toBeLessThan(-1);
      expect(bounds.max[1], tree.getName()).toBeGreaterThan(2.5);
    }
  });
  it("keeps every moored hull partly below the actual lake surface", () => {
    for (const name of [0, 1, 2, 3, 4]
      .map((i) => `market_sampan_${i}`)
      .concat(["lok_sampan", "sora_moored_boat"])) {
      const hull = document
        .getRoot()
        .listNodes()
        .find((n) => n.getName() === name + "_hull")!;
      expect(hull).toBeDefined();
      const bounds = getBounds(hull);
      expect(bounds.min[1], name).toBeCloseTo(-0.22, 2);
      expect(bounds.max[1], name).toBeGreaterThan(0.06);
    }
  });
  it("rests Pa Lok's oil lamp on its stool", () => {
    const nodes = document.getRoot().listNodes();
    const lamp = nodes.find((n) => n.getName() === "real_practical_lantern_lok_lamp")!;
    const stool = nodes.find((n) => n.getName() === "real_lok_lamp_stool")!;
    expect(lamp).toBeDefined();
    expect(stool).toBeDefined();
    const contact = getBounds(lamp).min[1] - getBounds(stool).max[1];
    expect(contact).toBeGreaterThanOrEqual(-0.005);
    expect(contact).toBeLessThan(0.012);
  });
  it("supports every story document in height and across its footprint", () => {
    const nodes = document.getRoot().listNodes();
    const supports = nodes.filter((n) => n.getExtras().ep3_supports_document);
    expect(supports).toHaveLength(6);
    for (const support of supports) {
      const page = nodes.find((n) => n.getName() === support.getExtras().ep3_supports_document)!;
      expect(page).toBeDefined();
      const sheet = getBounds(page),
        table = getBounds(support);
      expect(sheet.min[1] - table.max[1], page.getName()).toBeCloseTo(0.002, 2);
      for (const axis of [0, 2]) {
        expect(sheet.min[axis], page.getName()).toBeGreaterThanOrEqual(table.min[axis] - 0.01);
        expect(sheet.max[axis], page.getName()).toBeLessThanOrEqual(table.max[axis] + 0.01);
      }
    }
  });
  it("gives all nine actors complete eye geometry and a neutral default pose", () => {
    const nodes = document.getRoot().listNodes();
    const bodies = nodes.filter((n) => n.getExtras().ep3_anatomy_version === 2);
    expect(bodies).toHaveLength(9);
    for (const body of bodies) {
      const eyes = body.listChildren().filter((n) => /_eye_[01]$/.test(n.getName()));
      expect(eyes, body.getName()).toHaveLength(2);
      for (const eye of eyes) {
        const bounds = getBounds(eye);
        expect(bounds.max[0] - bounds.min[0]).toBeGreaterThan(0.018);
        expect(bounds.max[0] - bounds.min[0]).toBeLessThan(0.028);
      }
      body.traverse((node) => {
        expect(
          node.getWeights().every((weight) => Math.abs(weight) < 1e-6),
          node.getName(),
        ).toBe(true);
      });
    }
    expect(nodes.find((n) => n.getName() === "pich_body")?.getExtras().ep3_actor_source).toBe(
      "MakeHuman male child",
    );
  });
  it("keeps the central chest covered on every clothed actor", () => {
    const bodies = document
      .getRoot()
      .listNodes()
      .filter((n) => n.getExtras().ep3_anatomy_version === 2);
    for (const body of bodies) {
      const skinNode = body.getMesh() ? body : body.listChildren().find((n) => n.getName() === "");
      const skin = skinNode?.getMesh();
      expect(skin, body.getName()).toBeTruthy();
      const primitives = skin!.listPrimitives();
      const minima = [0, 1, 2].map((axis) =>
        Math.min(...primitives.map((p) => p.getAttribute("POSITION")!.getMinNormalized([])[axis])),
      );
      const maxima = [0, 1, 2].map((axis) =>
        Math.max(...primitives.map((p) => p.getAttribute("POSITION")!.getMaxNormalized([])[axis])),
      );
      // Blender may preserve Z-up mesh coordinates under an exported Y-up node.
      const vertical = maxima[2] - minima[2] > maxima[1] - minima[1] ? 2 : 1;
      const height = maxima[vertical] - minima[vertical];
      let exposed = 0;
      for (const primitive of primitives) {
        const positions = primitive.getAttribute("POSITION")!;
        const indices = primitive.getIndices()!.getArray()!;
        for (let i = 0; i < indices.length; i += 3) {
          const a = positions.getElement(indices[i], [0, 0, 0]),
            b = positions.getElement(indices[i + 1], [0, 0, 0]),
            c = positions.getElement(indices[i + 2], [0, 0, 0]);
          const x = ((a[0] + b[0] + c[0]) / 3) * Math.abs(skinNode!.getScale()[0]);
          const y = (a[vertical] + b[vertical] + c[vertical]) / 3 - minima[vertical];
          if (Math.abs(x) < 0.1 && y > height * 0.65 && y < height * 0.8) exposed++;
        }
      }
      expect(exposed, body.getName()).toBe(0);
    }
  });
});
