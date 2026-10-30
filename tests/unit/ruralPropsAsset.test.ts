import { beforeAll, describe, expect, it } from "vitest";
import { NodeIO, type Document, type Node } from "@gltf-transform/core";
import { ALL_EXTENSIONS } from "@gltf-transform/extensions";
import { getBounds } from "@gltf-transform/functions";
import { MeshoptDecoder } from "meshoptimizer";
import { fileURLToPath } from "node:url";
import { isLfsPointer } from "./lfsAsset";

const PATH = fileURLToPath(
  new URL("../../public/assets/ep1/ep1_area_village.glb", import.meta.url),
);

describe.skipIf(isLfsPointer(PATH))("ruralPropsAsset (needs the real Git LFS asset)", () => {
  let asset: Document;
  let nodes: Map<string, Node>;
  beforeAll(async () => {
    await MeshoptDecoder.ready;
    asset = await new NodeIO()
      .registerExtensions(ALL_EXTENSIONS)
      .registerDependencies({ "meshopt.decoder": MeshoptDecoder })
      .read(PATH);
    nodes = new Map(
      asset
        .getRoot()
        .listNodes()
        .map((node) => [node.getName(), node]),
    );
  }, 20000);

  it("grounds the actual shipped spade, folded umbrellas and stored traps within 5mm of soil", () => {
    for (const name of [
      "rusted_spade_01.001",
      ...[0, 1, 2].flatMap((i) => [`umbrella_${i}`, `fish_trap_${i}`]),
    ]) {
      const node = nodes.get(name)!;
      expect(node, name).toBeTruthy();
      const box = getBounds(node);
      expect(box.min[1], name).toBeGreaterThanOrEqual(-0.003);
      expect(box.min[1], name).toBeLessThan(0.005);
      expect(box.max[1] - box.min[1]).toBeGreaterThan(0.6);
    }
    for (let k = 0; k < 4; k++) {
      const lower = getBounds(nodes.get(`stacked_board_${k}`)!);
      const upper = getBounds(nodes.get(`stacked_board_${k + 1}`)!);
      expect(Math.abs(upper.min[1] - lower.max[1])).toBeLessThan(0.002);
    }
  });

  it("connects hanging traps and cloth to the actual beams and stair rail", () => {
    for (let k = 0; k < 3; k++) {
      const trap = nodes.get(`house_decay_stored_trap_${k}`)!;
      expect(trap.getExtras().support_kind).toBe("girder_lashing");
      const beam = nodes.get(String(trap.getExtras().support_beam))!;
      expect(beam).toBeTruthy();
      const fixture = getBounds(trap),
        support = getBounds(beam);
      expect(fixture.max[1]).toBeGreaterThan(support.max[1]);
      expect(fixture.max[1] - support.max[1]).toBeLessThan(0.02);
      expect(fixture.min[1]).toBeGreaterThan(1);
    }
    const rag = nodes.get("house_detail_tied_rag_3")!;
    const attachment = rag.getExtras().attachment_point as number[];
    expect(attachment[2]).toBeCloseTo(0.88 + ((9 - 7.6) / 3) * 2.5);
    expect(getBounds(rag).max[1]).toBeGreaterThan(attachment[2]);
    expect(nodes.has("house_decay_mourning_rags")).toBe(false);
  });

  it("ships interlaced wall relief and supported stairs while keeping their gameplay colliders", () => {
    for (const name of ["shed_wall_s_0", "shed_wall_e_0", "shed_wall_w_0"]) {
      const node = nodes.get(name)!;
      expect(node.getExtras().support_kind).toBe("framed_panel");
      const triangles = node
        .getMesh()!
        .listPrimitives()
        .reduce((sum, p) => sum + p.getIndices()!.getCount() / 3, 0);
      expect(triangles).toBeGreaterThan(1000);
      for (const primitive of node.getMesh()!.listPrimitives()) {
        expect(primitive.getAttribute("NORMAL")).toBeTruthy();
        if (primitive.getMaterial()?.getBaseColorTexture())
          expect(primitive.getAttribute("TEXCOORD_0")).toBeTruthy();
      }
      expect(nodes.has(`col_${name}`)).toBe(true);
    }
    for (const [flight, count] of [
      ["front", 12],
      ["rear", 11],
    ] as const) {
      const stairs = nodes.get(`stairs_${flight}_detailed`)!;
      expect(stairs.getExtras().tread_count).toBe(count);
      expect(getBounds(stairs).min[1]).toBeLessThanOrEqual(0);
      expect(nodes.has(`col_stairs_${flight}`)).toBe(true);
    }
    const footing = nodes.get("footing_-3_10")!;
    const stone = footing.getMesh()!.listPrimitives()[0].getMaterial()!;
    expect(stone.getBaseColorTexture()).toBeTruthy();
    expect(stone.getNormalTexture()).toBeTruthy();
    expect(getBounds(footing).max[1]).toBeCloseTo(0.1, 3);
  });
});
