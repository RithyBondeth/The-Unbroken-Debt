import type { Scene } from "@babylonjs/core/scene";
import type { Mesh } from "@babylonjs/core/Meshes/mesh";
import { StandardMaterial } from "@babylonjs/core/Materials/standardMaterial";
import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { seededRandom } from "@/audio/synth";
import { TAXI_WINDOW } from "./taxiApparitions";

/** Where the face pressed and the two palms struck, in the glass's UV (u forward, v up). */
const FACE = { u: 0.31, v: 0.47 };
const PALMS = [
  { u: 0.14, v: 0.55, turn: -0.35, scale: 1 },
  { u: 0.47, v: 0.6, turn: 0.28, scale: 0.94 },
] as const;

/** One greasy palm print with its five fingers, and the runs where it dragged down the wet glass. */
function palm(
  c: CanvasRenderingContext2D,
  x: number,
  y: number,
  turn: number,
  scale: number,
  rand: () => number,
): void {
  c.save();
  c.translate(x, y);
  c.rotate(turn);
  c.scale(scale, scale);
  const grease = (a: number) =>
    `rgba(${196 + rand() * 20},${192 + rand() * 18},${184 + rand() * 14},${a})`;
  // The palm: a heel, a broad pad under the fingers, and the hollow between pressed lighter.
  c.fillStyle = grease(0.42);
  c.beginPath();
  c.ellipse(0, 12, 27, 32, 0, 0, Math.PI * 2);
  c.fill();
  c.globalCompositeOperation = "destination-out";
  c.fillStyle = "rgba(0,0,0,0.25)";
  c.beginPath();
  c.ellipse(3, 14, 12, 15, 0.3, 0, Math.PI * 2);
  c.fill();
  c.globalCompositeOperation = "source-over";
  // Long, thin fingers, spread wide as if it caught itself on the glass.
  const fingers = [
    [-26, -2, -0.75, 30, 6.5],
    [-15, -22, -0.22, 48, 6],
    [-1, -26, 0, 54, 6.2],
    [13, -22, 0.2, 50, 5.8],
    [24, -10, 0.5, 40, 5.2],
  ] as const;
  for (const [fx, fy, angle, length, width] of fingers) {
    c.save();
    c.translate(fx, fy);
    c.rotate(angle);
    c.fillStyle = grease(0.46);
    c.beginPath();
    c.ellipse(0, -length / 2, width, length / 2, 0, 0, Math.PI * 2);
    c.fill();
    // The pad of the fingertip pressed hardest.
    c.fillStyle = grease(0.3);
    c.beginPath();
    c.ellipse(0, -length + width, width * 0.9, width * 1.3, 0, 0, Math.PI * 2);
    c.fill();
    c.restore();
  }
  // Skin texture and grit broken through the print.
  c.globalCompositeOperation = "destination-out";
  for (let i = 0; i < 260; i++) {
    c.fillStyle = `rgba(0,0,0,${0.2 + rand() * 0.5})`;
    c.fillRect(-34 + rand() * 68, -80 + rand() * 128, 1 + rand() * 2.5, 1 + rand() * 2.5);
  }
  c.globalCompositeOperation = "source-over";
  // Rain has caught the print and run down from it.
  for (let i = 0; i < 6; i++) {
    const sx = -22 + rand() * 44,
      len = 50 + rand() * 120;
    const g = c.createLinearGradient(0, 36, 0, 36 + len);
    g.addColorStop(0, grease(0.3));
    g.addColorStop(1, grease(0));
    c.fillStyle = g;
    c.fillRect(sx, 36, 1.5 + rand() * 3, len);
  }
  c.restore();
}

/**
 * What the face at Sora's window leaves behind: two muddy palm prints with their
 * runs, and a bloom of breath on the inside of the cold glass where its mouth was
 * (it breathed on her side). The prints stay for the rest of the ride, washing
 * slowly in the rain; the lightning shows them up.
 */
export class TaxiGlassMarks {
  private readonly material: StandardMaterial;
  private readonly prints: DynamicTexture;
  private readonly breath: StandardMaterial;

  constructor(scene: Scene, glass: Mesh) {
    const size = 512;
    this.prints = new DynamicTexture(
      "taxi_window_handprints",
      { width: size, height: size },
      scene,
      true,
    );
    const c = this.prints.getContext() as unknown as CanvasRenderingContext2D;
    c.clearRect(0, 0, size, size);
    const rand = seededRandom(6060);
    // The glass's V runs top-down on this canvas: each print is drawn turned over.
    for (const p of PALMS)
      palm(c, p.u * size, (1 - p.v) * size, p.turn + Math.PI, p.scale * 1.45, rand);
    this.prints.hasAlpha = true;
    this.prints.update();
    this.material = new StandardMaterial("M_taxi_window_handprints", scene);
    this.material.diffuseTexture = this.prints;
    this.material.useAlphaFromDiffuseTexture = true;
    this.material.diffuseColor = new Color3(0.8, 0.8, 0.78);
    this.material.specularColor = new Color3(0.3, 0.3, 0.3);
    this.material.backFaceCulling = false;
    this.material.alpha = 0;
    this.material.zOffset = -3;
    const marks = glass.clone("taxi_window_handprints", glass.parent);
    marks.material = this.material;
    marks.isPickable = false;
    // Just inside the glass the face was outside: the prints were pressed from the other side.
    const inward = -Math.sign(glass.getBoundingInfo().boundingBox.centerWorld.x);
    marks.setAbsolutePosition(glass.getAbsolutePosition().add(new Vector3(inward * 0.004, 0, 0)));

    const fog = new DynamicTexture("taxi_window_breath", { width: 256, height: 256 }, scene, true);
    const f = fog.getContext() as unknown as CanvasRenderingContext2D;
    f.clearRect(0, 0, 256, 256);
    const x = FACE.u * 256,
      y = (1 - FACE.v) * 256;
    const g = f.createRadialGradient(x, y, 0, x, y, 30);
    g.addColorStop(0, "rgba(200,206,210,0.55)");
    g.addColorStop(0.6, "rgba(200,206,210,0.3)");
    g.addColorStop(1, "rgba(200,206,210,0)");
    f.fillStyle = g;
    f.fillRect(0, 0, 256, 256);
    fog.hasAlpha = true;
    fog.update();
    this.breath = new StandardMaterial("M_taxi_window_breath", scene);
    this.breath.diffuseTexture = fog;
    this.breath.useAlphaFromDiffuseTexture = true;
    this.breath.emissiveColor = new Color3(0.16, 0.17, 0.18);
    this.breath.specularColor = Color3.Black();
    this.breath.backFaceCulling = false;
    this.breath.alpha = 0;
    this.breath.zOffset = -4;
    const bloom = glass.clone("taxi_window_breath", glass.parent);
    bloom.material = this.breath;
    bloom.isPickable = false;
    bloom.setAbsolutePosition(glass.getAbsolutePosition().add(new Vector3(inward * 0.006, 0, 0)));
  }

  update(t: number, flash: number): void {
    const since = t - TAXI_WINDOW.beat;
    // The prints land with the slap and fade only slowly in the rain.
    this.material.alpha = since < 0 ? 0 : Math.max(0.45, 1 - since / 30);
    // Grease on wet glass catches whatever light there is: faint at night, stark in a flash.
    this.material.emissiveColor.set(0.4, 0.41, 0.43).scaleInPlace(0.3 + flash * 0.7);
    // Breath condenses while it is there, then evaporates over a few seconds.
    this.breath.alpha =
      since < -0.35 ? 0 : since < 0.4 ? (since + 0.35) / 0.75 : Math.max(0, 1 - (since - 0.4) / 4);
  }
}
