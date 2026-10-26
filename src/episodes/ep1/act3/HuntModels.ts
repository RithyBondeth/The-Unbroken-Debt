import type { Scene } from "@babylonjs/core/scene";
import type { Camera } from "@babylonjs/core/Cameras/camera";
import type { Area } from "../../../core/AreaLoader";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { CreateBox } from "@babylonjs/core/Meshes/Builders/boxBuilder";
import { CreateCylinder } from "@babylonjs/core/Meshes/Builders/cylinderBuilder";
import { CreateTorus } from "@babylonjs/core/Meshes/Builders/torusBuilder";
import { CreateLathe } from "@babylonjs/core/Meshes/Builders/latheBuilder";
import { CreateTube } from "@babylonjs/core/Meshes/Builders/tubeBuilder";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import { PointLight } from "@babylonjs/core/Lights/pointLight";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { seededRandom } from "../../../audio/synth";
import { JARS } from "../data/hunt";
import { ShadowFigure } from "../entities/ShadowFigure";

export interface SearchJar {
  id: string;
  root: TransformNode;
  lid: TransformNode;
  contents: TransformNode;
  opening: number;
}

/** Hollow glazed jars, removable wooden lids, cut brass pieces and the low, dragging shadow. */
export class HuntModels {
  readonly jars: SearchJar[] = [];
  readonly roamer: TransformNode;
  readonly meshes: Mesh[] = [];
  private form!: ShadowFigure;
  private readonly brass: PBRMaterial;
  private readonly dark: PBRMaterial;
  private readonly wood: PBRMaterial;
  private readonly cloth: PBRMaterial;
  private preview: TransformNode | null = null;
  private previewPieces: TransformNode[] = [];
  private previewLight: PointLight | null = null;

  constructor(
    private readonly scene: Scene,
    area: Area,
  ) {
    this.brass = this.agedBrass();
    this.dark = this.mat("charcoal", "#111512", 0.96);
    this.wood = this.textured("lid_teak", "#58432c", false);
    this.cloth = this.textured("worn_cotton", "#7e7257", true);
    const ceramic = this.textured("jar_glaze", "#493a28", false);
    ceramic.roughness = 0.36;
    const foot = this.mat("jar_unglazed_foot", "#725239", 0.96);
    for (const [index, spec] of JARS.entries()) {
      const marker = area.level.interactables.find((m) => m.name === `interact_jar_${spec.id}`);
      if (!marker) throw new Error(`[Under-house] missing jar ${spec.id}`);
      marker.node.setEnabled(false);
      const root = this.root(`hunt_jar_${spec.id}`, spec.at);
      const profile = [
        [0, 0.025],
        [0.22, 0.025],
        [0.29, 0.1],
        [0.35, 0.32],
        [0.34, 0.56],
        [0.26, 0.74],
        [0.208, 0.82],
        [0.208, 0.855],
        [0.23, 0.86],
        [0.239, 0.842],
        [0.225, 0.812],
        [0.226, 0.78],
        [0.314, 0.55],
        [0.324, 0.32],
        [0.265, 0.12],
        [0.17, 0.085],
        [0, 0.085],
      ];
      const body = CreateLathe(
        `${spec.id}_hollow_jar`,
        {
          shape: profile.map(([r, y]) => new Vector3(r, y, 0)),
          tessellation: 80,
          sideOrientation: Mesh.DOUBLESIDE,
        },
        scene,
      );
      this.finish(body, root, [0, 0, 0], ceramic);
      this.cylinder(root, `${spec.id}_foot_ring`, 0.45, 0.028, [0, 0.025, 0], foot);
      for (const y of [0.72, 0.75, 0.805]) {
        const band = CreateTorus(
          `${spec.id}_thrown_ridge`,
          { diameter: y < 0.8 ? 0.53 : 0.438, thickness: 0.005, tessellation: 80 },
          scene,
        );
        this.finish(band, root, [0, y, 0], ceramic);
      }
      // Raised maker's mark and old mineral drips catch grazing lamplight.
      for (let k = 0; k < 3; k++)
        this.box(
          root,
          `${spec.id}_potters_stamp`,
          [0.018, 0.005, 0.003],
          [-0.023 + k * 0.022, 0.5, 0.341],
          foot,
        );
      const lid = this.root(`${spec.id}_removable_lid`, new Vector3(0, 0.87, 0), root);
      this.cylinder(lid, `${spec.id}_lid_disc`, 0.445, 0.025, [0, 0, 0], this.wood);
      this.cylinder(lid, `${spec.id}_lid_lip`, 0.395, 0.014, [0, -0.018, 0], this.wood);
      for (const x of [-0.095, 0.095])
        this.box(lid, `${spec.id}_lid_batten`, [0.016, 0.011, 0.36], [x, 0.017, 0], this.wood);
      this.tube(
        lid,
        `${spec.id}_rattan_lift`,
        [
          [-0.055, 0.02, 0],
          [-0.05, 0.06, 0],
          [0, 0.085, 0],
          [0.05, 0.06, 0],
          [0.055, 0.02, 0],
        ],
        0.006,
        this.cloth,
      );
      const contents = this.root(`${spec.id}_contents`, new Vector3(0, 0.665, 0), root);
      this.cylinder(contents, `${spec.id}_cloth_pad`, 0.34, 0.012, [0, -0.013, 0], this.cloth);
      if (spec.contents === "key") {
        const piece = this.keyPiece(contents, spec.piece);
        piece.rotation.x = Math.PI / 2;
        piece.rotation.z = index * 0.13;
      } else if (spec.contents === "oil") {
        const bottle = this.mat(`${spec.id}_oil_ceramic`, "#776347", 0.42);
        this.cylinder(contents, `${spec.id}_oil_bottle`, 0.075, 0.09, [0, 0.035, 0], bottle);
        this.cylinder(contents, `${spec.id}_bottle_neck`, 0.03, 0.025, [0, 0.092, 0], bottle);
        this.cylinder(contents, `${spec.id}_bottle_cork`, 0.026, 0.012, [0, 0.109, 0], this.wood);
      } else {
        const paper = this.mat("jar_journal_paper", "#c5b088", 1);
        for (let k = 0; k < 4; k++) {
          const note = this.box(
            contents,
            "jar_journal_fold",
            [0.14, 0.002, 0.09],
            [0, k * 0.003, 0],
            paper,
          );
          note.rotation.y = 0.12;
        }
        this.box(
          contents,
          "jar_journal_tie",
          [0.009, 0.015, 0.105],
          [0, 0.006, 0],
          this.cloth,
        ).rotation.y = 0.12;
      }
      this.jars.push({ id: spec.id, root, lid, contents, opening: 0 });
    }
    this.roamer = this.root("under_house_roamer", Vector3.Zero());
    this.buildRoamer();
    this.roamer.setEnabled(false);
    area.container.meshes.push(...this.meshes);
  }

  jarState(id: string, opened: boolean, taken: boolean, instant = false): void {
    const jar = this.jars.find((j) => j.id === id)!;
    if (instant) jar.opening = Number(opened);
    jar.contents.setEnabled(opened && !taken);
    jar.lid.metadata = { opened };
  }
  updateJars(dt: number): void {
    for (const jar of this.jars) {
      const target = Number((jar.lid.metadata as { opened: boolean } | null)?.opened ?? false);
      jar.opening += (target - jar.opening) * (1 - Math.exp(-dt * 6));
      jar.lid.position.set(
        jar.opening * 0.34,
        0.87 + Math.sin((jar.opening * Math.PI) / 2) * 0.15,
        jar.opening * 0.1,
      );
      jar.lid.rotation.z = -jar.opening * 0.85;
    }
  }
  pose(at: Vector3, direction: Vector3, seconds: number, visibility: number): void {
    this.roamer.position.copyFrom(at);
    this.roamer.rotation.y = Math.atan2(direction.x, direction.z);
    this.form.animate(seconds, 0.65);
    this.roamer.setEnabled(visibility > 0);
    this.form.setPresence(visibility);
  }

  createPreview(camera: Camera): void {
    this.preview = this.root("satchel_key_workspace", new Vector3(0.22, 0.04, 0.62));
    this.preview.parent = camera;
    this.preview.rotation.z = -0.05;
    const first = this.meshes.length;
    this.box(this.preview, "key_work_cloth", [0.3, 0.19, 0.007], [0, 0, 0.012], this.cloth);
    for (const y of [-0.087, 0.087])
      this.box(this.preview, "cloth_hem", [0.29, 0.003, 0.002], [0, y, 0.006], this.wood);
    this.previewPieces = [0, 1, 2].map((k) => this.keyPiece(this.preview!, k));
    for (const x of [-0.143, 0.143])
      this.box(this.preview, "cloth_side_hem", [0.003, 0.174, 0.002], [x, 0, 0.006], this.cloth);
    // Raised, slightly uneven thread, visible against the woven backing.
    const thread = this.mat("linen_stitch", "#ad9c78", 1);
    for (const y of [-0.079, 0.079])
      this.tube(
        this.preview,
        "cloth_running_stitch",
        Array.from({ length: 57 }, (_, i) => [
          -0.135 + i * 0.0048,
          y + (i % 2) * 0.001,
          0.006 - (i % 2) * 0.002,
        ]),
        0.0005,
        thread,
      );
    const meshes = this.meshes.slice(first);
    meshes.forEach((m) => {
      m.renderingGroupId = 1;
      m.isPickable = false;
    });
    for (const light of this.scene.lights) light.excludedMeshes.push(...meshes);
    this.previewLight = new PointLight(
      "key_workspace_light",
      new Vector3(0.1, 0.2, 0.2),
      this.scene,
    );
    this.previewLight.parent = camera;
    this.previewLight.intensity = 0.35;
    this.previewLight.diffuse = new Color3(1, 0.83, 0.62);
    this.previewLight.includedOnlyMeshes = meshes;
    this.preview.setEnabled(false);
  }
  showPreview(visible: boolean, pieces: boolean[], assembled: boolean, blend = 0): void {
    if (!this.preview) return;
    this.preview.setEnabled(visible);
    if (this.previewLight) this.previewLight.setEnabled(visible);
    const separated = [
      new Vector3(-0.025, 0.036, 0),
      new Vector3(0, -0.025, 0),
      new Vector3(0.035, 0.025, 0),
    ];
    this.previewPieces.forEach((root, i) => {
      root.setEnabled(pieces[i] || assembled);
      root.position.copyFrom(separated[i].scale(assembled ? 0 : 1 - blend));
      root.position.z = -0.008;
      root.rotation.z = (i - 1) * 0.18 * (assembled ? 0 : 1 - blend);
    });
  }

  private keyPiece(parent: TransformNode, index: number): TransformNode {
    const root = this.root(`brass_key_piece_${index}`, Vector3.Zero(), parent);
    if (index === 0) {
      const bow = CreateTorus(
        "key_bow_forged_ring",
        { diameter: 0.047, thickness: 0.006, tessellation: 48 },
        this.scene,
      );
      this.finish(bow, root, [-0.055, 0, 0], this.brass);
      bow.rotation.x = Math.PI / 2;
      this.shaft(root, -0.032, 0.024);
      for (const y of [-0.011, 0.011])
        this.box(root, "key_bow_engraving", [0.012, 0.001, 0.001], [-0.055, y, -0.0035], this.dark);
    } else if (index === 1) {
      this.shaft(root, 0.004, 0.047);
      for (const x of [-0.006, 0.009])
        this.box(root, "key_shaft_etch", [0.001, 0.005, 0.001], [x, 0, -0.0038], this.dark);
    } else {
      this.shaft(root, 0.047, 0.039);
      this.box(root, "key_bit_shoulder", [0.033, 0.012, 0.007], [0.048, -0.006, 0], this.brass);
      for (const [x, h] of [
        [0.035, 0.014],
        [0.05, 0.021],
        [0.063, 0.011],
      ])
        this.box(root, "key_cut_tooth", [0.007, h, 0.006], [x, -0.009 - h / 2, 0], this.brass);
    }
    // Uneven fractured ends, rather than three clean saw cuts.
    for (const x of index === 0 ? [-0.019] : index === 1 ? [-0.019, 0.027] : [0.027])
      for (let k = 0; k < 3; k++)
        this.box(
          root,
          "key_broken_grain",
          [0.003, 0.0015, 0.002],
          [x + (k % 2) * 0.001, (k - 1) * 0.002, 0],
          this.brass,
        );
    return root;
  }
  private shaft(root: TransformNode, x: number, length: number): void {
    const shaft = this.cylinder(
      root,
      "hollow_brass_key_shaft",
      0.008,
      length,
      [x, 0, 0],
      this.brass,
    );
    shaft.rotation.z = Math.PI / 2;
  }
  private buildRoamer(): void {
    this.form = new ShadowFigure(this.scene, "roamer", 1.87);
    this.form.root.parent = this.roamer;
    this.meshes.push(...this.form.meshes);
  }
  private root(name: string, at: Vector3, parent?: TransformNode): TransformNode {
    const root = new TransformNode(name, this.scene);
    root.position.copyFrom(at);
    if (parent) root.parent = parent;
    return root;
  }
  private mat(name: string, hex: string, roughness: number, metallic = 0): PBRMaterial {
    const m = new PBRMaterial(`M_hunt_${name}`, this.scene);
    m.albedoColor = Color3.FromHexString(hex);
    m.roughness = roughness;
    m.metallic = metallic;
    m.maxSimultaneousLights = 8;
    return m;
  }
  private finish(mesh: Mesh, parent: TransformNode, at: number[], material: PBRMaterial): Mesh {
    mesh.parent = parent;
    mesh.position.set(at[0], at[1], at[2]);
    mesh.material = material;
    this.meshes.push(mesh);
    return mesh;
  }
  private box(
    root: TransformNode,
    name: string,
    size: number[],
    at: number[],
    mat: PBRMaterial,
  ): Mesh {
    return this.finish(
      CreateBox(name, { width: size[0], height: size[1], depth: size[2] }, this.scene),
      root,
      at,
      mat,
    );
  }
  private cylinder(
    root: TransformNode,
    name: string,
    diameter: number,
    height: number,
    at: number[],
    mat: PBRMaterial,
  ): Mesh {
    return this.finish(
      CreateCylinder(name, { diameter, height, tessellation: 48 }, this.scene),
      root,
      at,
      mat,
    );
  }
  private tube(
    root: TransformNode,
    name: string,
    path: number[][],
    radius: number,
    mat: PBRMaterial,
  ): Mesh {
    return this.finish(
      CreateTube(
        name,
        { path: path.map((p) => new Vector3(...p)), radius, tessellation: 10, cap: Mesh.CAP_ALL },
        this.scene,
      ),
      root,
      [0, 0, 0],
      mat,
    );
  }
  private agedBrass(): PBRMaterial {
    const mat = this.mat("aged_cut_brass", "#ffffff", 0.47, 0.78);
    const texture = new DynamicTexture("T_hunt_brass_wear", 256, this.scene, true);
    const c = texture.getContext() as CanvasRenderingContext2D,
      rand = seededRandom(1210);
    c.fillStyle = "#aa884c";
    c.fillRect(0, 0, 256, 256);
    for (let i = 0; i < 120; i++) {
      const x = rand() * 256,
        y = rand() * 256,
        r = 2 + rand() * 13;
      const gradient = c.createRadialGradient(x, y, 0, x, y, r);
      gradient.addColorStop(0, "rgba(31,54,39,0.48)");
      gradient.addColorStop(1, "rgba(31,54,39,0)");
      c.fillStyle = gradient;
      c.fillRect(x - r, y - r, r * 2, r * 2);
    }
    for (let i = 0; i < 1200; i++) {
      c.strokeStyle = rand() > 0.5 ? "rgba(233,204,135,0.16)" : "rgba(30,28,15,0.17)";
      c.lineWidth = 0.4;
      const x = rand() * 256,
        y = rand() * 256;
      c.beginPath();
      c.moveTo(x, y);
      c.lineTo(x + rand() * 8, y + rand() * 2);
      c.stroke();
    }
    texture.update();
    mat.albedoTexture = texture;
    return mat;
  }
  private textured(name: string, color: string, woven: boolean): PBRMaterial {
    const mat = this.mat(name, "#ffffff", woven ? 0.98 : 0.7),
      tex = new DynamicTexture(`T_hunt_${name}`, 512, this.scene, true),
      c = tex.getContext() as CanvasRenderingContext2D,
      rand = seededRandom(woven ? 1120 : 1121);
    c.fillStyle = color;
    c.fillRect(0, 0, 512, 512);
    for (let k = 0; k < (woven ? 0 : 1400); k++) {
      c.strokeStyle = `rgba(${rand() > 0.5 ? "192,153,99" : "15,16,12"},${rand() * 0.11})`;
      c.lineWidth = 0.5 + rand();
      const x = rand() * 512;
      c.beginPath();
      c.moveTo(x, 0);
      c.bezierCurveTo(x + rand() * 10, 150, x - rand() * 15, 350, x, 512);
      c.stroke();
    }
    if (woven) {
      // Crossed warp and weft, with the small irregularities of hand-woven cotton.
      for (let k = 0; k < 512; k += 4) {
        c.fillStyle = `rgba(20,18,13,${0.12 + rand() * 0.14})`;
        c.fillRect(k, 0, 1, 512);
        c.fillRect(0, k, 512, 1);
        c.fillStyle = "rgba(212,198,160,0.12)";
        c.fillRect(k + 1, 0, 1, 512);
        c.fillRect(0, k + 1, 512, 1);
        for (let x = 0; x < 512; x += 8) {
          c.fillStyle = "rgba(15,15,12,0.12)";
          c.fillRect(x + (k % 8), k, 2, 2);
        }
      }
      for (let k = 0; k < 450; k++) {
        c.fillStyle = "rgba(18,16,12,0.06)";
        c.beginPath();
        c.ellipse(
          rand() * 512,
          rand() * 512,
          2 + rand() * 10,
          1 + rand() * 3,
          rand() * 6,
          0,
          Math.PI * 2,
        );
        c.fill();
      }
    }
    tex.update();
    mat.albedoTexture = tex;
    return mat;
  }
}
