import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import { Texture } from "@babylonjs/core/Materials/Textures/texture";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import type { Scene } from "@babylonjs/core/scene";
import { seeded } from "./drawings";

/** Tactile close-range surfaces; deterministic, generated once per book. */
export function bookMaterials(scene: Scene): {
  leather: PBRMaterial;
  edges: PBRMaterial;
  linen: PBRMaterial;
  ribbon: PBRMaterial;
} {
  const material = (name: string, colour: string, roughness: number) => {
    const m = new PBRMaterial(`M_sketchbook_${name}`, scene);
    m.albedoColor = Color3.FromHexString(colour);
    m.metallic = 0;
    m.roughness = roughness;
    m.maxSimultaneousLights = 4;
    return m;
  };
  const leather = material("leather", "#684631", 0.84);
  const size = 512;
  const colour = new DynamicTexture(
    "T_book_leather",
    size,
    scene,
    true,
    Texture.TRILINEAR_SAMPLINGMODE,
  );
  const ctx = colour.getContext() as unknown as CanvasRenderingContext2D;
  const image = ctx.createImageData(size, size);
  const rand = seeded("sora-worn-leather");
  for (let y = 0; y < size; y++)
    for (let x = 0; x < size; x++) {
      const edge = Math.min(x, y, size - 1 - x, size - 1 - y);
      const wear = Math.exp(-edge / 9) * 34;
      const pores = (rand() - 0.5) * 22 + Math.sin(x * 0.09 + Math.cos(y * 0.05)) * 3;
      const i = (y * size + x) * 4;
      image.data[i] = 142 + pores + wear;
      image.data[i + 1] = 119 + pores + wear;
      image.data[i + 2] = 97 + pores + wear;
      image.data[i + 3] = 255;
    }
  ctx.putImageData(image, 0, 0);
  // A quiet stitched border, under the leather's worn turn-in.
  ctx.strokeStyle = "rgba(204,172,124,0.55)";
  ctx.lineWidth = 1.1;
  ctx.setLineDash([3, 4]);
  ctx.strokeRect(11, 11, size - 22, size - 22);
  ctx.setLineDash([]);
  for (let k = 0; k < 90; k++) {
    const x = rand() * size,
      y = rand() * size;
    ctx.strokeStyle = `rgba(216,183,139,${0.03 + rand() * 0.08})`;
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x + rand() * 14, y - rand() * 3);
    ctx.stroke();
  }
  colour.update();
  leather.albedoTexture = colour;
  const normal = new DynamicTexture("T_book_leather_normal", size, scene, true);
  const nctx = normal.getContext() as unknown as CanvasRenderingContext2D;
  const normals = nctx.createImageData(size, size);
  for (let i = 0; i < normals.data.length; i += 4) {
    normals.data[i] = 128 + (rand() - 0.5) * 36;
    normals.data[i + 1] = 128 + (rand() - 0.5) * 36;
    normals.data[i + 2] = 252;
    normals.data[i + 3] = 255;
  }
  nctx.putImageData(normals, 0, 0);
  normal.update();
  normal.level = 0.22;
  leather.bumpTexture = normal;
  const edges = material("paper_edges", "#d4c3a3", 0.98);
  const grain = new DynamicTexture("T_book_paper_edges", { width: 256, height: 128 }, scene, true);
  const g = grain.getContext();
  g.fillStyle = "#dacbae";
  g.fillRect(0, 0, 256, 128);
  for (let y = 0; y < 128; y += 2) {
    g.fillStyle = `rgba(86,66,43,${0.08 + rand() * 0.2})`;
    g.fillRect(0, y, 256, 0.5 + rand() * 0.6);
  }
  grain.update();
  edges.albedoColor = Color3.White();
  edges.albedoTexture = grain;
  return {
    leather,
    edges,
    linen: material("binding_linen", "#99886c", 1),
    ribbon: material("ribbon", "#713d32", 0.96),
  };
}
