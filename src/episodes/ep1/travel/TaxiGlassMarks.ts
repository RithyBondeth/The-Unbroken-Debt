import type { Scene } from "@babylonjs/core/scene";
import type { Mesh } from "@babylonjs/core/Meshes/mesh";
import { StandardMaterial } from "@babylonjs/core/Materials/standardMaterial";
import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { seededRandom } from "@/audio/synth";
import { TAXI_WINDOW, taxiPass, taxiPassBeat } from "./taxiApparitions";

/**
 * Where the ghost's face presses and her two wet palms strike on Sora's side glass
 * (in glass UV: u=0 front -> u=1 rear, v=0 sill -> v=1 header).
 */
const FACE = { u: 0.48, v: 0.61 };
const PALMS = [
  { u: 0.27, v: 0.47, turn: -0.24, scale: 0.84, flip: 1 },
  { u: 0.69, v: 0.51, turn: 0.22, scale: 0.8, flip: -1 },
] as const;

/** Soft organic radial smudge blob so prints look like real damp skin & mud on glass, never crisp geometric ovals. */
function smudge(
  c: CanvasRenderingContext2D,
  x: number,
  y: number,
  rx: number,
  ry: number,
  rot: number,
  alpha: number,
): void {
  c.save();
  c.translate(x, y);
  c.rotate(rot);
  c.scale(1, ry / Math.max(0.1, rx));
  const g = c.createRadialGradient(0, 0, rx * 0.12, 0, 0, rx);
  g.addColorStop(0, `rgba(182,176,164,${alpha.toFixed(3)})`);
  g.addColorStop(0.55, `rgba(168,162,150,${(alpha * 0.62).toFixed(3)})`);
  g.addColorStop(1, "rgba(155,150,140,0)");
  c.fillStyle = g;
  c.beginPath();
  c.arc(0, 0, rx, 0, Math.PI * 2);
  c.fill();
  c.restore();
}

/** One anatomically proportioned wet muddy palm print with distinct finger pads, knuckle prints & dragged rain streaks. */
function palm(
  c: CanvasRenderingContext2D,
  x: number,
  y: number,
  turn: number,
  scale: number,
  flip: 1 | -1,
  rand: () => number,
): void {
  c.save();
  c.translate(x, y);
  c.rotate(turn);
  c.scale(scale * flip, scale);
  // Anatomical palm pads: heel, thumb ball (thenar), outer edge (hypothenar), and upper knuckle ridge.
  smudge(c, -9, 18, 17, 22, -0.18, 0.46);
  smudge(c, 13, 14, 15, 24, 0.16, 0.44);
  smudge(c, 1, -4, 24, 13, 0.04, 0.42);
  // Hollow center of palm presses lighter
  c.globalCompositeOperation = "destination-out";
  c.fillStyle = "rgba(0,0,0,0.45)";
  c.beginPath();
  c.ellipse(1, 10, 9.5, 11.5, 0.12, 0, Math.PI * 2);
  c.fill();
  c.globalCompositeOperation = "source-over";

  // Five slender anatomical fingers: faint shaft + pronounced fingertip pad & mid-phalanx contact
  const fingers = [
    [-25, 4, -0.78, 28, 5.2], // thumb
    [-16, -18, -0.24, 42, 4.9], // index
    [-2, -22, -0.02, 48, 5.1], // middle
    [11, -19, 0.17, 44, 4.8], // ring
    [22, -10, 0.42, 34, 4.3], // pinky
  ] as const;
  for (const [fx, fy, angle, length, width] of fingers) {
    c.save();
    c.translate(fx, fy);
    c.rotate(angle);
    // Faint dragged wet smear along each finger
    smudge(c, 0, -length * 0.48, width * 1.15, length * 0.46, 0, 0.24);
    // Mid-joint contact
    smudge(c, 0, -length * 0.56, width * 1.05, width * 1.4, 0, 0.34);
    // Firmly pressed fingertip pad
    smudge(c, 0, -length + width * 0.9, width * 1.18, width * 1.65, 0, 0.54);
    // Subtle downward slip drag from each fingertip gripping wet glass
    const slip = 10 + rand() * 14;
    const dg = c.createLinearGradient(0, -length + width, 0, -length + width + slip);
    dg.addColorStop(0, "rgba(186,180,168,0.28)");
    dg.addColorStop(1, "rgba(186,180,168,0)");
    c.fillStyle = dg;
    c.fillRect(-width * 0.55, -length + width, width * 1.1, slip);
    c.restore();
  }

  // Organic skin-pore & raindrop breakup across the grease print
  c.globalCompositeOperation = "destination-out";
  for (let i = 0; i < 320; i++) {
    c.fillStyle = `rgba(0,0,0,${0.18 + rand() * 0.46})`;
    c.beginPath();
    c.arc(-32 + rand() * 64, -72 + rand() * 114, 0.8 + rand() * 2.2, 0, Math.PI * 2);
    c.fill();
  }
  c.globalCompositeOperation = "source-over";

  // Thin wet rain rivulets running down from the muddy heel of the palm
  for (let i = 0; i < 7; i++) {
    const sx = -20 + rand() * 40,
      len = 36 + rand() * 92;
    const g = c.createLinearGradient(0, 28, 0, 28 + len);
    g.addColorStop(0, "rgba(176,170,158,0.24)");
    g.addColorStop(1, "rgba(176,170,158,0)");
    c.fillStyle = g;
    c.fillRect(sx, 28, 1.0 + rand() * 2.1, len);
  }
  c.restore();
}

/**
 * What the haunt at Sora's window leaves behind in three escalating stages:
 * 1) Beat 4a slap (57.88 s): two wet muddy palm prints slam onto the pane immediately!
 * 2) Pitch-black lull (58.9..60.2 s): wet dragged fingernail streaks slide down the glass
 *    right as the fingernail-scrape sound plays in the dark!
 * 3) Beat 4b face press (60.56 s): a cold bloom of breath condenses inside the glass
 *    where her mouth pressed, lingering and evaporating slowly after she vanishes.
 */
export class TaxiGlassMarks {
  private readonly material: StandardMaterial;
  private readonly prints: DynamicTexture;
  private readonly scratches: StandardMaterial;
  private readonly breath: StandardMaterial;
  private readonly slapAt = taxiPassBeat(taxiPass("overtake"));

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
      palm(c, p.u * size, (1 - p.v) * size, p.turn + Math.PI, p.scale, p.flip, rand);
    this.prints.hasAlpha = true;
    this.prints.update();
    this.material = new StandardMaterial("M_taxi_window_handprints", scene);
    this.material.diffuseTexture = this.prints;
    this.material.useAlphaFromDiffuseTexture = true;
    this.material.diffuseColor = new Color3(0.74, 0.73, 0.7);
    this.material.specularColor = new Color3(0.24, 0.24, 0.25);
    this.material.backFaceCulling = false;
    this.material.alpha = 0;
    this.material.zOffset = -3;
    const marks = glass.clone("taxi_window_handprints", glass.parent);
    marks.material = this.material;
    marks.isPickable = false;
    // Just inside the glass the face was outside: the prints were pressed from the other side.
    const inward = -Math.sign(glass.getBoundingInfo().boundingBox.centerWorld.x);
    marks.setAbsolutePosition(glass.getAbsolutePosition().add(new Vector3(inward * 0.004, 0, 0)));

    // Wet fingernail drag streaks appearing during the pitch-black scrape (58.9..60.2 s)
    const scratchTex = new DynamicTexture(
      "taxi_window_nail_drags",
      { width: size, height: size },
      scene,
      true,
    );
    const sc = scratchTex.getContext() as unknown as CanvasRenderingContext2D;
    sc.clearRect(0, 0, size, size);
    for (const p of PALMS) {
      const px = p.u * size,
        py = (1 - p.v) * size;
      for (let fi = -2; fi <= 2; fi++) {
        const sx = px + fi * 13.5 * p.scale,
          sy = py - 24 * p.scale;
        const dragLen = (82 + rand() * 54) * p.scale;
        const g = sc.createLinearGradient(sx, sy, sx + fi * 2.5, sy + dragLen);
        g.addColorStop(0, "rgba(188,184,174,0.44)");
        g.addColorStop(0.55, "rgba(176,172,162,0.32)");
        g.addColorStop(1, "rgba(165,162,154,0)");
        sc.strokeStyle = g;
        sc.lineWidth = 2.6 + rand() * 1.4;
        sc.lineCap = "round";
        sc.beginPath();
        sc.moveTo(sx, sy);
        sc.quadraticCurveTo(
          sx + (rand() - 0.5) * 6,
          sy + dragLen * 0.5,
          sx + fi * 2.5,
          sy + dragLen,
        );
        sc.stroke();
      }
    }
    scratchTex.hasAlpha = true;
    scratchTex.update();
    this.scratches = new StandardMaterial("M_taxi_window_nail_drags", scene);
    this.scratches.diffuseTexture = scratchTex;
    this.scratches.useAlphaFromDiffuseTexture = true;
    this.scratches.diffuseColor = new Color3(0.76, 0.76, 0.74);
    this.scratches.specularColor = new Color3(0.28, 0.28, 0.3);
    this.scratches.backFaceCulling = false;
    this.scratches.alpha = 0;
    this.scratches.zOffset = -3.5;
    const scratchMesh = glass.clone("taxi_window_nail_drags", glass.parent);
    scratchMesh.material = this.scratches;
    scratchMesh.isPickable = false;
    scratchMesh.setAbsolutePosition(
      glass.getAbsolutePosition().add(new Vector3(inward * 0.005, 0, 0)),
    );

    const fog = new DynamicTexture("taxi_window_breath", { width: 256, height: 256 }, scene, true);
    const f = fog.getContext() as unknown as CanvasRenderingContext2D;
    f.clearRect(0, 0, 256, 256);
    const x = FACE.u * 256,
      y = (1 - FACE.v) * 256;
    for (const [dx, dy, rad, a] of [
      [0, 0, 28, 0.44],
      [-7, 4, 20, 0.22],
      [8, 3, 18, 0.2],
      [0, -9, 16, 0.16],
    ] as const) {
      const g = f.createRadialGradient(x + dx, y + dy, 0, x + dx, y + dy, rad);
      g.addColorStop(0, `rgba(198,205,212,${a})`);
      g.addColorStop(0.55, `rgba(194,202,210,${(a * 0.48).toFixed(3)})`);
      g.addColorStop(1, "rgba(194,202,210,0)");
      f.fillStyle = g;
      f.fillRect(0, 0, 256, 256);
    }
    fog.hasAlpha = true;
    fog.update();
    this.breath = new StandardMaterial("M_taxi_window_breath", scene);
    this.breath.diffuseTexture = fog;
    this.breath.useAlphaFromDiffuseTexture = true;
    this.breath.emissiveColor = new Color3(0.15, 0.16, 0.18);
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
    const sinceSlap = t - this.slapAt;
    const sinceFace = t - TAXI_WINDOW.beat;
    // Stage 1: Palm prints land IMMEDIATELY on Beat 4a's slap (57.88 s) and slowly wash in rain!
    this.material.alpha = sinceSlap < 0 ? 0 : Math.max(0.4, 0.88 - sinceSlap / 36);
    this.material.emissiveColor.set(0.34, 0.35, 0.37).scaleInPlace(0.24 + flash * 0.78);
    // Stage 2: Wet fingernail drag streaks materialize smoothly during the blackout scrape (58.9..60.2 s)!
    const scrapeGrow = Math.max(0, Math.min(1, (t - 58.9) / 1.1));
    this.scratches.alpha =
      scrapeGrow <= 0 ? 0 : scrapeGrow * Math.max(0.35, 0.82 - Math.max(0, sinceFace) / 34);
    this.scratches.emissiveColor.set(0.38, 0.4, 0.43).scaleInPlace(0.22 + flash * 0.82);
    // Stage 3: Cold breath condenses right as her face presses against the glass (60.56 s), then evaporates!
    this.breath.alpha =
      sinceFace < -0.35
        ? 0
        : sinceFace < 0.4
          ? (sinceFace + 0.35) / 0.75
          : Math.max(0, 1 - (sinceFace - 0.4) / 4.8);
  }
}
