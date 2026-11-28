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

/**
 * The shipped village after the farmstead rebuild (tools/areas/rebuild-farmstead.py,
 * Nov 22, 2026). glTF space: y up, Blender y is -z.
 */
describe.skipIf(isLfsPointer(PATH))("farmsteadAsset (needs the real Git LFS asset)", () => {
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
  }, 60000);

  it("climbs: both stairs reach from the ground to the floor, and every ladder faces its climber", () => {
    for (const name of ["col_rear_stairs", "col_front_stairs"]) {
      const node = nodes.get(name)!;
      expect(node, name).toBeTruthy();
      const box = getBounds(node);
      expect(box.min[1], name).toBeLessThan(0.3);
      expect(box.max[1], name).toBeCloseTo(2.5, 1);
    }
    for (const name of [
      "ladder_fs_kitchen",
      "ladder_fs_servants",
      "ladder_fs_barn_loft",
      "ladder_trapdoor",
      "ladder_attic",
    ]) {
      const node = nodes.get(name)!;
      expect(node, name).toBeTruthy();
      expect(["+x", "-x", "+y", "-y"], name).toContain(node.getExtras().facing);
    }
  });

  it("floors the house round its trapdoor and stair well, its galleries and the walkway", () => {
    for (const name of [
      ...[0, 1, 2, 3].map((k) => `col_house_floor_floor_${k}`),
      ...[0, 1, 2, 3].map((k) => `col_back_floor_floor_${k}`),
      "col_trapdoor_lid",
      "col_gallery_w_floor",
      "col_gallery_e_floor",
      "col_walkway_floor",
      "col_fs_kitchen_floor",
      "col_fs_barn_floor",
    ]) {
      const node = nodes.get(name)!;
      expect(node, name).toBeTruthy();
    }
    // The stair well is open: no floor collider covers its middle (Blender (2.75, 32.3)).
    for (const [name, node] of nodes) {
      if (!name.startsWith("col_back_floor_floor")) continue;
      const box = getBounds(node);
      const over =
        box.min[0] < 2.75 && box.max[0] > 2.75 && box.min[2] < -32.3 && box.max[2] > -32.3;
      expect(over, name).toBe(false);
    }
  });

  it("keeps what the acts find by name: doors, jars, the coffin's parts, the portrait", () => {
    for (const name of [
      "interact_door_sok",
      "col_door_sok",
      "door_sok_padlock",
      "interact_door_yaymey",
      "interact_shed_door",
      "interact_portrait",
      "portrait_sok",
      "interact_thread",
      "marker_main_burner",
      ...[1, 2, 3, 4, 5, 6].map((k) => `interact_jar_J${k}`),
      "col_fs_barn_gate",
    ])
      expect(nodes.has(name), name).toBe(true);
    const coffin = [...nodes.keys()].filter((name) => name.startsWith("coffin_"));
    expect(coffin.some((name) => name.startsWith("coffin_body"))).toBe(true);
    expect(coffin.some((name) => name.startsWith("coffin_lid"))).toBe(true);
    // Jars J5 and J6 stand on the rice barn's floor, 1.2 m up.
    for (const id of ["J5", "J6"])
      expect(getBounds(nodes.get(`jar_${id}_mesh`)!).min[1]).toBeGreaterThan(1);
  });

  it("has no water, no tent and no smoke threads left in it", () => {
    for (const name of nodes.keys()) {
      expect(name).not.toMatch(/^(paddy_water|pond|puddle|flood|tent_|fu_smoke)/);
    }
  });
});
