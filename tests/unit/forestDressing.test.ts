import { describe, expect, it } from "vitest";
import { NullEngine } from "@babylonjs/core/Engines/nullEngine";
import { Scene } from "@babylonjs/core/scene";
import { AssetContainer } from "@babylonjs/core/assetContainer";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { CreateCylinder } from "@babylonjs/core/Meshes/Builders/cylinderBuilder";
import { CreateSphere } from "@babylonjs/core/Meshes/Builders/sphereBuilder";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { seededRandom } from "../../src/audio/synth";
import {
  TRUNK_BINS,
  bakePlantHeights,
  flexOf,
  measureTrunk,
  plantPhase,
  treeVoice,
  trunkRadius,
} from "../../src/render/plantHeights";
import { grassChance, layoutGrass } from "../../src/episodes/ep1/data/grass";
import { PATH, ROAD_Z, pathDistance } from "../../src/episodes/ep1/data/forestBorder";
import { SAVE_SHRINE_POSITION } from "../../src/episodes/ep1/data/saveShrine";
import { grassClumpData } from "../../src/episodes/ep1/act1/TallGrass";
import { tube } from "../../src/episodes/ep1/act1/TreeOmens";
import { BOUNDARY_CORD, DRESSED_TRUNKS, OMEN_FIG } from "../../src/episodes/ep1/data/treeOmens";

describe("plant heights for the wind", () => {
  it("knows how each plant bends and sounds by its name", () => {
    expect(flexOf("bamboo_3")).toBeGreaterThan(flexOf("tree_12"));
    expect(flexOf("dead_6")).toBeLessThan(flexOf("tree_12"));
    expect(treeVoice("bamboo_7")).toBe("bamboo");
    expect(treeVoice("coco_0")).toBe("palm");
    expect(treeVoice("dead_3")).toBe("dead");
    expect(treeVoice("tree_301")).toBe("leafy");
    expect(treeVoice("fern_02_a.001")).toBeNull();
    const phases = [plantPhase(1, 2), plantPhase(1.5, 2), plantPhase(40, -3)];
    for (const p of phases) {
      expect(p).toBeGreaterThanOrEqual(0);
      expect(p).toBeLessThan(Math.PI * 2);
    }
    expect(new Set(phases).size).toBe(3);
    expect(plantPhase(1, 2)).toBe(phases[0]);
  });

  it("measures a trunk's centre and its radius all the way round", () => {
    const points: number[] = [];
    for (let k = 0; k < 400; k++) {
      const a = (k / 400) * Math.PI * 2 * 7,
        y = 0.5 + (k / 400) * 2;
      const r = 0.3 + (Math.cos(a) > 0.9 ? 0.08 : 0);
      points.push(2 + Math.cos(a) * r, y, 5 + Math.sin(a) * r);
    }
    const trunk = measureTrunk(points, 0.8, 1.8)!;
    expect(trunk.x).toBeCloseTo(2, 1);
    expect(trunk.z).toBeCloseTo(5, 1);
    expect(trunk.radii.length).toBe(TRUNK_BINS);
    expect(trunkRadius(trunk, Math.PI)).toBeCloseTo(0.3, 1);
    expect(trunkRadius(trunk, 0)).toBeGreaterThan(trunkRadius(trunk, Math.PI));
    expect(trunkRadius(trunk, Math.PI * 4 + 1)).toBeCloseTo(trunkRadius(trunk, 1));
    expect(measureTrunk([0, 0, 0], 0.8, 1.8)).toBeNull();
    const wide = points.map((v, i) => (i % 3 === 1 ? v : v * 6));
    expect(measureTrunk(wide, 0.8, 1.8)).toBeNull();
  });

  it("bakes height above the foot and one phase per plant into uv6, and lists its trunk", () => {
    const engine = new NullEngine(),
      scene = new Scene(engine);
    try {
      const container = new AssetContainer(scene);
      const root = new TransformNode("__root__", scene);
      const tree = new TransformNode("tree_12", scene);
      tree.parent = root;
      tree.position.set(4, 1, -2);
      const trunk = CreateCylinder(
        "tree_12_primitive0",
        { height: 6, diameter: 0.5, subdivisions: 12 },
        scene,
      );
      trunk.material = new PBRMaterial("M_wet_bark", scene);
      trunk.parent = tree;
      trunk.position.y = 3;
      const crown = CreateSphere("tree_12_primitive1", { diameter: 4 }, scene);
      crown.material = new PBRMaterial("M_forest_leaf", scene);
      crown.parent = tree;
      crown.position.y = 6;
      const rock = CreateSphere("rock", { diameter: 1 }, scene);
      rock.material = new PBRMaterial("M_stone", scene);
      container.meshes.push(trunk, crown, rock);
      container.transformNodes.push(root, tree);
      const sites = bakePlantHeights(container);
      expect(rock.isVerticesDataPresent("uv6")).toBe(false);
      for (const mesh of [trunk, crown]) {
        const uv6 = mesh.getVerticesData("uv6")!;
        const heights = uv6.filter((_, i) => i % 2 === 0);
        expect(Math.min(...heights)).toBeGreaterThanOrEqual(0);
        expect(new Set(uv6.filter((_, i) => i % 2 === 1)).size).toBe(1);
      }
      const top = Math.max(...crown.getVerticesData("uv6")!.filter((_, i) => i % 2 === 0));
      expect(top).toBeCloseTo(8 * flexOf("tree_12"), 1);
      expect(sites).toHaveLength(1);
      expect(sites[0].voice).toBe("leafy");
      expect(sites[0].trunk!.x).toBeCloseTo(4, 1);
      expect(trunkRadius(sites[0].trunk!, 1)).toBeCloseTo(0.25, 1);
    } finally {
      scene.dispose();
      engine.dispose();
    }
  });
});

describe("tall grass", () => {
  it("grows on the verges, never on the trodden path, the road or the shrine's clearing", () => {
    for (const [x, z] of PATH) expect(grassChance(x, z)).toBe(0);
    expect(grassChance(0, ROAD_Z)).toBe(0);
    expect(grassChance(SAVE_SHRINE_POSITION.x, SAVE_SHRINE_POSITION.z)).toBe(0);
    expect(grassChance(0, -10)).toBe(0); // the swept yard
    expect(grassChance(4.2, 31)).toBeGreaterThan(0.6); // a step off the path
    expect(grassChance(10, ROAD_Z - 3.2)).toBeGreaterThan(0.5); // the road bank
  });

  it("lays out the same clumps every time, fewer when spaced wider, clear of art", () => {
    const options = { spacing: 0.7, clear: () => true };
    const a = layoutGrass(options),
      b = layoutGrass(options);
    expect(a).toEqual(b);
    expect(layoutGrass({ ...options, spacing: 1 }).length).toBeLessThan(a.length * 0.7);
    expect(a.every((c) => pathDistance(c.x, c.z) >= 0.9 || c.z < 2 || c.z > 61)).toBe(true);
    expect(a.every((c) => c.scale > 0.25 && c.scale < 1.2)).toBe(true);
    const blocked = layoutGrass({ ...options, clear: (x) => x < 0 });
    expect(blocked.every((c) => c.x < 0)).toBe(true);
    expect(new Set(a.map((c) => c.variant))).toEqual(new Set([0, 1, 2]));
  });

  it("builds a clump of tapering blades rooted at the origin", () => {
    const data = grassClumpData(seededRandom(1), 16, 4);
    const positions = data.positions!;
    const n = positions.length / 3;
    expect(n).toBe(16 * 5 * 2);
    expect(data.indices!.length).toBe(16 * 4 * 6);
    expect(Math.max(...data.indices!)).toBeLessThan(n);
    const ys = positions.filter((_, i) => i % 3 === 1);
    expect(Math.min(...ys)).toBeCloseTo(0);
    expect(Math.max(...ys)).toBeLessThanOrEqual(1.01);
    expect(data.colors!.every((c) => c >= 0 && c <= 1)).toBe(true);
  });
});

describe("tree omens", () => {
  it("builds tubes with rings, UVs and wind for every vertex", () => {
    const out = { positions: [], normals: [], uvs: [], wind: [], indices: [] };
    const path = [new Vector3(0, 0, 0), new Vector3(0, 1, 0), new Vector3(0.2, 2, 0)];
    tube(
      out,
      path,
      () => 0.1,
      6,
      (i) => i * 0.5,
      1.2,
    );
    const n = out.positions.length / 3;
    expect(n).toBe(3 * 7);
    expect(out.uvs.length).toBe(n * 2);
    expect(out.wind.length).toBe(n * 2);
    expect(out.indices.length).toBe(2 * 6 * 6);
    expect(out.wind.slice(-2)).toEqual([1, 1.2]);
    for (let i = 0; i < 7; i++) {
      const [x, , z] = out.positions.slice(i * 3, i * 3 + 3);
      expect(Math.hypot(x, z)).toBeCloseTo(0.1);
    }
  });

  it("marks trunks a step off the path, keeps the fig off it, and strings the cord across it", () => {
    for (const trunk of DRESSED_TRUNKS) {
      const d = pathDistance(trunk.x, trunk.z);
      expect(d).toBeGreaterThan(2);
      expect(d).toBeLessThan(9);
      expect(trunk.threads.length).toBeGreaterThan(0);
    }
    expect(DRESSED_TRUNKS.filter((t) => t.blood).length).toBeGreaterThanOrEqual(2);
    expect(pathDistance(OMEN_FIG.x, OMEN_FIG.z)).toBeGreaterThan(4.5);
    const [ax, az] = BOUNDARY_CORD.from,
      [bx, bz] = BOUNDARY_CORD.to;
    expect(pathDistance(ax, az)).toBeGreaterThan(1.5);
    expect(pathDistance(bx, bz)).toBeGreaterThan(1.5);
    expect(pathDistance((ax + bx) / 2, (az + bz) / 2)).toBeLessThan(1);
    // High enough to walk under.
    expect(BOUNDARY_CORD.height - 4 * 0.32 * 0.25).toBeGreaterThan(1.75);
  });
});
