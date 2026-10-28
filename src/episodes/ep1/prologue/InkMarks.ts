import type { Scene } from "@babylonjs/core/scene";
import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { CreateTube } from "@babylonjs/core/Meshes/Builders/tubeBuilder";
import { CreateCylinder } from "@babylonjs/core/Meshes/Builders/cylinderBuilder";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { Vector3, Quaternion } from "@babylonjs/core/Maths/math.vector";
import type { FirstPersonHands } from "../../../player/FirstPersonHands";
import { drawingFrame } from "../../../player/DrawingPose";
import { makeDraftingSurface } from "./DraftingSurface";
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
  private lineSurface: AbstractMesh | null = null;
  private drawing = false;
  private readonly tweens: ((dt: number) => boolean)[] = [];
  /** Metres to the paper's local units. */
  private readonly m: number;

  constructor(
    private readonly scene: Scene,
    private readonly paper: AbstractMesh,
    private readonly hands?: FirstPersonHands,
  ) {
    this.ink = new PBRMaterial("M_wet_ink", scene);
    this.ink.albedoColor = new Color3(0.012, 0.01, 0.009);
    this.ink.roughness = 0.4;
    this.ink.metallic = 0;
    this.m = 1 / Math.abs(paper.scaling.x || 1);
    makeDraftingSurface(scene, paper);
  }

  update(dt: number): void {
    for (let i = this.tweens.length - 1; i >= 0; i--)
      if (this.tweens[i](dt)) this.tweens.splice(i, 1);
  }

  /** P02: pressure-varied nib lines follow the pencilled right roof and cornice. */
  async inkLine(seconds: number): Promise<void> {
    if (this.drawing) return;
    this.drawing = true;
    this.lineSurface?.dispose(false, true);
    const m = this.m;
    const surface = CreatePlane("ink_line", { width: 0.6 * m, height: 0.42 * m }, this.scene);
    this.lineSurface = surface;
    surface.parent = this.paper;
    surface.rotation.x = Math.PI / 2;
    surface.position.y = 0.0015 * m;
    surface.isPickable = false;
    const texture = new DynamicTexture(
      "T_fresh_drafting_ink",
      { width: 2048, height: 1434 },
      this.scene,
      true,
    );
    texture.hasAlpha = true;
    texture.uScale = -1;
    texture.uOffset = 1;
    texture.anisotropicFilteringLevel = 16;
    const c = texture.getContext() as CanvasRenderingContext2D;
    const mat = this.ink.clone("M_fresh_drafting_ink");
    mat.albedoTexture = texture;
    mat.useAlphaFromAlbedoTexture = true;
    mat.transparencyMode = PBRMaterial.PBRMATERIAL_ALPHABLEND;
    mat.backFaceCulling = false;
    mat.zOffset = -1;
    surface.material = mat;
    // Coordinates in the authored illustration's 2000 × 1400 drawing space.
    const strokes = [
      [
        [1006, 265],
        [1044, 343],
        [1090, 421],
        [1153, 493],
        [1191, 506],
      ],
      [
        [1009, 281],
        [1041, 352],
        [1084, 425],
        [1146, 495],
      ],
      [
        [1003, 507],
        [1065, 507],
        [1136, 507],
        [1190, 506],
      ],
      [
        [1013, 514],
        [1071, 515],
        [1137, 514],
        [1181, 513],
      ],
    ];
    const pen = this.makePen();
    const live = seconds > 0.05;
    pen.setEnabled(live);
    if (live) this.hands?.holdDrawing(pen);
    const baseRotation = pen.rotationQuaternion!.clone();
    let previous = -1;
    const draw = (progress: number) => {
      // Reserve a short approach and lift at either end; ink never precedes the nib.
      const amount = Math.max(0, Math.min(1, (progress - 0.12) / 0.76));
      const k = Math.min(strokes.length - 1, Math.floor(amount * strokes.length));
      const phase = Math.min(1, amount * strokes.length - k);
      const writingFraction = k === strokes.length - 1 ? 0.95 : 0.82;
      const contact = Math.min(1, phase / writingFraction);
      const inkProgress = contact * contact * (3 - 2 * contact);
      const painted = (k + inkProgress) / strokes.length;
      const step = Math.floor(painted * 600);
      if (step !== previous) {
        previous = step;
        c.clearRect(0, 0, 2048, 1434);
        c.save();
        c.scale(2048 / 2000, 1434 / 1400);
        c.strokeStyle = "#241e19";
        c.lineCap = "round";
        for (let k = 0; k < strokes.length; k++) {
          const points = strokes[k];
          const t = Math.max(0, Math.min(1, painted * strokes.length - k));
          for (let i = 1; i <= 100 * t; i++) {
            const sample = (v: number) => {
              const f = v * (points.length - 1);
              const index = Math.min(points.length - 2, Math.floor(f));
              const blend = f - index;
              return points[index].map((x, axis) => x + (points[index + 1][axis] - x) * blend);
            };
            const a = sample((i - 1) / 100),
              b = sample(i / 100);
            c.lineWidth =
              (k < 2 ? 1.5 : 1.1) * (0.42 + 0.58 * Math.sin((Math.PI * i) / 101)) +
              0.12 * Math.sin(i * 1.7);
            c.beginPath();
            c.moveTo(...(a as [number, number]));
            c.lineTo(...(b as [number, number]));
            c.stroke();
          }
          if (t < 1) break;
        }
        c.restore();
        texture.update();
      }
      // Recompute the nib from progress, independent of texture upload frequency.
      const points = strokes[k];
      const f = inkProgress * (points.length - 1),
        index = Math.min(points.length - 2, Math.floor(f));
      let tip = points[index].map((x, axis) => x + (points[index + 1][axis] - x) * (f - index));
      const reach =
        progress < 0.12 ? 1 - progress / 0.12 : progress > 0.88 ? (progress - 0.88) / 0.12 : 0;
      let lift = reach * reach * 0.05;
      if (phase > writingFraction && k < strokes.length - 1) {
        const travel = (phase - writingFraction) / (1 - writingFraction);
        const ease = travel * travel * (3 - 2 * travel);
        const end = points[points.length - 1],
          next = strokes[k + 1][0];
        tip = end.map((value, axis) => value + (next[axis] - value) * ease);
        lift += 0.008 * Math.sin(Math.PI * travel);
      }
      // Tiny wrist pivots follow the stroke; the nib remains the contact pivot.
      pen.rotationQuaternion = baseRotation.multiply(
        Quaternion.RotationYawPitchRoll(
          0.006 * Math.sin(phase * Math.PI * 2),
          0.009 * Math.sin(phase * Math.PI),
          0,
        ),
      );
      pen.position.set(
        ((0.5 - tip[0] / 2000) * 0.6 - reach * reach * 0.09) * m,
        (0.0016 + lift) * m,
        ((0.5 - tip[1] / 1400) * 0.42 - reach * reach * 0.065) * m,
      );
    };
    if (live) await this.tween(seconds, draw, false);
    else draw(1);
    this.hands?.holdDrawing(null);
    pen.dispose(false, true);
    mat.roughness = 0.78;
    this.drawing = false;
  }

  private makePen(): TransformNode {
    const root = new TransformNode("studio_drawing_dip_pen", this.scene);
    root.parent = this.paper;
    root.scaling.setAll(this.m);
    root.rotationQuaternion = drawingFrame().pen;
    const wood = new PBRMaterial("M_dip_pen_rosewood", this.scene);
    wood.albedoColor = Color3.FromHexString("#4b2618").toLinearSpace();
    wood.roughness = 0.35;
    const steel = new PBRMaterial("M_dip_pen_steel", this.scene);
    steel.albedoColor = Color3.FromHexString("#a99d79").toLinearSpace();
    steel.metallic = 0.85;
    steel.roughness = 0.28;
    const shaft = CreateCylinder(
      "studio_dip_pen_holder",
      { height: 0.145, diameterBottom: 0.0075, diameterTop: 0.0055, tessellation: 20 },
      this.scene,
    );
    shaft.parent = root;
    shaft.position.y = 0.095;
    shaft.material = wood;
    const ferrule = CreateCylinder(
      "studio_dip_pen_ferrule",
      { height: 0.019, diameter: 0.0075, tessellation: 20 },
      this.scene,
    );
    ferrule.parent = root;
    ferrule.position.y = 0.024;
    ferrule.material = steel;
    for (const side of [-1, 1]) {
      const nib = CreateTube(
        `studio_split_nib_${side}`,
        {
          path: [
            new Vector3(side * 0.00015, 0, 0),
            new Vector3(side * 0.0015, 0.009, 0.0005),
            new Vector3(side * 0.002, 0.017, 0),
          ],
          radius: 0.0007,
          tessellation: 8,
        },
        this.scene,
      );
      nib.parent = root;
      nib.material = steel;
    }
    for (const mesh of root.getChildMeshes()) {
      mesh.isPickable = false;
      // Share the hand's depth pass: fingers occlude the shaft correctly and
      // the remote desk light cannot project a huge, detached pencil shadow.
      mesh.renderingGroupId = 1;
      mesh.alwaysSelectAsActiveMesh = true;
    }
    return root;
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

  private tween(seconds: number, apply: (k: number) => void, ease = true): Promise<void> {
    return new Promise((done) => {
      let t = 0;
      this.tweens.push((dt) => {
        t = Math.min(1, t + dt / seconds);
        apply(ease ? 1 - (1 - t) ** 3 : t);
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
