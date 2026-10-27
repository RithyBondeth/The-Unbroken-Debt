import type { Scene } from "@babylonjs/core/scene";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { VertexData } from "@babylonjs/core/Meshes/mesh.vertexData";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { seededRandom } from "../../../audio/synth";

const WIDTH = 1024,
  HEIGHT = 512;
interface Drop {
  x: number;
  y: number;
  radius: number;
  speed: number;
}

/** A curved, raked windshield. The same wiper angle drives the blades and water removal. */
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
  constructor(scene: Scene) {
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
    for (let j = 0; j <= 8; j++)
      for (let i = 0; i <= 32; i++) {
        const u = i / 32,
          v = j / 8,
          x = (u * 2 - 1) * (0.82 - 0.13 * v);
        positions.push(x, 1.04 + 0.72 * v, 1.28 - 0.42 * v + 0.035 * (1 - (u * 2 - 1) ** 2));
        uvs.push(u, v);
        if (i < 32 && j < 8) {
          const a = j * 33 + i;
          indices.push(a, a + 33, a + 1, a + 1, a + 33, a + 34);
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
    const r = 0.9 + this.random() ** 2 * 3.1;
    return {
      x: this.random() * WIDTH,
      y: anywhere ? this.random() * HEIGHT : -15,
      radius: r,
      speed: r > 1.8 ? 45 + this.random() * 85 : 1 + this.random() * 4,
    };
  }
  update(dt: number, angle: number, flash: number): void {
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
    for (const x of [-0.43, 0.43]) {
      const cx = (x / 1.64 + 0.5) * WIDTH,
        cy = HEIGHT * 0.975;
      const end = (a: number) => [
        cx - ((Math.sin(a) * 0.65) / 1.64) * WIDTH,
        cy - ((Math.cos(a) * 0.65 * 0.889) / 0.72) * HEIGHT,
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
