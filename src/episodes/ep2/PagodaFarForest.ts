import type { Scene } from "@babylonjs/core/scene";
import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import { Texture } from "@babylonjs/core/Materials/Textures/texture";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { VertexData } from "@babylonjs/core/Meshes/mesh.vertexData";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { Material } from "@babylonjs/core/Materials/material";
import { seededRandom } from "../../audio/synth";
import { CARD_COLUMNS, CARD_ROWS, paintForestCards } from "../ep1/act1/forestCards";
import { applyFoliageWind } from "../../render/FoliageWind";
import type { WindState } from "../../render/wind";
import { LOST_GARDEN, TANK_BASIN } from "./data/pagoda";

/** One far tree: a pair of crossed painted cards. Runtime X east, Z south. */
export interface FarTree {
  x: number;
  z: number;
  yaw: number;
  width: number;
  height: number;
  variant: number;
}

/** The compound's authored forest reaches about this far; cards begin beyond it. */
const INNER = { x: 46, z: 50 };
/** The pond's sunken basin, in the gap the compound's ground leaves for it. */
const POND_BASIN = { minX: -18.6, maxX: 18.6, minZ: -39.2, maxZ: -17.4 };

type Basin = { minX: number; maxX: number; minZ: number; maxZ: number };

/** Rectangles [x0, x1, z0, z1] covering a square of half-width `r`, minus the basins. */
export function floorPieces(r: number, basins: readonly Basin[]): number[][] {
  let pieces = [[-r, r, -r, r]];
  for (const { minX, maxX, minZ, maxZ } of basins)
    pieces = pieces.flatMap(([x0, x1, z0, z1]) => {
      if (minX >= x1 || maxX <= x0 || minZ >= z1 || maxZ <= z0) return [[x0, x1, z0, z1]];
      const out: number[][] = [];
      if (z0 < minZ) out.push([x0, x1, z0, minZ]);
      if (maxZ < z1) out.push([x0, x1, maxZ, z1]);
      const top = Math.max(z0, minZ),
        bottom = Math.min(z1, maxZ);
      if (x0 < minX) out.push([x0, minX, top, bottom]);
      if (maxX < x1) out.push([maxX, x1, top, bottom]);
      return out;
    });
  return pieces;
}

/**
 * Lays far trees in an elliptical belt from the authored forest out to the fog,
 * densest near, thinning far away, so the jungle seems to go on without end.
 */
export function layoutFarForest(seed = 6242202, count = 760, outer = 118): FarTree[] {
  const random = seededRandom(seed);
  const trees: FarTree[] = [];
  for (let tries = 0; trees.length < count && tries < count * 20; tries++) {
    const a = random() * Math.PI * 2;
    // Square-root-free bias towards the near edge of the belt.
    const t = random() ** 1.6;
    const ex = INNER.x + (outer - INNER.x) * t,
      ez = INNER.z + (outer - INNER.z) * t;
    const x = Math.cos(a) * ex,
      z = Math.sin(a) * ez + 1;
    // The lost garden has its own trees; a card standing in a lane would look flat.
    if (LOST_GARDEN.some((g) => x > g.minX && x < g.maxX && z > g.minZ && z < g.maxZ)) continue;
    trees.push({
      x,
      z,
      yaw: random() * Math.PI,
      width: 9 + random() * 7,
      height: 15 + random() * 13 + t * 6,
      variant: Math.floor(random() * CARD_COLUMNS * CARD_ROWS),
    });
  }
  return trees;
}

/** Builds the far forest and an endless dark forest floor under it. */
export function buildFarForest(scene: Scene, wind: WindState, ground: Material | null): Mesh[] {
  const cell = 256;
  const texture = new DynamicTexture(
    "T_ep2_far_cards",
    { width: cell * CARD_COLUMNS, height: cell * CARD_ROWS },
    scene,
    true,
    Texture.TRILINEAR_SAMPLINGMODE,
  );
  paintForestCards(
    texture.getContext() as unknown as CanvasRenderingContext2D,
    cell,
    seededRandom(6242203),
  );
  texture.hasAlpha = true;
  texture.update();
  // The same material name Episode 1 uses, so the shared wind treats these as far cards.
  const material = new PBRMaterial("M_forest_far_cards", scene);
  material.albedoTexture = texture;
  material.useAlphaFromAlbedoTexture = true;
  material.transparencyMode = PBRMaterial.PBRMATERIAL_ALPHATEST;
  material.alphaCutOff = 0.45;
  material.metallic = 0;
  material.roughness = 1;
  material.backFaceCulling = false;
  material.directIntensity = 0.7;
  material.environmentIntensity = 0.5;
  const meshes: Mesh[] = [];
  const cells = new Map<string, FarTree[]>();
  for (const tree of layoutFarForest()) {
    const key = `${Math.floor(tree.x / 40)},${Math.floor(tree.z / 40)}`;
    let list = cells.get(key);
    if (!list) cells.set(key, (list = []));
    list.push(tree);
  }
  for (const [key, list] of cells) {
    const positions: number[] = [],
      normals: number[] = [],
      uvs: number[] = [],
      heights: number[] = [],
      indices: number[] = [];
    for (const tree of list) {
      const col = tree.variant % CARD_COLUMNS,
        row = Math.floor(tree.variant / CARD_COLUMNS);
      const u0 = col / CARD_COLUMNS,
        u1 = (col + 1) / CARD_COLUMNS,
        vTop = 1 - row / CARD_ROWS,
        vBottom = 1 - (row + 1) / CARD_ROWS;
      for (let q = 0; q < 2; q++) {
        const a = tree.yaw + (q * Math.PI) / 2,
          dx = Math.cos(a) * (tree.width / 2),
          dz = Math.sin(a) * (tree.width / 2),
          v = positions.length / 3;
        for (const [side, up, u, vv] of [
          [-1, 0, u0, vBottom],
          [1, 0, u1, vBottom],
          [1, 1, u1, vTop],
          [-1, 1, u0, vTop],
        ]) {
          positions.push(tree.x + side * dx, -0.3 + up * tree.height, tree.z + side * dz);
          const n = new Vector3(
            side * Math.cos(a) * 0.7,
            0.35 + 0.65 * up,
            side * Math.sin(a) * 0.7,
          ).normalize();
          normals.push(n.x, n.y, n.z);
          uvs.push(u, vv);
          heights.push(up * tree.height, (tree.x * 0.05 + tree.z * 0.035) % 6.28);
        }
        indices.push(v, v + 2, v + 1, v, v + 3, v + 2);
      }
    }
    const mesh = new Mesh(`ep2_far_forest_${key}`, scene);
    const data = new VertexData();
    data.positions = positions;
    data.normals = normals;
    data.uvs = uvs;
    data.indices = indices;
    data.applyToMesh(mesh);
    mesh.setVerticesData("uv6", heights, false, 2);
    mesh.material = material;
    mesh.isPickable = false;
    mesh.receiveShadows = false;
    mesh.freezeWorldMatrix();
    meshes.push(mesh);
  }
  applyFoliageWind([material], wind);
  if (ground) {
    // The forest floor runs on under the far trees, just below the compound's own ground,
    // with holes for the sunken pond and tank, whose water lies lower still.
    const floor = new Mesh("ep2_far_forest_floor", scene);
    const positions: number[] = [],
      normals: number[] = [],
      uvs: number[] = [],
      indices: number[] = [];
    for (const [x0, x1, z0, z1] of floorPieces(130, [POND_BASIN, TANK_BASIN])) {
      const v = positions.length / 3;
      for (const [x, z] of [
        [x0, z0],
        [x0, z1],
        [x1, z1],
        [x1, z0],
      ]) {
        positions.push(x, -0.06, z);
        normals.push(0, 1, 0);
        uvs.push(x / 3, z / 3);
      }
      // Wound to face up under the area's imported materials; the other way round the
      // floor is culled and the night sky shows through as a dark blue ground.
      indices.push(v, v + 2, v + 1, v, v + 3, v + 2);
    }
    const data = new VertexData();
    data.positions = positions;
    data.normals = normals;
    data.uvs = uvs;
    data.indices = indices;
    data.applyToMesh(floor);
    floor.material = ground;
    floor.isPickable = false;
    floor.freezeWorldMatrix();
    meshes.push(floor);
  }
  return meshes;
}
