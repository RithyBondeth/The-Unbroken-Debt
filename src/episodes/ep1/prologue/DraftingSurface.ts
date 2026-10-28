import type { Scene } from "@babylonjs/core/scene";
import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { VertexData } from "@babylonjs/core/Meshes/mesh.vertexData";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { Texture } from "@babylonjs/core/Materials/Textures/texture";
import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import { seededRandom } from "../../../audio/synth";

/** Fine cotton paper, with an actual lifted edge rather than a thick white box. */
export function makeDraftingSurface(scene: Scene, anchor: AbstractMesh): void {
  const m = 1 / Math.abs(anchor.scaling.x || 1);
  // Keep the original pick target, but replace its visible slab with a thin sheet.
  anchor.visibility = 0;
  const sheet = new Mesh("studio_cotton_drawing_sheet", scene);
  sheet.parent = anchor;
  sheet.isPickable = false;
  sheet.receiveShadows = true;
  const positions: number[] = [],
    uvs: number[] = [],
    indices: number[] = [];
  const nx = 40,
    nz = 28;
  for (let j = 0; j <= nz; j++)
    for (let i = 0; i <= nx; i++) {
      const u = i / nx,
        v = j / nz;
      const edge = Math.pow(Math.abs(u - 0.5) * 2, 12);
      const curl = edge * (0.0006 + 0.0012 * Math.sin(v * Math.PI) ** 2);
      positions.push((u - 0.5) * 0.6 * m, (0.0011 + curl) * m, (v - 0.5) * 0.42 * m);
      uvs.push(1 - u, v);
      if (i < nx && j < nz) {
        const a = j * (nx + 1) + i;
        indices.push(a, a + 1, a + nx + 1, a + 1, a + nx + 2, a + nx + 1);
      }
    }
  const normals: number[] = [];
  VertexData.ComputeNormals(positions, indices, normals);
  const data = new VertexData();
  Object.assign(data, { positions, indices, normals, uvs });
  data.applyToMesh(sheet);
  const paper = new PBRMaterial("M_studio_cotton_drawing", scene);
  paper.albedoTexture = new Texture(
    `${import.meta.env.BASE_URL}assets/ep1/drafting/illustration.png`,
    scene,
  );
  paper.albedoTexture.anisotropicFilteringLevel = 16;
  paper.roughness = 0.94;
  paper.metallic = 0;
  paper.backFaceCulling = false;
  paper.maxSimultaneousLights = 8;
  const grain = new DynamicTexture("T_drawing_paper_tooth", 256, scene, true);
  const c = grain.getContext();
  const random = seededRandom(193208);
  c.fillStyle = "#8080ff";
  c.fillRect(0, 0, 256, 256);
  for (let i = 0; i < 16000; i++) {
    const value = 104 + Math.floor(random() * 48);
    c.fillStyle = `rgb(${124 + (value % 9)},${124 + ((value * 3) % 9)},255)`;
    c.fillRect(random() * 256, random() * 256, 0.5, 1 + random() * 2);
  }
  grain.update();
  grain.gammaSpace = false;
  grain.uScale = 5;
  grain.vScale = 4;
  grain.level = 0.12;
  paper.bumpTexture = grain;
  sheet.material = paper;
}
