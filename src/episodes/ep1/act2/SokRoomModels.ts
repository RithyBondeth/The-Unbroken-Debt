import type { Scene } from "@babylonjs/core/scene";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { VertexData } from "@babylonjs/core/Meshes/mesh.vertexData";
import { CreateBox } from "@babylonjs/core/Meshes/Builders/boxBuilder";
import { CreateCylinder } from "@babylonjs/core/Meshes/Builders/cylinderBuilder";
import { CreateDisc } from "@babylonjs/core/Meshes/Builders/discBuilder";
import { CreateTube } from "@babylonjs/core/Meshes/Builders/tubeBuilder";
import { CreateSphere } from "@babylonjs/core/Meshes/Builders/sphereBuilder";
import { CreatePlane } from "@babylonjs/core/Meshes/Builders/planeBuilder";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import type { Area } from "../../../core/AreaLoader";
import { seededRandom } from "../../../audio/synth";
import { GOVERNOR } from "../data/investigation";

/** Close-up props: hand-made period silhouettes and restrained, aged materials. Metres, Y up. */
export class SokRoomModels {
  readonly gramophone: TransformNode;
  readonly journal: TransformNode;
  readonly plank: TransformNode;
  readonly papers: TransformNode;
  readonly record: TransformNode;
  readonly governor: TransformNode;
  readonly tonearm: TransformNode;
  readonly meshes: Mesh[] = [];
  readonly gramophoneMeshes: Mesh[] = [];
  private readonly wood: PBRMaterial;
  private readonly edge: PBRMaterial;
  private readonly brass: PBRMaterial;
  private readonly dark: PBRMaterial;
  private readonly paper: PBRMaterial;
  private readonly ink: PBRMaterial;
  private open = 0;

  constructor(
    private readonly scene: Scene,
    area: Area,
  ) {
    this.wood = this.material("teak", "#ffffff", 0.65);
    this.edge = this.material("teak_edge", "#4c2b1b", 0.56);
    this.brass = this.material("brass", "#a68a51", 0.47, 0.78);
    this.dark = this.material("iron", "#181b19", 0.58, 0.55);
    this.paper = this.material("paper", "#d5c098", 0.96);
    this.ink = this.material("cord", "#68513a", 0.95);
    this.paintWood();
    const marker = area.level.interactables.find((m) => m.name === "interact_gramophone");
    if (!marker) throw new Error("[Sok room] missing gramophone anchor");
    for (const mesh of marker.node.getChildMeshes(false)) mesh.setEnabled(false);
    this.gramophone = new TransformNode("sok_gramophone", scene);
    this.gramophone.position.copyFrom(marker.position);
    this.gramophone.position.y -= 0.9;
    this.gramophone.rotation.y = 0.35;
    this.buildCabinet();
    this.record = new TransformNode("sok_record_spinning", scene);
    this.record.parent = this.gramophone;
    this.record.position.set(0, 0.818, 0.015);
    this.buildRecord();
    this.tonearm = new TransformNode("sok_tonearm", scene);
    this.tonearm.parent = this.gramophone;
    this.tonearm.position.set(0.158, 0.84, -0.12);
    this.tube(
      this.tonearm,
      "tonearm_tube",
      [
        [0, 0, 0],
        [0.008, 0.07, 0.025],
        [-0.02, 0.078, 0.09],
        [-0.07, 0.06, 0.16],
      ],
      0.008,
      this.brass,
    );
    const head = this.cylinder(
      this.tonearm,
      "soundbox",
      0.036,
      0.018,
      [-0.07, 0.05, 0.16],
      this.dark,
    );
    head.rotation.x = Math.PI / 2;
    this.tube(
      this.tonearm,
      "needle",
      [
        [-0.07, 0.035, 0.16],
        [-0.07, -0.015, 0.16],
      ],
      0.0015,
      this.brass,
    );
    this.buildHorn();
    this.governor = new TransformNode("sok_speed_pointer", scene);
    this.governor.parent = this.gramophone;
    this.governor.position.set(0, 0.705, 0.247);
    this.buildDial();
    this.gramophoneMeshes.push(...this.meshes);

    // A wall hiding place beside the desk, separate from the later chest's floor planks.
    this.journal = new TransformNode("interact_sok_wall_plank", scene);
    this.journal.position.set(
      marker.position.x - 0.47,
      marker.position.y + 0.25,
      marker.position.z - 1.12,
    );
    this.journal.rotation.y = Math.PI / 2;
    this.box(this.journal, "recess", [0.29, 0.62, 0.012], [0, 0, -0.025], this.dark);
    for (const x of [-0.153, 0.153])
      this.box(this.journal, "rebate", [0.018, 0.65, 0.035], [x, 0, -0.005], this.edge);
    for (const y of [-0.325, 0.325])
      this.box(this.journal, "rebate", [0.324, 0.018, 0.035], [0, y, -0.005], this.edge);
    this.papers = new TransformNode("interact_sok_journal", scene);
    this.papers.parent = this.journal;
    for (let k = 0; k < 7; k++) {
      const sheet = this.sheet(k);
      sheet.parent = this.papers;
      sheet.position.set(((k % 3) - 1) * 0.002, -0.05, -0.006 + k * 0.0012);
    }
    const script = this.paperScript();
    const face = CreatePlane("sok_journal_handwriting", { width: 0.214, height: 0.327 }, scene);
    face.parent = this.papers;
    face.position.set(0, -0.05, 0.008);
    face.rotation.y = Math.PI;
    face.material = script;
    this.meshes.push(face);
    this.tube(
      this.papers,
      "journal_tie",
      [
        [-0.112, -0.15, 0.015],
        [0, -0.16, 0.018],
        [0.112, -0.15, 0.015],
      ],
      0.002,
      this.ink,
    );
    this.plank = new TransformNode("sok_plank_moving", scene);
    this.plank.parent = this.journal;
    this.box(this.plank, "loose_wall_board", [0.296, 0.64, 0.024], [0, 0, 0.032], this.wood);
    for (const y of [-0.27, 0.27]) {
      const nail = CreateSphere("sok_plank_nail", { diameter: 0.009, segments: 8 }, scene);
      nail.parent = this.plank;
      nail.position.set(0.09, y, 0.046);
      nail.scaling.z = 0.25;
      nail.material = this.dark;
      this.meshes.push(nail);
    }
    // A small split and an exposed nail give the player an authored visual clue.
    this.box(this.plank, "plank_split", [0.0015, 0.19, 0.001], [-0.055, -0.16, 0.045], this.dark);
    area.container.meshes.push(...this.meshes);
    area.container.transformNodes.push(
      this.gramophone,
      this.record,
      this.tonearm,
      this.governor,
      this.journal,
      this.papers,
      this.plank,
    );
  }

  update(dt: number, rpm: number, playing: boolean, opened: boolean, instant = false): void {
    this.open += ((opened ? 1 : 0) - this.open) * (instant ? 1 : 1 - Math.exp(-dt * 7));
    this.plank.position.set(-this.open * 0.31, this.open * -0.025, this.open * 0.09);
    this.plank.rotation.y = -this.open * 0.3;
    if (playing) this.record.rotation.y -= (dt * rpm * Math.PI) / 30;
    this.governor.rotation.z = (-(rpm - 75) / 15) * 0.95;
    const target = playing ? 0 : -0.45;
    this.tonearm.rotation.y += (target - this.tonearm.rotation.y) * Math.min(1, dt * 4);
  }

  private material(name: string, hex: string, roughness: number, metallic = 0): PBRMaterial {
    const m = new PBRMaterial(`M_sok_${name}`, this.scene);
    m.albedoColor = Color3.FromHexString(hex);
    m.roughness = roughness;
    m.metallic = metallic;
    m.maxSimultaneousLights = 8;
    return m;
  }

  private box(
    root: TransformNode,
    name: string,
    size: number[],
    at: number[],
    material: PBRMaterial,
  ): Mesh {
    const m = CreateBox(
      `sok_${name}`,
      { width: size[0], height: size[1], depth: size[2] },
      this.scene,
    );
    m.parent = root;
    m.position.copyFromFloats(at[0], at[1], at[2]);
    m.material = material;
    this.meshes.push(m);
    return m;
  }

  private cylinder(
    root: TransformNode,
    name: string,
    diameter: number,
    height: number,
    at: number[],
    material: PBRMaterial,
  ): Mesh {
    const m = CreateCylinder(`sok_${name}`, { diameter, height, tessellation: 64 }, this.scene);
    m.parent = root;
    m.position.copyFromFloats(at[0], at[1], at[2]);
    m.material = material;
    this.meshes.push(m);
    return m;
  }

  private tube(
    root: TransformNode,
    name: string,
    path: number[][],
    radius: number,
    material: PBRMaterial,
  ): Mesh {
    const m = CreateTube(
      `sok_${name}`,
      { path: path.map((p) => new Vector3(...p)), radius, tessellation: 12, cap: Mesh.CAP_ALL },
      this.scene,
    );
    m.parent = root;
    m.material = material;
    this.meshes.push(m);
    return m;
  }

  private buildCabinet(): void {
    const root = this.gramophone;
    for (const x of [-0.24, 0.24])
      for (const z of [-0.24, 0.24]) {
        this.cylinder(root, "stand_foot", 0.065, 0.045, [x, 0.0225, z], this.edge);
        this.box(root, "stand_leg", [0.046, 0.58, 0.046], [x, 0.32, z], this.wood);
      }
    this.box(root, "stand_lower_shelf", [0.55, 0.025, 0.55], [0, 0.22, 0], this.wood);
    this.box(root, "stand_top", [0.61, 0.035, 0.61], [0, 0.61, 0], this.edge);
    this.box(root, "cabinet", [0.405, 0.148, 0.405], [0, 0.714, 0], this.wood);
    for (const [y, w, h] of [
      [0.64, 0.45, 0.025],
      [0.666, 0.426, 0.014],
      [0.79, 0.44, 0.025],
      [0.807, 0.461, 0.012],
    ])
      this.box(root, "cabinet_moulding", [w, h, w], [0, y, 0], this.edge);
    for (const x of [-0.192, 0.192])
      for (const z of [-0.192, 0.192])
        this.cylinder(root, "cabinet_corner", 0.022, 0.12, [x, 0.719, z], this.brass);
    this.box(root, "front_inset", [0.31, 0.087, 0.004], [0, 0.722, 0.205], this.edge);
    this.tube(
      root,
      "winding_crank",
      [
        [0.205, 0.722, -0.08],
        [0.3, 0.722, -0.08],
        [0.3, 0.665, -0.08],
        [0.35, 0.665, -0.08],
      ],
      0.006,
      this.brass,
    );
    const handle = this.cylinder(
      root,
      "crank_wood_grip",
      0.022,
      0.062,
      [0.365, 0.665, -0.08],
      this.edge,
    );
    handle.rotation.z = Math.PI / 2;
    this.cylinder(root, "tonearm_base", 0.047, 0.016, [0.158, 0.825, -0.12], this.brass);
  }

  private buildRecord(): void {
    this.cylinder(this.record, "turntable", 0.342, 0.013, [0, 0, 0], this.brass);
    this.cylinder(this.record, "shellac", 0.314, 0.004, [0, 0.008, 0], this.dark);
    const mat = this.material("record_grooves", "#ffffff", 0.35, 0.08);
    const texture = new DynamicTexture("T_sok_record", 1024, this.scene, true);
    const c = texture.getContext() as CanvasRenderingContext2D;
    c.fillStyle = "#161a18";
    c.fillRect(0, 0, 1024, 1024);
    for (let r = 155; r < 506; r += 3) {
      c.strokeStyle = r % 2 ? "#343a33" : "#202620";
      c.lineWidth = 0.7;
      c.beginPath();
      c.arc(512, 512, r, 0, Math.PI * 2);
      c.stroke();
    }
    c.fillStyle = "#6f342b";
    c.beginPath();
    c.arc(512, 512, 145, 0, Math.PI * 2);
    c.fill();
    c.strokeStyle = "#c8ac74";
    c.lineWidth = 3;
    c.beginPath();
    c.arc(512, 512, 135, 0, Math.PI * 2);
    c.stroke();
    c.fillStyle = "#dbc495";
    c.textAlign = "center";
    c.font = "32px serif";
    c.fillText("SOK", 512, 465);
    c.font = "17px serif";
    c.fillText("PRIVATE RECORD", 512, 499);
    c.fillText("1932", 512, 555);
    texture.update();
    mat.albedoTexture = texture;
    const face = CreateDisc(
      "sok_record_face",
      { radius: 0.157, tessellation: 96, sideOrientation: Mesh.DOUBLESIDE },
      this.scene,
    );
    face.rotation.x = Math.PI / 2;
    face.position.y = 0.0105;
    face.parent = this.record;
    face.material = mat;
    this.meshes.push(face);
    this.cylinder(this.record, "spindle", 0.007, 0.021, [0, 0.018, 0], this.brass);
  }

  private buildHorn(): void {
    const root = this.gramophone;
    this.tube(
      root,
      "horn_elbow",
      [
        [-0.145, 0.82, -0.13],
        [-0.145, 0.94, -0.16],
        [-0.145, 1.04, -0.14],
      ],
      0.023,
      this.brass,
    );
    const positions: number[] = [],
      indices: number[] = [],
      uvs: number[] = [];
    const rings = 28,
      sides = 96;
    for (let i = 0; i <= rings; i++) {
      const t = i / rings;
      for (let j = 0; j <= sides; j++) {
        const a = (j / sides) * Math.PI * 2;
        const r = (0.023 + 0.225 * t ** 2.2) * (1 + 0.026 * Math.cos(a * 12) * t);
        positions.push(
          -0.145 + Math.cos(a) * r,
          1.04 + 0.22 * t + Math.sin(a) * r * 0.88,
          -0.14 + 0.39 * t - Math.sin(a) * r * 0.48,
        );
        uvs.push(j / sides, t);
        if (i < rings && j < sides) {
          const k = i * (sides + 1) + j;
          indices.push(k, k + 1, k + sides + 1, k + 1, k + sides + 2, k + sides + 1);
        }
      }
    }
    const normals: number[] = [];
    VertexData.ComputeNormals(positions, indices, normals);
    const data = new VertexData();
    data.positions = positions;
    data.indices = indices;
    data.normals = normals;
    data.uvs = uvs;
    const horn = new Mesh("sok_fluted_horn", this.scene);
    data.applyToMesh(horn);
    const brass = this.brass.clone("M_sok_horn");
    brass.backFaceCulling = false;
    brass.twoSidedLighting = true;
    horn.material = brass;
    horn.parent = root;
    this.meshes.push(horn);
    const lip: number[][] = [];
    for (let j = 0; j <= sides; j++) {
      const a = (j / sides) * Math.PI * 2,
        r = 0.248 * (1 + 0.026 * Math.cos(a * 12));
      lip.push([
        -0.145 + Math.cos(a) * r,
        1.26 + Math.sin(a) * r * 0.88,
        0.25 - Math.sin(a) * r * 0.48,
      ]);
    }
    this.tube(root, "rolled_horn_lip", lip, 0.0045, this.brass);
    this.cylinder(root, "horn_support", 0.016, 0.24, [-0.145, 0.94, -0.14], this.dark);
  }

  private buildDial(): void {
    const mat = this.material("dial", "#ffffff", 0.58, 0.35);
    const tex = new DynamicTexture("T_sok_governor", 512, this.scene, true),
      c = tex.getContext() as CanvasRenderingContext2D;
    c.fillStyle = "#bba370";
    c.fillRect(0, 0, 512, 512);
    c.strokeStyle = "#3a3121";
    c.fillStyle = "#342c1e";
    c.textAlign = "center";
    for (let rpm = GOVERNOR.min; rpm <= GOVERNOR.max; rpm++) {
      const a = ((rpm - 75) / 15) * 0.95 - Math.PI / 2;
      const major = rpm % 5 === 0;
      c.lineWidth = major ? 3 : 1;
      c.beginPath();
      c.moveTo(256 + Math.cos(a) * 174, 265 + Math.sin(a) * 174);
      c.lineTo(256 + Math.cos(a) * (major ? 147 : 160), 265 + Math.sin(a) * (major ? 147 : 160));
      c.stroke();
      if (major) {
        c.font = "24px serif";
        c.fillText(String(rpm), 256 + Math.cos(a) * 126, 273 + Math.sin(a) * 126);
      }
    }
    c.font = "19px serif";
    c.fillText("GOVERNOR", 256, 348);
    c.font = "14px serif";
    c.fillText("SLOW   ·   FAST", 256, 380);
    tex.update();
    mat.albedoTexture = tex;
    const plate = CreatePlane("sok_governor_plate", { width: 0.144, height: 0.144 }, this.scene);
    plate.parent = this.gramophone;
    plate.rotation.y = Math.PI;
    plate.position.set(0, 0.705, 0.245);
    plate.material = mat;
    this.meshes.push(plate);
    this.box(this.governor, "governor_needle", [0.003, 0.049, 0.003], [0, 0.024, 0.002], this.dark);
    const knob = this.cylinder(
      this.governor,
      "governor_knob",
      0.022,
      0.012,
      [0, 0, 0.008],
      this.brass,
    );
    knob.rotation.x = Math.PI / 2;
  }

  private paintWood(): void {
    const tex = new DynamicTexture("T_sok_teak", 512, this.scene, true),
      c = tex.getContext() as CanvasRenderingContext2D,
      rand = seededRandom(723);
    c.fillStyle = "#533722";
    c.fillRect(0, 0, 512, 512);
    for (let k = 0; k < 1300; k++) {
      c.strokeStyle = `rgba(${rand() > 0.5 ? "160,113,64" : "24,18,12"},${0.03 + rand() * 0.12})`;
      const x = rand() * 512;
      c.lineWidth = 0.4 + rand() * 1.2;
      c.beginPath();
      c.moveTo(x, 0);
      c.bezierCurveTo(x + rand() * 14, 180, x - rand() * 14, 330, x, 512);
      c.stroke();
    }
    tex.update();
    this.wood.albedoTexture = tex;
  }

  private sheet(layer: number): Mesh {
    const p: number[] = [],
      ix: number[] = [],
      uv: number[] = [],
      normals: number[] = [];
    const nx = 12,
      ny = 16;
    for (let y = 0; y <= ny; y++)
      for (let x = 0; x <= nx; x++) {
        const u = x / nx,
          v = y / ny,
          edge = Math.abs(u - 0.5) * 2;
        p.push(
          (u - 0.5) * 0.22,
          (v - 0.5) * 0.34,
          0.002 * edge ** 3 * Math.sin(v * 9 + layer) + 0.001 * Math.sin(u * 6),
        );
        uv.push(u, 1 - v);
        if (x < nx && y < ny) {
          const k = y * (nx + 1) + x;
          ix.push(k, k + nx + 1, k + 1, k + 1, k + nx + 1, k + nx + 2);
        }
      }
    VertexData.ComputeNormals(p, ix, normals);
    const d = new VertexData();
    d.positions = p;
    d.indices = ix;
    d.uvs = uv;
    d.normals = normals;
    const sheet = new Mesh(`sok_journal_sheet_${layer}`, this.scene);
    d.applyToMesh(sheet);
    sheet.material = this.paper;
    this.meshes.push(sheet);
    return sheet;
  }

  private paperScript(): PBRMaterial {
    const mat = this.material("journal_ink", "#ffffff", 0.97);
    const tex = new DynamicTexture("T_sok_journal", { width: 768, height: 1152 }, this.scene, true),
      c = tex.getContext() as CanvasRenderingContext2D,
      rand = seededRandom(724);
    c.fillStyle = "#d7c39a";
    c.fillRect(0, 0, 768, 1152);
    for (let k = 0; k < 13000; k++) {
      c.fillStyle = `rgba(89,57,29,${rand() * 0.09})`;
      c.fillRect(rand() * 768, rand() * 1152, 1 + rand() * 3, 1);
    }
    c.fillStyle = "#4e402c";
    c.font = "32px 'Preah Vihear'";
    const lines = [
      "សៀវភៅកំណត់ហេតុ",
      "សុខ",
      "ឆ្នាំ ១៩១០",
      "ជីតា — ជា",
      "ឆ្នាំ ១៩២០ — កញ្ញា",
      "អ្នកតា",
      "ជីវិតបួន",
      "ត្រាប្រាំ",
    ];
    lines.forEach((line, k) => c.fillText(line, 65 + rand() * 8, 110 + k * 99));
    // Sok's own diagrams: four payments and five seals; the fourth name stays unknown.
    c.strokeStyle = "#625035";
    c.lineWidth = 2;
    for (let k = 0; k < 4; k++) {
      const x = 180 + k * 130;
      c.beginPath();
      c.arc(x, 974, 24, 0, Math.PI * 2);
      c.stroke();
      if (k < 3) {
        c.beginPath();
        c.moveTo(x - 17, 958);
        c.lineTo(x + 17, 990);
        c.stroke();
      }
    }
    for (let k = 0; k < 5; k++) {
      c.beginPath();
      c.arc(155 + k * 115, 1055, 14 + (k % 2) * 3, 0, Math.PI * 2);
      c.stroke();
    }
    c.strokeStyle = "#665132";
    c.lineWidth = 2;
    c.beginPath();
    c.moveTo(65, 900);
    c.bezierCurveTo(240, 940, 330, 890, 590, 935);
    c.stroke();
    tex.update();
    mat.albedoTexture = tex;
    return mat;
  }
}
