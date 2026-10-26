import type { Scene } from "@babylonjs/core/scene";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { VertexData } from "@babylonjs/core/Meshes/mesh.vertexData";
import { CreateLathe } from "@babylonjs/core/Meshes/Builders/latheBuilder";
import { CreateCylinder } from "@babylonjs/core/Meshes/Builders/cylinderBuilder";
import { CreateSphere } from "@babylonjs/core/Meshes/Builders/sphereBuilder";
import { CreateDisc } from "@babylonjs/core/Meshes/Builders/discBuilder";
import { CreateTube } from "@babylonjs/core/Meshes/Builders/tubeBuilder";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import type { Area } from "../../../core/AreaLoader";
import { seededRandom } from "../../../audio/synth";
import { OFFERINGS, type Offering } from "../data/betel";

type Prop = Offering | "betel_tray";

/** Canonical, life-size offering props. Pickups and the arranged tray use the same geometry. */
export class OfferingModels {
  readonly pickupIds = new Set<string>();
  private readonly wood: PBRMaterial;
  private readonly rim: PBRMaterial;
  private readonly leaves: PBRMaterial;
  private readonly husk: PBRMaterial;
  private readonly cut: PBRMaterial;
  private readonly brass: PBRMaterial;
  private readonly lime: PBRMaterial;
  private readonly wax: PBRMaterial;
  private readonly wick: PBRMaterial;
  private readonly incense: PBRMaterial;
  private readonly stem: PBRMaterial;
  private serial = 0;

  constructor(private readonly scene: Scene) {
    this.wood = this.material("lacquer", "#48281c", 0.48);
    this.rim = this.material("worn_lacquer_edge", "#765037", 0.62);
    this.leaves = this.material("betel_leaf", "#ffffff", 0.62);
    this.leaves.backFaceCulling = false;
    this.leaves.twoSidedLighting = true;
    this.husk = this.material("areca_husk", "#956039", 0.88);
    this.cut = this.material("areca_cut", "#ffffff", 0.9);
    this.brass = this.material("lime_brass", "#8e7443", 0.52, 0.82);
    this.lime = this.material("lime_paste", "#ded5bd", 0.98);
    this.wax = this.material("candle_wax", "#d4bb83", 0.82);
    this.wick = this.material("unlit_wick", "#282019", 1);
    this.incense = this.material("incense_powder", "#6a4b30", 1);
    this.stem = this.material("incense_stem", "#6e2a21", 0.9);
    this.paintSurfaces();
    this.paintLeaf();
    this.paintCut();
  }

  /** Replace only the placeholder render children; keep Blender's interaction anchors and flags. */
  replacePickups(area: Area): void {
    const offsets: Record<Prop, number> = {
      betel_tray: -0.05,
      betel: -0.05,
      areca: -0.05,
      lime: -0.06,
      candle: -0.02,
      // The horizontal sticks' lowest surface is 0.2 mm above their root.
      incense: -0.0202,
    };
    for (const marker of area.level.interactables) {
      const prop = marker.extras.item as Prop | undefined;
      if (!prop || !(prop === "betel_tray" || OFFERINGS.includes(prop))) continue;
      this.pickupIds.add(marker.name);
      for (const mesh of marker.node.getChildMeshes(false)) mesh.setEnabled(false);
      const model = this.make(prop);
      model.parent = marker.node;
      model.position.y = offsets[prop];
      area.container.meshes.push(...model.getChildMeshes<Mesh>());
      area.container.transformNodes.push(model);
    }
  }

  make(prop: Prop): TransformNode {
    const root = new TransformNode(`offering_${prop}_${this.serial++}`, this.scene);
    if (prop === "betel_tray") this.tray(root);
    if (prop === "betel") this.betel(root);
    if (prop === "areca") this.areca(root);
    if (prop === "lime") this.limePot(root);
    if (prop === "candle") this.candle(root);
    if (prop === "incense") this.sticks(root);
    return root;
  }

  private material(name: string, hex: string, roughness: number, metallic = 0): PBRMaterial {
    const material = new PBRMaterial(`M_offering_${name}`, this.scene);
    material.albedoColor = Color3.FromHexString(hex);
    material.roughness = roughness;
    material.metallic = metallic;
    material.maxSimultaneousLights = 8;
    return material;
  }

  private lathe(
    root: TransformNode,
    name: string,
    profile: [number, number][],
    material: PBRMaterial,
    segments = 64,
  ): Mesh {
    const mesh = CreateLathe(
      `${root.name}_${name}`,
      {
        shape: profile.map(([r, y]) => new Vector3(r, y, 0)),
        tessellation: segments,
        closed: true,
      },
      this.scene,
    );
    mesh.material = material;
    mesh.parent = root;
    return mesh;
  }

  private tray(root: TransformNode): void {
    this.lathe(
      root,
      "turned_tray",
      [
        [0, 0],
        [0.13, 0],
        [0.145, 0.004],
        [0.15, 0.008],
        [0.18, 0.012],
        [0.197, 0.024],
        [0.201, 0.03],
        [0.201, 0.034],
        [0.197, 0.036],
        [0.192, 0.033],
        [0.183, 0.026],
        [0.15, 0.019],
        [0, 0.018],
      ],
      this.wood,
      96,
    );
    // The rounded rim and concentric turning marks catch grazing lamplight.
    for (const [r, y] of [
      [0.198, 0.0348],
      [0.184, 0.0258],
      [0.148, 0.0192],
    ])
      this.lathe(
        root,
        "rim",
        [
          [r - 0.0007, y],
          [r, y + 0.0005],
          [r + 0.0006, y],
        ],
        this.rim,
        96,
      );
  }

  private betel(root: TransformNode): void {
    for (let k = 0; k < 3; k++) {
      const mesh = new Mesh(`${root.name}_leaf_${k}`, this.scene);
      const positions: number[] = [],
        indices: number[] = [],
        uvs: number[] = [];
      const rows = 20,
        columns = 12;
      for (let row = 0; row <= rows; row++)
        for (let col = 0; col <= columns; col++) {
          const t = row / rows,
            s = (col / columns) * 2 - 1;
          const half = 0.036 * Math.sin(Math.PI * t) ** 0.65 * (1 - 0.64 * t);
          positions.push(
            s * half,
            0.0015 + 0.002 * (1 - Math.abs(s)) + 0.0025 * s * s * Math.sin(Math.PI * t),
            (t - 0.45) * 0.088,
          );
          uvs.push(col / columns, t);
          if (row < rows && col < columns) {
            const a = row * (columns + 1) + col,
              b = a + columns + 1;
            indices.push(a, a + 1, b, a + 1, b + 1, b);
          }
        }
      const data = new VertexData();
      data.positions = positions;
      data.indices = indices;
      data.uvs = uvs;
      data.normals = [];
      VertexData.ComputeNormals(positions, indices, data.normals);
      data.applyToMesh(mesh);
      mesh.material = this.leaves;
      mesh.parent = root;
      mesh.rotation.y = (k - 1) * 0.32;
      mesh.position.set((k - 1) * 0.006, k * 0.0013, (k - 1) * 0.002);
      const stem = CreateTube(
        `${root.name}_leaf_stem_${k}`,
        {
          path: [new Vector3(0, 0.002, -0.039), new Vector3(0.002, 0.001, -0.049)],
          radius: 0.0007,
          tessellation: 6,
        },
        this.scene,
      );
      stem.parent = mesh;
      stem.material = this.leaves;
    }
  }

  private areca(root: TransformNode): void {
    for (let k = 0; k < 2; k++) {
      const nut = CreateSphere(
        `${root.name}_whole_${k}`,
        { diameter: 0.028, segments: 16 },
        this.scene,
      );
      nut.scaling.set(0.9, 1.15, 0.87);
      nut.position.set(-0.013 + k * 0.026, 0.016, 0.009);
      nut.material = this.husk;
      nut.parent = root;
    }
    for (let k = 0; k < 3; k++) {
      const slice = this.lathe(
        root,
        `slice_${k}`,
        [
          [0, 0],
          [0.012, 0],
          [0.014, 0.0015],
          [0.013, 0.004],
          [0, 0.004],
        ],
        this.husk,
        40,
      );
      slice.position.set(-0.017 + k * 0.017, k * 0.002, -0.015);
      slice.rotation.z = (k - 1) * 0.12;
      const face = CreateDisc(
        `${root.name}_marbled_cut_${k}`,
        { radius: 0.0125, tessellation: 40 },
        this.scene,
      );
      face.rotation.x = Math.PI / 2;
      face.position.y = 0.0042;
      face.parent = slice;
      face.material = this.cut;
    }
  }

  private limePot(root: TransformNode): void {
    this.lathe(
      root,
      "brass_pot",
      [
        [0, 0],
        [0.015, 0],
        [0.022, 0.004],
        [0.025, 0.014],
        [0.024, 0.027],
        [0.022, 0.035],
        [0.019, 0.036],
        [0.0175, 0.032],
        [0.018, 0.01],
        [0, 0.006],
      ],
      this.brass,
    );
    this.lathe(
      root,
      "chalky_lime",
      [
        [0, 0.028],
        [0.017, 0.029],
        [0.018, 0.032],
        [0.016, 0.0305],
        [0.01, 0.0318],
        [0, 0.031],
      ],
      this.lime,
      48,
    );
    const lid = this.lathe(
      root,
      "lid",
      [
        [0, 0],
        [0.019, 0],
        [0.022, 0.001],
        [0.022, 0.003],
        [0.018, 0.005],
        [0.005, 0.007],
        [0.004, 0.01],
        [0, 0.011],
      ],
      this.brass,
    );
    lid.position.set(0.027, 0.012, 0.004);
    lid.rotation.z = -0.9;
  }

  private candle(root: TransformNode): void {
    this.lathe(
      root,
      "saucer",
      [
        [0, 0],
        [0.018, 0],
        [0.022, 0.003],
        [0.023, 0.006],
        [0.021, 0.007],
        [0.016, 0.0035],
        [0, 0.003],
      ],
      this.brass,
    );
    this.lathe(
      root,
      "wax",
      [
        [0, 0.003],
        [0.009, 0.003],
        [0.0088, 0.02],
        [0.0084, 0.048],
        [0.008, 0.071],
        [0.006, 0.072],
        [0.003, 0.069],
        [0, 0.069],
      ],
      this.wax,
      40,
    );
    for (let k = 0; k < 4; k++) {
      const a = k * 1.7;
      const drip = CreateTube(
        `${root.name}_wax_drip_${k}`,
        {
          path: [
            new Vector3(Math.cos(a) * 0.0077, 0.069, Math.sin(a) * 0.0077),
            new Vector3(Math.cos(a) * 0.009, 0.059, Math.sin(a) * 0.009),
            new Vector3(Math.cos(a) * 0.0088, 0.04 + k * 0.005, Math.sin(a) * 0.0088),
          ],
          radius: 0.0011,
          tessellation: 6,
          cap: Mesh.CAP_ALL,
        },
        this.scene,
      );
      drip.parent = root;
      drip.material = this.wax;
    }
    const wick = CreateTube(
      `${root.name}_wick`,
      {
        path: [new Vector3(0, 0.069, 0), new Vector3(0.001, 0.076, 0.001)],
        radius: 0.00065,
        tessellation: 6,
      },
      this.scene,
    );
    wick.material = this.wick;
    wick.parent = root;
  }

  private sticks(root: TransformNode): void {
    for (let k = -1; k <= 1; k++) {
      const stick = CreateCylinder(
        `${root.name}_stick_${k}`,
        { height: 0.105, diameter: 0.0024, tessellation: 10 },
        this.scene,
      );
      stick.rotation.z = Math.PI / 2;
      stick.position.set(0.004 * k, 0.0014, k * 0.005);
      stick.material = this.incense;
      stick.parent = root;
      const red = CreateCylinder(
        `${root.name}_red_stem_${k}`,
        { height: 0.025, diameter: 0.0017, tessellation: 8 },
        this.scene,
      );
      red.rotation.z = Math.PI / 2;
      red.position.set(-0.059 + k * 0.004, 0.0014, k * 0.005);
      red.material = this.stem;
      red.parent = root;
    }
  }

  private paintSurfaces(): void {
    const texture = new DynamicTexture(
      "T_offering_turned_wood",
      { width: 512, height: 256 },
      this.scene,
      true,
    );
    const ctx = texture.getContext() as unknown as CanvasRenderingContext2D;
    const pixels = ctx.createImageData(512, 256);
    const rand = seededRandom(411);
    for (let y = 0; y < 256; y++)
      for (let x = 0; x < 512; x++) {
        const grain = Math.sin(y * 0.52 + Math.sin(x * 0.025) * 0.5) * 8 + (rand() - 0.5) * 11;
        const i = (y * 512 + x) * 4;
        pixels.data[i] = 195 + grain;
        pixels.data[i + 1] = 181 + grain;
        pixels.data[i + 2] = 163 + grain;
        pixels.data[i + 3] = 255;
      }
    ctx.putImageData(pixels, 0, 0);
    for (let k = 0; k < 60; k++) {
      const x = rand() * 512,
        y = rand() * 256;
      ctx.strokeStyle = "rgba(239,219,181,0.13)";
      ctx.beginPath();
      ctx.moveTo(x, y);
      ctx.lineTo(x + 2 + rand() * 18, y + rand() * 2);
      ctx.stroke();
    }
    texture.update();
    this.wood.albedoTexture = texture;
    const patina = new DynamicTexture("T_offering_brass_patina", 256, this.scene, true);
    const p = patina.getContext() as unknown as CanvasRenderingContext2D;
    p.fillStyle = "#ded5bd";
    p.fillRect(0, 0, 256, 256);
    for (let k = 0; k < 100; k++) {
      const x = rand() * 256,
        y = rand() * 256,
        r = 2 + rand() * 15;
      const spot = p.createRadialGradient(x, y, 0, x, y, r);
      spot.addColorStop(0, "rgba(55,68,49,0.22)");
      spot.addColorStop(1, "rgba(55,68,49,0)");
      p.fillStyle = spot;
      p.fillRect(x - r, y - r, r * 2, r * 2);
    }
    patina.update();
    this.brass.albedoTexture = patina;
  }

  private paintLeaf(): void {
    const texture = new DynamicTexture(
      "T_offering_leaf_veins",
      { width: 256, height: 512 },
      this.scene,
      true,
    );
    const ctx = texture.getContext() as unknown as CanvasRenderingContext2D;
    const gradient = ctx.createLinearGradient(0, 0, 256, 0);
    gradient.addColorStop(0, "#263d22");
    gradient.addColorStop(0.48, "#53633a");
    gradient.addColorStop(1, "#2b4022");
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, 256, 512);
    const rand = seededRandom(409);
    const image = ctx.getImageData(0, 0, 256, 512);
    for (let i = 0; i < image.data.length; i += 4) {
      const n = (rand() - 0.5) * 10;
      image.data[i] += n;
      image.data[i + 1] += n;
      image.data[i + 2] += n;
    }
    ctx.putImageData(image, 0, 0);
    ctx.strokeStyle = "rgba(159,161,92,0.5)";
    ctx.lineWidth = 1.4;
    ctx.beginPath();
    ctx.moveTo(128, 0);
    ctx.lineTo(128, 512);
    ctx.stroke();
    for (let y = 48; y < 480; y += 48)
      for (const side of [-1, 1]) {
        ctx.lineWidth = 0.8;
        ctx.beginPath();
        ctx.moveTo(128, y);
        ctx.quadraticCurveTo(128 + side * 50, y + 13, 128 + side * 122, y + 95);
        ctx.stroke();
      }
    texture.update();
    this.leaves.albedoTexture = texture;
  }

  private paintCut(): void {
    const texture = new DynamicTexture("T_offering_areca_cut", 256, this.scene, true);
    const ctx = texture.getContext() as unknown as CanvasRenderingContext2D;
    ctx.fillStyle = "#c4a376";
    ctx.fillRect(0, 0, 256, 256);
    const rand = seededRandom(410);
    for (let k = 0; k < 190; k++) {
      const angle = rand() * Math.PI * 2,
        r = rand() * 124;
      const x = 128 + Math.cos(angle) * r,
        y = 128 + Math.sin(angle) * r;
      ctx.strokeStyle = rand() > 0.5 ? "rgba(79,42,22,0.65)" : "rgba(239,221,182,0.7)";
      ctx.lineWidth = 1 + rand() * 3;
      ctx.beginPath();
      ctx.moveTo(x, y);
      ctx.quadraticCurveTo(x + (rand() - 0.5) * 24, y + 12, x + (rand() - 0.5) * 17, y + 26);
      ctx.stroke();
    }
    texture.update();
    this.cut.albedoTexture = texture;
  }
}
