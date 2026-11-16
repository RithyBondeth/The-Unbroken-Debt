import type { Scene } from "@babylonjs/core/scene";
import type { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import { Texture } from "@babylonjs/core/Materials/Textures/texture";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { VertexData } from "@babylonjs/core/Meshes/mesh.vertexData";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { seededRandom } from "@/audio/synth";
import { CARD_COLUMNS, CARD_ROWS, paintForestCards } from "./forestCards";
import { applyFoliageWind } from "./FoliageWind";
import type { WindState } from "./wind";

/**
 * One far tree as Episode 2's far forest draws it: a pair of crossed painted cards
 * (`forestCards.ts`), its foot at (x, y, z) in whatever frame the meshes are parented to.
 */
export interface FarTreeCard {
  x: number;
  y: number;
  z: number;
  yaw: number;
  width: number;
  height: number;
  /** Atlas cell, 0–7 (see `paintForestCards`). */
  variant: number;
  /** Which batch the card is merged into, so far batches can be culled or switched off. */
  cell: string;
}

/** Atlas cells: broadleaf crowns, the emergent with buttresses, palms, bamboo, dead. */
export const CARD_VARIANT = {
  broadleaf: [0, 1, 2],
  emergent: 3,
  sugarPalm: 4,
  bamboo: 5,
  coconut: 6,
  dead: 7,
} as const;

/**
 * The far-forest card material, under the name the shared wind (`FoliageWind`) and
 * Episodes 1 and 2 use for it. Painted once per scene.
 */
export function farTreeCardMaterial(scene: Scene, seed = 6242203): PBRMaterial {
  const existing = scene.getMaterialByName("M_forest_far_cards");
  if (existing instanceof PBRMaterial) return existing;
  const cell = 256;
  const texture = new DynamicTexture(
    "T_far_tree_cards",
    { width: cell * CARD_COLUMNS, height: cell * CARD_ROWS },
    scene,
    true,
    Texture.TRILINEAR_SAMPLINGMODE,
  );
  paintForestCards(
    texture.getContext() as unknown as CanvasRenderingContext2D,
    cell,
    seededRandom(seed),
  );
  texture.hasAlpha = true;
  texture.update();
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
  return material;
}

/**
 * Merges far tree cards into one mesh per cell, with the per-vertex heights the
 * shared wind bends crowns by. Meshes are parented to `parent` when given (a moving
 * route, say); otherwise their world matrices are frozen.
 */
export function buildFarTreeCards(
  scene: Scene,
  name: string,
  trees: readonly FarTreeCard[],
  wind: WindState,
  parent?: TransformNode,
): Mesh[] {
  const material = farTreeCardMaterial(scene);
  const cells = new Map<string, FarTreeCard[]>();
  for (const tree of trees) {
    let list = cells.get(tree.cell);
    if (!list) cells.set(tree.cell, (list = []));
    list.push(tree);
  }
  const meshes: Mesh[] = [];
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
          positions.push(tree.x + side * dx, tree.y + up * tree.height, tree.z + side * dz);
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
    const mesh = new Mesh(`${name}_${key}`, scene);
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
    if (parent) mesh.parent = parent;
    else mesh.freezeWorldMatrix();
    meshes.push(mesh);
  }
  applyFoliageWind([material], wind);
  return meshes;
}
