import type { Scene } from "@babylonjs/core/scene";
import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { CreateBox } from "@babylonjs/core/Meshes/Builders/boxBuilder";
import { CreatePlane } from "@babylonjs/core/Meshes/Builders/planeBuilder";
import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { seededRandom } from "../../../audio/synth";

/**
 * Fresh ink on the illustration: the line Sora inks at P02, and the blot that
 * spills across the drawing at P05 (sketchbook entry SB-01). Both lie on the
 * paper in its own space: x across (−x is the picture's right), z up the
 * picture, y out of the paper (glTF axes of the `interact_illustration` box).
 * Sizes are in metres, divided by the paper node's scale (the exporter keeps it).
 */
export class InkMarks {
  private readonly ink: PBRMaterial;
  private readonly tweens: ((dt: number) => boolean)[] = [];
  /** Metres to the paper's local units. */
  private readonly m: number;

  constructor(
    private readonly scene: Scene,
    private readonly paper: AbstractMesh,
  ) {
    this.ink = new PBRMaterial("M_wet_ink", scene);
    this.ink.albedoColor = new Color3(0.012, 0.01, 0.009);
    this.ink.roughness = 0.4;
    this.ink.metallic = 0;
    this.m = 1 / Math.abs(paper.scaling.x || 1);
  }

  update(dt: number): void {
    for (let i = this.tweens.length - 1; i >= 0; i--)
      if (this.tweens[i](dt)) this.tweens.splice(i, 1);
  }

  /** P02: a pen stroke carries the ink on into the pencilled half. */
  inkLine(seconds: number): Promise<void> {
    const m = this.m;
    const line = CreateBox(
      "ink_line",
      { width: 1, height: 0.0003 * m, depth: 0.003 * m },
      this.scene,
    );
    line.material = this.ink;
    line.parent = this.paper;
    line.isPickable = false;
    const length = 0.07 * m;
    const start = 0.004 * m;
    line.position.set(-start, 0.0012 * m, 0.035 * m);
    line.scaling.x = 0.0001;
    return this.tween(seconds, (k) => {
      line.scaling.x = Math.max(0.0001, length * k);
      line.position.x = -start - (length * k) / 2;
    });
  }

  /** P05: the ink jar's spill runs across the drawing. */
  spill(seconds: number): Promise<void> {
    const m = this.m;
    const blot = CreatePlane("ink_blot", { size: 0.24 * m }, this.scene);
    blot.parent = this.paper;
    blot.isPickable = false;
    blot.rotation.x = Math.PI / 2;
    blot.position.set(-0.03 * m, 0.0016 * m, 0.0);
    const material = this.ink.clone("M_ink_blot");
    material.albedoTexture = blotTexture(this.scene);
    material.useAlphaFromAlbedoTexture = true;
    material.transparencyMode = PBRMaterial.PBRMATERIAL_ALPHATEST;
    material.alphaCutOff = 0.45;
    blot.material = material;
    blot.scaling.setAll(0.05);
    return this.tween(seconds, (k) => blot.scaling.setAll(0.05 + 0.95 * k));
  }

  private tween(seconds: number, apply: (k: number) => void): Promise<void> {
    return new Promise((done) => {
      let t = 0;
      this.tweens.push((dt) => {
        t = Math.min(1, t + dt / seconds);
        apply(1 - (1 - t) ** 3);
        if (t < 1) return false;
        done();
        return true;
      });
    });
  }
}

/** An ink blot: a pool with lobes where it ran, and splashes thrown off it. */
function blotTexture(scene: Scene): DynamicTexture {
  const size = 512;
  const texture = new DynamicTexture("T_ink_blot", size, scene, true);
  const ctx = texture.getContext() as CanvasRenderingContext2D;
  const rand = seededRandom(812);
  ctx.clearRect(0, 0, size, size);
  ctx.fillStyle = "#000";
  const c = size / 2;
  ctx.beginPath();
  const n = 48;
  for (let i = 0; i <= n; i++) {
    const a = (i / n) * Math.PI * 2;
    const r = size * (0.2 + 0.05 * Math.sin(a * 3 + 1) + 0.04 * Math.sin(a * 7) + rand() * 0.03);
    const x = c + Math.cos(a) * r;
    const y = c + Math.sin(a) * r * 0.85;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.fill();
  for (let k = 0; k < 5; k++) {
    // Runs where the ink flowed down the sloping board.
    const a = rand() * Math.PI * 2;
    const len = size * (0.12 + rand() * 0.14);
    ctx.lineWidth = size * (0.03 + rand() * 0.04);
    ctx.lineCap = "round";
    ctx.beginPath();
    ctx.moveTo(c + Math.cos(a) * size * 0.15, c + Math.sin(a) * size * 0.13);
    ctx.lineTo(c + Math.cos(a) * (size * 0.15 + len), c + Math.sin(a) * (size * 0.13 + len));
    ctx.strokeStyle = "#000";
    ctx.stroke();
  }
  for (let k = 0; k < 40; k++) {
    const a = rand() * Math.PI * 2;
    const r = size * (0.27 + rand() * 0.2);
    ctx.beginPath();
    ctx.arc(
      c + Math.cos(a) * r,
      c + Math.sin(a) * r,
      size * (0.004 + rand() ** 2 * 0.02),
      0,
      Math.PI * 2,
    );
    ctx.fill();
  }
  texture.hasAlpha = true;
  texture.update();
  return texture;
}
