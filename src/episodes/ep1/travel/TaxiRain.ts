import type { Scene } from "@babylonjs/core/scene";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { VertexData } from "@babylonjs/core/Meshes/mesh.vertexData";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import type { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { seededRandom } from "@/audio/synth";

const WIDTH = 1024;

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
}

/** The flat, upright 1930s windscreen. The same wiper angle drives the blades and water removal. */
export class TaxiRain {
  readonly glass: Mesh;
  readonly sideTexture: DynamicTexture;
  private readonly texture: DynamicTexture;
  private readonly material: PBRMaterial;
  private readonly mask: HTMLCanvasElement;
  private readonly mist: HTMLCanvasElement;
  private readonly random = seededRandom(5910);
  private readonly drops: Drop[] = [];
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
      { width: 512, height: 512 },
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
    for (let i = 0; i < 2600; i++) {
      const x = this.random() * WIDTH,
        y = this.random() * HEIGHT;
      mist.fillStyle = `rgba(165,185,199,${0.05 + this.random() * 0.13})`;
      mist.beginPath();
      mist.ellipse(x, y, 0.5 + this.random(), 0.8 + this.random() * 1.5, 0, 0, Math.PI * 2);
      mist.fill();
    }
    for (let i = 0; i < 700; i++) this.drops.push(this.drop(true));
    this.material = new PBRMaterial("M_taxi_wet_windshield", scene);
    this.material.albedoTexture = this.texture;
    this.material.emissiveTexture = this.texture;
    this.material.albedoColor = new Color3(0.65, 0.73, 0.8);
    this.material.emissiveColor.set(0.1, 0.12, 0.15);
    this.material.useAlphaFromAlbedoTexture = true;
    this.material.transparencyMode = PBRMaterial.PBRMATERIAL_ALPHABLEND;
    this.material.roughness = 0.12;
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
    this.paint(0);
  }
  private drop(anywhere = false): Drop {
    const HEIGHT = this.height;
    const r = 0.9 + this.random() ** 2 * 3.1;
    return {
      x: this.random() * WIDTH,
      y: anywhere ? this.random() * HEIGHT : -15,
      radius: r,
      speed: r > 1.8 ? 45 + this.random() * 85 : 1 + this.random() * 4,
    };
  }
  update(dt: number, angle: number, flash: number): void {
    const HEIGHT = this.height,
      { min, max, wipers, blade } = this.frame,
      width = max.x - min.x,
      tall = max.y - min.y;
    for (const d of this.drops) {
      d.y += d.speed * dt;
      d.x += (d.speed * 0.075 + Math.sin(d.y * 0.024) * 2) * dt;
      if (d.y > HEIGHT + 20) Object.assign(d, this.drop());
    }
    const mask = this.mask.getContext("2d")!;
    mask.globalCompositeOperation = "source-over";
    mask.fillStyle = `rgba(255,255,255,${Math.min(1, dt * 1.2)})`;
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
    this.material.emissiveColor.set(0.1 + flash * 0.25, 0.12 + flash * 0.3, 0.15 + flash * 0.36);
    this.sinceDraw += dt;
    if (this.sinceDraw >= 1 / 24) {
      this.sinceDraw = 0;
      this.paint(flash);
    }
  }
  private paint(flash: number): void {
    const HEIGHT = this.height;
    const c = this.texture.getContext() as CanvasRenderingContext2D;
    c.clearRect(0, 0, WIDTH, HEIGHT);
    c.drawImage(this.mist, 0, 0);
    for (const d of this.drops) {
      if (d.speed > 20) {
        c.strokeStyle = `rgba(130,155,177,${0.22 + flash * 0.18})`;
        c.lineWidth = d.radius * 0.8;
        c.lineCap = "round";
        c.beginPath();
        c.moveTo(d.x - 1.6, d.y - d.radius * 8);
        c.lineTo(d.x, d.y);
        c.stroke();
      }
      c.fillStyle = "rgba(14,25,33,.27)";
      c.beginPath();
      c.ellipse(d.x, d.y, d.radius, d.radius * 1.6, -0.12, 0, Math.PI * 2);
      c.fill();
      c.strokeStyle = `rgba(203,218,229,${0.42 + flash * 0.34})`;
      c.lineWidth = 0.65;
      c.beginPath();
      c.ellipse(
        d.x - 0.3,
        d.y - 0.6,
        d.radius * 0.8,
        d.radius * 1.4,
        -0.12,
        Math.PI * 0.95,
        Math.PI * 1.95,
      );
      c.stroke();
    }
    // Side windows retain runoff: wipers only clear the windshield.
    const side = this.sideTexture.getContext() as CanvasRenderingContext2D;
    side.clearRect(0, 0, 512, 512);
    side.drawImage(c.canvas, 0, 0, WIDTH, HEIGHT, 0, 0, 512, 512);
    this.sideTexture.update();
    c.globalCompositeOperation = "destination-in";
    c.drawImage(this.mask, 0, 0);
    c.globalCompositeOperation = "source-over";
    this.texture.update();
  }
}
