import type { Scene } from "@babylonjs/core/scene";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { VertexData } from "@babylonjs/core/Meshes/mesh.vertexData";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import type { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { seededRandom } from "@/audio/synth";

const WIDTH = 1024;
const SIDE_SIZE = 512;

/**
 * The windscreen's glass as the cabin marks it: its lower and upper corners (the glass
 * leans back from bottom to top), and the top-hung vacuum wipers' pivots and blade reach.
 */
export interface WindscreenFrame {
  min: Vector3;
  max: Vector3;
  wipers: Vector3[];
  blade: number;
}
interface Drop {
  x: number;
  y: number;
  radius: number;
  speed: number;
  phase: number;
}

/** The flat, upright 1930s windscreen. The same wiper angle drives the blades and water removal. */
export class TaxiRain {
  readonly glass: Mesh;
  readonly sideTexture: DynamicTexture;
  private readonly texture: DynamicTexture;
  private readonly material: PBRMaterial;
  private readonly mask: HTMLCanvasElement;
  private readonly mist: HTMLCanvasElement;
  private readonly sideMist: HTMLCanvasElement;
  private readonly random = seededRandom(5910);
  private readonly drops: Drop[] = [];
  private readonly sideDrops: Drop[] = [];
  private sinceDraw = 0;
  private previous = 0;
  /** Canvas height: square pixels on the glass. */
  private readonly height: number;
  constructor(
    scene: Scene,
    private readonly frame: WindscreenFrame,
  ) {
    const width = frame.max.x - frame.min.x,
      tall = frame.max.y - frame.min.y;
    this.height = Math.max(128, Math.round((WIDTH * tall) / width / 32) * 32);
    const HEIGHT = this.height;
    this.texture = new DynamicTexture(
      "taxi_windshield_water",
      { width: WIDTH, height: HEIGHT },
      scene,
      false,
    );
    this.texture.hasAlpha = true;
    this.sideTexture = new DynamicTexture(
      "taxi_side_window_runoff",
      { width: SIDE_SIZE, height: SIDE_SIZE },
      scene,
      false,
    );
    this.sideTexture.hasAlpha = true;
    this.mask = document.createElement("canvas");
    this.mask.width = WIDTH;
    this.mask.height = HEIGHT;
    const mask = this.mask.getContext("2d")!;
    mask.fillStyle = "white";
    mask.fillRect(0, 0, WIDTH, HEIGHT);
    this.mist = document.createElement("canvas");
    this.mist.width = WIDTH;
    this.mist.height = HEIGHT;
    const mist = this.mist.getContext("2d")!;
    for (let i = 0; i < 2400; i++) {
      const x = this.random() * WIDTH,
        y = this.random() * HEIGHT;
      mist.fillStyle = `rgba(165,184,198,${0.025 + this.random() * 0.065})`;
      mist.beginPath();
      mist.ellipse(x, y, 0.55 + this.random() * 0.9, 0.7 + this.random() * 1.1, 0, 0, Math.PI * 2);
      mist.fill();
    }
    this.sideMist = document.createElement("canvas");
    this.sideMist.width = SIDE_SIZE;
    this.sideMist.height = SIDE_SIZE;
    const sideMist = this.sideMist.getContext("2d")!;
    for (let i = 0; i < 1600; i++) {
      const x = this.random() * SIDE_SIZE,
        y = this.random() * SIDE_SIZE;
      sideMist.fillStyle = `rgba(150,172,188,${0.03 + this.random() * 0.075})`;
      sideMist.beginPath();
      sideMist.arc(x, y, 0.6 + this.random() * 1.1, 0, Math.PI * 2);
      sideMist.fill();
    }
    for (let i = 0; i < 820; i++) this.drops.push(this.drop(true));
    for (let i = 0; i < 420; i++) this.sideDrops.push(this.sideDrop(true));
    this.material = new PBRMaterial("M_taxi_wet_windshield", scene);
    this.material.albedoTexture = this.texture;
    this.material.emissiveTexture = this.texture;
    this.material.albedoColor = new Color3(0.74, 0.8, 0.86);
    this.material.emissiveColor.set(0.11, 0.13, 0.15);
    this.material.useAlphaFromAlbedoTexture = true;
    this.material.transparencyMode = PBRMaterial.PBRMATERIAL_ALPHABLEND;
    this.material.roughness = 0.08;
    this.material.backFaceCulling = false;
    this.material.metallic = 0;
    this.glass = new Mesh("taxi_curved_windshield", scene);
    const positions: number[] = [],
      uvs: number[] = [],
      indices: number[] = [],
      normals: number[] = [];
    // Flat glass, a hair inside the frame's rubber, leaning back from its foot to its head.
    for (let j = 0; j <= 4; j++)
      for (let i = 0; i <= 8; i++) {
        const u = i / 8,
          v = j / 4;
        positions.push(
          frame.min.x + (frame.max.x - frame.min.x) * u,
          frame.min.y + (frame.max.y - frame.min.y) * v,
          frame.min.z + (frame.max.z - frame.min.z) * v,
        );
        uvs.push(u, v);
        if (i < 8 && j < 4) {
          const a = j * 9 + i;
          indices.push(a, a + 9, a + 1, a + 1, a + 9, a + 10);
        }
      }
    VertexData.ComputeNormals(positions, indices, normals);
    const data = new VertexData();
    data.positions = positions;
    data.normals = normals;
    data.uvs = uvs;
    data.indices = indices;
    data.applyToMesh(this.glass);
    this.glass.material = this.material;
    this.glass.isPickable = false;
    this.paint(0, 1);
  }
  private drop(anywhere = false): Drop {
    const HEIGHT = this.height;
    const r = 0.85 + this.random() ** 2.1 * 2.75;
    return {
      x: this.random() * WIDTH,
      y: anywhere ? this.random() * HEIGHT : -12,
      radius: r,
      speed: r > 1.75 ? 48 + this.random() * 88 : 1.2 + this.random() * 3.8,
      phase: this.random() * Math.PI * 2,
    };
  }
  private sideDrop(anywhere = false): Drop {
    const r = 0.9 + this.random() ** 2.0 * 2.5;
    return {
      x: anywhere ? this.random() * SIDE_SIZE : this.random() * (SIDE_SIZE * 0.72),
      y: anywhere ? this.random() * SIDE_SIZE : -10 + this.random() * (SIDE_SIZE * 0.45),
      radius: r,
      speed: r > 1.7 ? 38 + this.random() * 68 : 1.5 + this.random() * 4.2,
      phase: this.random() * Math.PI * 2,
    };
  }
  update(dt: number, angle: number, flash: number, power = 1): void {
    const HEIGHT = this.height,
      { min, max, wipers, blade } = this.frame,
      width = max.x - min.x,
      tall = max.y - min.y;
    for (const d of this.drops) {
      d.y += d.speed * dt;
      d.x += (d.speed * 0.065 + Math.sin(d.y * 0.028 + d.phase) * 2.4) * dt;
      if (d.y > HEIGHT + 16) Object.assign(d, this.drop());
    }
    // Side-window droplets stream diagonally back in the car's slipstream while gravity pulls down.
    for (const d of this.sideDrops) {
      d.y += d.speed * 0.72 * dt;
      d.x += (d.speed * 0.92 + Math.sin(d.y * 0.03 + d.phase) * 3) * dt;
      if (d.y > SIDE_SIZE + 14 || d.x > SIDE_SIZE + 14) Object.assign(d, this.sideDrop());
    }
    const mask = this.mask.getContext("2d")!;
    mask.globalCompositeOperation = "source-over";
    mask.fillStyle = `rgba(255,255,255,${Math.min(1, dt * 1.55)})`;
    mask.fillRect(0, 0, WIDTH, HEIGHT);
    mask.globalCompositeOperation = "destination-out";
    mask.fillStyle = "black";
    // Each blade hangs from its pivot at the head of the glass and sweeps the arc below it.
    for (const pivot of wipers) {
      const cx = ((pivot.x - min.x) / width) * WIDTH,
        cy = (1 - (pivot.y - min.y) / tall) * HEIGHT;
      const end = (a: number) => [
        cx + ((Math.sin(a) * blade) / width) * WIDTH,
        cy + ((Math.cos(a) * blade) / tall) * HEIGHT,
      ];
      const a = end(this.previous),
        b = end(angle);
      mask.beginPath();
      mask.moveTo(cx, cy);
      mask.lineTo(a[0], a[1]);
      mask.lineTo(b[0], b[1]);
      mask.closePath();
      mask.fill();
      mask.lineWidth = 8;
      mask.beginPath();
      mask.moveTo(cx, cy);
      mask.lineTo(b[0], b[1]);
      mask.stroke();
    }
    mask.globalCompositeOperation = "source-over";
    this.previous = angle;
    this.material.emissiveColor.set(
      0.06 + power * 0.06 + flash * 0.22,
      0.07 + power * 0.055 + flash * 0.26,
      0.09 + power * 0.04 + flash * 0.34,
    );
    this.sinceDraw += dt;
    if (this.sinceDraw >= 1 / 24) {
      this.sinceDraw = 0;
      this.paint(flash, power);
    }
  }
  private paint(flash: number, power: number): void {
    const HEIGHT = this.height;
    const c = this.texture.getContext() as CanvasRenderingContext2D;
    c.clearRect(0, 0, WIDTH, HEIGHT);
    c.drawImage(this.mist, 0, 0);
    // Warm amber headlamp refraction blended with cold silver-blue lightning flash on each bead.
    const rHi = Math.round(212 + power * 36 - flash * 16);
    const gHi = Math.round(214 + power * 14 + flash * 20);
    const bHi = Math.round(205 - power * 38 + flash * 48);
    const rimAlpha = 0.28 + power * 0.24 + flash * 0.36;
    const trailAlpha = 0.1 + power * 0.08 + flash * 0.16;
    for (const d of this.drops) {
      if (d.speed > 20) {
        c.strokeStyle = `rgba(${rHi},${gHi},${bHi},${trailAlpha.toFixed(3)})`;
        c.lineWidth = Math.max(0.7, d.radius * 0.45);
        c.lineCap = "round";
        c.beginPath();
        c.moveTo(d.x - 1.2, d.y - d.radius * 9.5);
        c.lineTo(d.x, d.y);
        c.stroke();
      }
      // Subtle translucent dark refraction core (never opaque dark ink blots)
      c.fillStyle = "rgba(8,14,20,0.12)";
      c.beginPath();
      c.ellipse(d.x, d.y, d.radius, d.radius * 1.45, -0.08, 0, Math.PI * 2);
      c.fill();
      // Lower warm/silver refractive lens crescent
      c.strokeStyle = `rgba(${rHi},${gHi},${bHi},${rimAlpha.toFixed(3)})`;
      c.lineWidth = Math.max(0.6, d.radius * 0.35);
      c.beginPath();
      c.ellipse(
        d.x + 0.15,
        d.y + 0.35,
        d.radius * 0.78,
        d.radius * 1.15,
        -0.08,
        Math.PI * 0.12,
        Math.PI * 0.88,
      );
      c.stroke();
      // Sharp pinprick upper specular catchlight on larger beads
      if (d.radius > 1.55) {
        c.fillStyle = `rgba(${rHi},${gHi},${bHi},${Math.min(0.85, rimAlpha * 1.15).toFixed(3)})`;
        c.beginPath();
        c.arc(d.x - d.radius * 0.25, d.y - d.radius * 0.45, d.radius * 0.26, 0, Math.PI * 2);
        c.fill();
      }
    }
    c.globalCompositeOperation = "destination-in";
    c.drawImage(this.mask, 0, 0);
    c.globalCompositeOperation = "source-over";
    this.texture.update();

    // Dedicated 1:1 aspect-ratio diagonal wind-blown rain on the side windows (zero stretching!).
    const side = this.sideTexture.getContext() as CanvasRenderingContext2D;
    side.clearRect(0, 0, SIDE_SIZE, SIDE_SIZE);
    side.drawImage(this.sideMist, 0, 0);
    const sRim = 0.22 + power * 0.12 + flash * 0.42;
    const sTrail = 0.08 + power * 0.05 + flash * 0.18;
    for (const d of this.sideDrops) {
      if (d.speed > 18) {
        side.strokeStyle = `rgba(182,202,218,${sTrail.toFixed(3)})`;
        side.lineWidth = Math.max(0.65, d.radius * 0.42);
        side.lineCap = "round";
        side.beginPath();
        side.moveTo(d.x - d.radius * 7.8, d.y - d.radius * 6.2);
        side.lineTo(d.x, d.y);
        side.stroke();
      }
      side.fillStyle = "rgba(8,14,20,0.14)";
      side.beginPath();
      side.ellipse(d.x, d.y, d.radius * 1.1, d.radius * 1.45, -0.68, 0, Math.PI * 2);
      side.fill();
      side.strokeStyle = `rgba(196,214,228,${sRim.toFixed(3)})`;
      side.lineWidth = 0.7;
      side.beginPath();
      side.ellipse(
        d.x,
        d.y + 0.25,
        d.radius * 0.85,
        d.radius * 1.15,
        -0.68,
        Math.PI * 0.15,
        Math.PI * 0.9,
      );
      side.stroke();
    }
    this.sideTexture.update();
  }
}
