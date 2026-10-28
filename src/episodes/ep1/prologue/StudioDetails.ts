import { createTelephoneReceiver } from "../../../player/TelephoneReceiver";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { VertexData } from "@babylonjs/core/Meshes/mesh.vertexData";
import { CreateBox } from "@babylonjs/core/Meshes/Builders/boxBuilder";
import { CreateCylinder } from "@babylonjs/core/Meshes/Builders/cylinderBuilder";
import { CreateLathe } from "@babylonjs/core/Meshes/Builders/latheBuilder";
import { CreateTorus } from "@babylonjs/core/Meshes/Builders/torusBuilder";
import { CreateTube } from "@babylonjs/core/Meshes/Builders/tubeBuilder";
import { CreatePlane } from "@babylonjs/core/Meshes/Builders/planeBuilder";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { Scene } from "@babylonjs/core/scene";
import type { Area } from "../../../core/AreaLoader";
import { mergeStaticMeshes } from "../../../render/StaticBatcher";
import { seededRandom } from "../../../audio/synth";

/** Close-range studio craftsmanship. Existing anchors, colliders and story IDs remain authoritative. */
export class StudioDetails {
  readonly drawerTravel = 0.46;
  readonly matchbox: Mesh;
  private readonly walnut: PBRMaterial;
  private readonly drawerWood: PBRMaterial;
  private readonly brass: PBRMaterial;
  private readonly darkBrass: PBRMaterial;
  private readonly black: PBRMaterial;
  private readonly paper: PBRMaterial;
  private readonly ceramic: PBRMaterial;
  private readonly staticMeshes: Mesh[] = [];
  private batching = false;
  private phoneCord: Mesh | null = null;
  private phoneCordRest!: TransformNode;
  private phoneCordSocket!: TransformNode;
  private readonly lastCordEnd = new Vector3(Infinity, Infinity, Infinity);

  constructor(
    private readonly scene: Scene,
    area: Area,
  ) {
    this.walnut = this.wood("polished_walnut", "#614334", 0.46);
    this.drawerWood = this.wood("drawer_cedar", "#a58a64", 0.78);
    this.brass = this.patinatedMetal();
    this.darkBrass = this.mat("oxidised_brass", "#554a34", 0.72, 0.58);
    this.black = this.mat("ebonite", "#272620", 0.32, 0.12);
    this.black.clearCoat.isEnabled = true;
    this.black.clearCoat.intensity = 0.3;
    this.black.clearCoat.roughness = 0.26;
    this.paper = this.mat("unbleached_paper", "#dfcfaa", 0.98);
    this.ceramic = this.mat("glazed_ivory", "#ccc4a8", 0.23);
    this.ceramic.clearCoat.isEnabled = true;
    this.ceramic.clearCoat.intensity = 0.45;
    this.buildPhone(this.anchor(area, "interact_telephone"));
    this.buildDrawer(this.anchor(area, "interact_drawer"));
    const matchbox = scene.getMeshByName("matchbox");
    if (!(matchbox instanceof Mesh)) throw new Error("[Studio] missing matchbox");
    this.matchbox = matchbox;
    this.buildMatchbox();
    this.buildLetters();
    this.batching = true;
    this.buildWorkingDetails();
    this.buildWallSconce();
    this.buildBankersLamp();
    mergeStaticMeshes(this.staticMeshes, { cellSize: 3 });
  }

  private anchor(area: Area, name: string): TransformNode {
    const node = area.level.interactables.find((m) => m.name === name)?.node;
    if (!node) throw new Error(`[Studio] missing ${name}`);
    return node;
  }

  private mat(name: string, colour: string, roughness: number, metallic = 0): PBRMaterial {
    const mat = new PBRMaterial(`M_studio_${name}`, this.scene);
    mat.albedoColor = Color3.FromHexString(colour).toLinearSpace();
    mat.roughness = roughness;
    mat.metallic = metallic;
    mat.maxSimultaneousLights = 8;
    return mat;
  }

  private wood(name: string, colour: string, roughness: number): PBRMaterial {
    const mat = this.mat(name, colour, roughness);
    const tex = new DynamicTexture(
      `T_studio_${name}`,
      { width: 256, height: 512 },
      this.scene,
      true,
    );
    const c = tex.getContext() as unknown as CanvasRenderingContext2D;
    const rand = seededRandom(807);
    c.fillStyle = colour;
    c.fillRect(0, 0, 256, 512);
    for (let i = 0; i < 480; i++) {
      const x = rand() * 256;
      c.strokeStyle = i % 3 ? `rgba(23,13,7,${0.025 + rand() * 0.11})` : "rgba(225,197,143,0.09)";
      c.lineWidth = 0.4 + rand() * 1.2;
      c.beginPath();
      c.moveTo(x, 0);
      c.bezierCurveTo(x + rand() * 12, 170, x - rand() * 9, 340, x + rand() * 5, 512);
      c.stroke();
    }
    tex.update();
    mat.albedoTexture = tex;
    mat.albedoColor.set(1, 1, 1);
    return mat;
  }

  private patinatedMetal(): PBRMaterial {
    const mat = this.mat("aged_brass", "#b29860", 0.46, 0.68);
    const tex = new DynamicTexture("T_studio_brass_patina", 256, this.scene, true);
    const c = tex.getContext(),
      rand = seededRandom(421);
    c.fillStyle = "#b29860";
    c.fillRect(0, 0, 256, 256);
    for (let i = 0; i < 3200; i++) {
      c.fillStyle = i % 4 ? "rgba(45,40,24,0.055)" : "rgba(77,105,80,0.09)";
      c.fillRect(rand() * 256, rand() * 256, 1 + rand() * 8, 1 + rand() * 3);
    }
    tex.update();
    mat.albedoTexture = tex;
    mat.albedoColor.set(1, 1, 1);
    return mat;
  }

  private attach(
    mesh: Mesh,
    parent: TransformNode | null,
    position: number[],
    mat: PBRMaterial,
  ): Mesh {
    mesh.parent = parent;
    mesh.position.set(position[0], position[1], position[2]);
    mesh.material = mat;
    mesh.receiveShadows = true;
    if (this.batching) {
      mesh.isPickable = false;
      this.staticMeshes.push(mesh);
    }
    return mesh;
  }

  private box(
    parent: TransformNode | null,
    name: string,
    size: number[],
    at: number[],
    mat: PBRMaterial,
  ): Mesh {
    return this.attach(
      CreateBox(`studio_${name}`, { width: size[0], height: size[1], depth: size[2] }, this.scene),
      parent,
      at,
      mat,
    );
  }

  private cylinder(
    parent: TransformNode | null,
    name: string,
    diameter: number,
    height: number,
    at: number[],
    mat: PBRMaterial,
    top = diameter,
  ): Mesh {
    return this.attach(
      CreateCylinder(
        `studio_${name}`,
        { diameterBottom: diameter, diameterTop: top, height, tessellation: 40 },
        this.scene,
      ),
      parent,
      at,
      mat,
    );
  }

  private lathe(
    parent: TransformNode | null,
    name: string,
    profile: number[][],
    at: number[],
    mat: PBRMaterial,
  ): Mesh {
    return this.attach(
      CreateLathe(
        `studio_${name}`,
        {
          shape: profile.map(([r, y]) => new Vector3(r, y, 0)),
          tessellation: 48,
          sideOrientation: Mesh.DOUBLESIDE,
        },
        this.scene,
      ),
      parent,
      at,
      mat,
    );
  }

  private tube(
    parent: TransformNode | null,
    name: string,
    path: number[][],
    radius: number,
    mat: PBRMaterial,
  ): Mesh {
    return this.attach(
      CreateTube(
        `studio_${name}`,
        {
          path: path.map((p) => new Vector3(...(p as [number, number, number]))),
          radius,
          tessellation: 8,
          cap: Mesh.CAP_ALL,
        },
        this.scene,
      ),
      parent,
      [0, 0, 0],
      mat,
    );
  }

  private ring(
    parent: TransformNode | null,
    name: string,
    diameter: number,
    thickness: number,
    at: number[],
    mat: PBRMaterial,
    front = true,
  ): Mesh {
    const mesh = this.attach(
      CreateTorus(`studio_${name}`, { diameter, thickness, tessellation: 48 }, this.scene),
      parent,
      at,
      mat,
    );
    if (front) mesh.rotation.x = Math.PI / 2;
    return mesh;
  }

  /** A chamfered slab: bevels catch the practical lights rather than infinitely sharp box edges. */
  private slab(
    parent: TransformNode,
    name: string,
    w: number,
    h: number,
    depth: number,
    at: number[],
    mat: PBRMaterial,
  ): Mesh {
    const mesh = new Mesh(`studio_${name}`, this.scene);
    const positions: number[] = [],
      indices: number[] = [],
      uvs: number[] = [];
    const corner = Math.min(w, h) * 0.08,
      bevel = Math.min(depth * 0.22, 0.004);
    for (const [z, inset] of [
      [-depth / 2, bevel],
      [-depth / 2 + bevel, 0],
      [depth / 2 - bevel, 0],
      [depth / 2, bevel],
    ]) {
      const x = w / 2 - inset,
        y = h / 2 - inset;
      for (const [px, py] of [
        [-x + corner, -y],
        [x - corner, -y],
        [x, -y + corner],
        [x, y - corner],
        [x - corner, y],
        [-x + corner, y],
        [-x, y - corner],
        [-x, -y + corner],
      ]) {
        positions.push(px, py, z);
        uvs.push(px / w + 0.5, py / h + 0.5);
      }
    }
    for (let r = 0; r < 3; r++)
      for (let i = 0; i < 8; i++) {
        const a = r * 8 + i,
          b = r * 8 + ((i + 1) % 8);
        indices.push(a, b, b + 8, a, b + 8, a + 8);
      }
    for (let i = 1; i < 7; i++) indices.push(0, i + 1, i, 24, 24 + i, 25 + i);
    const normals: number[] = [];
    VertexData.ComputeNormals(positions, indices, normals);
    const data = new VertexData();
    data.positions = positions;
    data.indices = indices;
    data.normals = normals;
    data.uvs = uvs;
    data.applyToMesh(mesh);
    return this.attach(mesh, parent, at, mat);
  }

  private label(
    name: string,
    width: number,
    height: number,
    draw: (c: CanvasRenderingContext2D) => void,
  ): PBRMaterial {
    const mat = this.mat(name, "#ffffff", 0.85);
    const tex = new DynamicTexture(`T_${name}`, { width, height }, this.scene, true);
    draw(tex.getContext() as unknown as CanvasRenderingContext2D);
    tex.update();
    mat.albedoTexture = tex;
    mat.backFaceCulling = false;
    return mat;
  }

  private batchParts(root: TransformNode, exclude?: TransformNode): void {
    const groups = new Map<number, Mesh[]>();
    for (const child of root.getChildMeshes(false)) {
      if (!(child instanceof Mesh) || !child.material || child.visibility === 0) continue;
      if (exclude && child.isDescendantOf(exclude)) continue;
      const key = child.material.uniqueId;
      const list = groups.get(key) ?? [];
      list.push(child);
      groups.set(key, list);
    }
    for (const list of groups.values()) {
      if (list.length < 2) continue;
      const mesh = Mesh.MergeMeshes(list, true, true);
      if (!mesh) continue;
      mesh.name = `studio_crafted_${root.name}_${mesh.material?.name}`;
      mesh.receiveShadows = true;
      mesh.setParent(root);
    }
  }

  private buildPhone(anchor: TransformNode): void {
    for (const mesh of anchor.getChildMeshes(false)) {
      if (mesh.name === "telephone_earpiece") mesh.name = "telephone_earpiece_legacy";
      mesh.setEnabled(false);
    }
    const root = new TransformNode("studio_magneto_phone", this.scene);
    root.position.copyFrom(anchor.getAbsolutePosition());
    root.rotation.y = Math.PI / 2;
    // Imported Blender roots mirror an axis. Preserve our world-space pose
    // when attaching the replacement, otherwise the phone grows into the wall.
    root.setParent(anchor);
    this.slab(root, "phone_walnut_backboard", 0.33, 0.62, 0.033, [0, 0, 0.025], this.walnut);
    this.slab(root, "phone_panel_rebate", 0.282, 0.45, 0.016, [0, -0.025, 0.048], this.walnut);
    this.slab(root, "phone_magneto_case", 0.26, 0.29, 0.07, [0, -0.105, 0.087], this.walnut);
    for (const x of [-0.088, 0.088]) {
      const bell = this.lathe(
        root,
        "phone_bell_dome",
        [
          [0, 0],
          [0.024, 0.006],
          [0.049, 0.024],
          [0.066, 0.05],
          [0.067, 0.058],
          [0.061, 0.063],
          [0.054, 0.048],
        ],
        [x, 0.178, 0.15],
        this.brass,
      );
      bell.rotation.x = -Math.PI / 2;
      this.ring(root, "bell_rolled_rim", 0.129, 0.004, [x, 0.178, 0.09], this.darkBrass);
      const pin = this.cylinder(root, "bell_nut", 0.014, 0.012, [x, 0.178, 0.154], this.darkBrass);
      pin.rotation.x = Math.PI / 2;
    }
    this.tube(
      root,
      "bell_clapper",
      [
        [0, 0.14, 0.07],
        [0, 0.198, 0.071],
      ],
      0.004,
      this.darkBrass,
    );
    this.cylinder(root, "clapper_head", 0.019, 0.01, [0, 0.204, 0.07], this.brass);
    const mouth = this.lathe(
      root,
      "transmitter_trumpet",
      [
        [0.023, 0],
        [0.027, 0.013],
        [0.036, 0.037],
        [0.061, 0.069],
        [0.072, 0.08],
        [0.074, 0.087],
        [0.065, 0.088],
        [0.045, 0.063],
        [0.019, 0.032],
      ],
      [0.02, -0.032, 0.126],
      this.black,
    );
    mouth.rotation.x = Math.PI / 2;
    this.ring(root, "mouthpiece_brass_lip", 0.142, 0.006, [0.02, -0.032, 0.214], this.brass);
    const diaphragm = this.cylinder(
      root,
      "transmitter_diaphragm",
      0.08,
      0.004,
      [0.02, -0.032, 0.177],
      this.black,
    );
    diaphragm.rotation.x = Math.PI / 2;
    for (let i = 0; i < 7; i++) {
      const angle = (i / 7) * Math.PI * 2;
      const hole = this.cylinder(
        root,
        "diaphragm_perforation",
        0.006,
        0.001,
        [0.02 + Math.cos(angle) * 0.022, -0.032 + Math.sin(angle) * 0.022, 0.18],
        this.darkBrass,
      );
      hole.rotation.x = Math.PI / 2;
    }
    const receiver = createTelephoneReceiver(this.scene, "telephone_earpiece");
    receiver.parent = root;
    receiver.position.set(-0.193, -0.075, 0.105);
    this.phoneCordRest = new TransformNode("telephone_cord_rest", this.scene);
    this.phoneCordRest.parent = receiver;
    this.phoneCordRest.position.set(0, -0.116, 0);
    this.phoneCordSocket = new TransformNode("telephone_cord_terminal", this.scene);
    this.phoneCordSocket.parent = root;
    this.phoneCordSocket.position.set(-0.055, -0.32, 0.05);
    this.tube(
      root,
      "receiver_hook",
      [
        [-0.12, 0.01, 0.07],
        [-0.175, 0.01, 0.07],
        [-0.19, 0.016, 0.11],
      ],
      0.006,
      this.brass,
    );
    this.tube(
      root,
      "magneto_crank",
      [
        [0.13, -0.125, 0.09],
        [0.194, -0.125, 0.09],
        [0.194, -0.197, 0.09],
        [0.227, -0.197, 0.09],
      ],
      0.006,
      this.brass,
    );
    const crank = this.lathe(
      root,
      "crank_turned_grip",
      [
        [0.008, 0],
        [0.014, 0.008],
        [0.016, 0.03],
        [0.014, 0.052],
        [0.008, 0.06],
      ],
      [0.223, -0.197, 0.09],
      this.black,
    );
    crank.rotation.z = -Math.PI / 2;
    for (const x of [-0.13, 0.13])
      for (const y of [-0.263, 0.263]) {
        const screw = this.cylinder(
          root,
          "phone_slotted_screw",
          0.012,
          0.003,
          [x, y, 0.045],
          this.brass,
        );
        screw.rotation.x = Math.PI / 2;
        this.box(root, "screw_slot", [0.008, 0.0014, 0.001], [x, y, 0.047], this.black).rotation.z =
          0.36;
      }
    const plaque = this.label("phone_enamel_plate", 512, 192, (c) => {
      c.fillStyle = "#cbc3a7";
      c.fillRect(0, 0, 512, 192);
      c.strokeStyle = "#70614a";
      c.lineWidth = 7;
      c.strokeRect(12, 12, 488, 168);
      c.textAlign = "center";
      c.fillStyle = "#3b382d";
      c.font = "28px serif";
      c.fillText("TÉLÉPHONE", 256, 73);
      c.font = "bold 46px serif";
      c.fillText("Nº 17", 256, 132);
    });
    this.box(
      root,
      "phone_number_plate_rim",
      [0.108, 0.044, 0.003],
      [0.005, -0.216, 0.124],
      this.darkBrass,
    );
    const number = this.attach(
      CreatePlane("studio_phone_enamel_number", { width: 0.102, height: 0.038 }, this.scene),
      root,
      [0.005, -0.216, 0.126],
      plaque,
    );
    number.rotation.y = Math.PI;
    for (const x of [-0.055, 0.055]) {
      this.cylinder(root, "porcelain_terminal", 0.02, 0.022, [x, -0.318, 0.042], this.ceramic);
      this.tube(
        root,
        "terminal_lead",
        [
          [x, -0.32, 0.042],
          [x, -0.37, 0.022],
          [x * 0.8, -0.43, 0.01],
        ],
        0.002,
        this.black,
      );
    }
    // A continuous interior target, including gaps between the bells and receiver.
    const hit = this.box(
      root,
      "phone_pickup_volume",
      [0.44, 0.65, 0.19],
      [-0.025, -0.015, 0.1],
      this.black,
    );
    hit.visibility = 0;
    this.batchParts(root, receiver);
    this.updateTelephoneCord();
  }

  updateTelephoneCord(heldEnd: Vector3 | null = null): void {
    const end = heldEnd ?? this.phoneCordRest.getAbsolutePosition();
    if (Vector3.DistanceSquared(end, this.lastCordEnd) < 0.000001) return;
    this.lastCordEnd.copyFrom(end);
    const start = this.phoneCordSocket.getAbsolutePosition();
    const sag = Math.min(0.3, Math.max(0.12, Vector3.Distance(start, end) * 0.22));
    const path = Array.from({ length: 33 }, (_, i) => {
      const t = i / 32,
        p = Vector3.Lerp(start, end, t);
      p.y -= Math.sin(t * Math.PI) * sag;
      p.x += Math.sin(t * Math.PI) * 0.035;
      return p;
    });
    this.phoneCord = CreateTube(
      "studio_cloth_telephone_cord",
      {
        path,
        radius: 0.0026,
        tessellation: 8,
        cap: Mesh.CAP_ALL,
        updatable: true,
        instance: this.phoneCord ?? undefined,
      },
      this.scene,
    );
    this.phoneCord.material = this.black;
    this.phoneCord.isPickable = false;
  }

  private buildDrawer(drawer: TransformNode): void {
    if (drawer instanceof Mesh) drawer.visibility = 0;
    this.scene.getMeshByName("drawer_knob")?.setEnabled(false);
    const moving = new TransformNode("studio_drawer_interior", this.scene);
    moving.position.copyFrom(drawer.getAbsolutePosition());
    moving.setParent(drawer);
    drawer = moving;
    this.box(drawer, "drawer_bottom", [0.42, 0.012, 0.47], [0.205, -0.044, 0], this.drawerWood);
    for (const z of [-0.238, 0.238])
      this.box(drawer, "drawer_side", [0.42, 0.065, 0.012], [0.205, -0.017, z], this.drawerWood);
    this.box(drawer, "drawer_back", [0.012, 0.065, 0.48], [0.411, -0.017, 0], this.drawerWood);
    const face = this.slab(
      drawer,
      "drawer_moulded_front",
      0.5,
      0.105,
      0.026,
      [0, 0, 0],
      this.walnut,
    );
    face.rotation.y = Math.PI / 2;
    const inset = this.slab(
      drawer,
      "drawer_front_rebate",
      0.444,
      0.067,
      0.006,
      [-0.016, 0, 0],
      this.drawerWood,
    );
    inset.rotation.y = Math.PI / 2;
    const plate = this.cylinder(
      drawer,
      "drawer_handle_rosette",
      0.035,
      0.005,
      [-0.025, 0, 0],
      this.darkBrass,
    );
    plate.rotation.z = Math.PI / 2;
    this.tube(
      drawer,
      "drawer_drop_pull",
      [
        [-0.034, 0.008, -0.018],
        [-0.049, -0.013, -0.021],
        [-0.053, -0.024, 0],
        [-0.049, -0.013, 0.021],
        [-0.034, 0.008, 0.018],
      ],
      0.004,
      this.brass,
    );
    // Pencil nubs and a spare button make the interior read as an actual working drawer.
    for (let i = 0; i < 3; i++) {
      const pencil = this.cylinder(
        drawer,
        "drawer_pencil_stub",
        0.006,
        0.09,
        [0.19, -0.032, 0.16 + i * 0.012],
        this.paper,
      );
      pencil.rotation.z = Math.PI / 2;
    }
    this.cylinder(drawer, "drawer_spare_button", 0.016, 0.003, [0.28, -0.035, -0.16], this.ceramic);
    this.batchParts(drawer);
  }

  private buildMatchbox(): void {
    const box = this.matchbox;
    box.setAbsolutePosition(new Vector3(-0.43, 0.65, -2.65));
    box.visibility = 0;
    const detail = new TransformNode("studio_matchbox_detail", this.scene);
    detail.position.copyFrom(box.getAbsolutePosition());
    detail.setParent(box);
    this.box(detail, "matchbox_cardboard_sleeve", [0.076, 0.032, 0.105], [0, 0, 0], this.paper);
    const striker = this.mat("matchbox_striker", "#61443b", 0.96);
    for (const x of [-0.0383, 0.0383])
      this.box(detail, "matchbox_striker", [0.001, 0.018, 0.088], [x, 0, 0], striker);
    const label = this.label("matchbox_label", 512, 384, (c) => {
      const rand = seededRandom(83);
      c.fillStyle = "#dbc8a1";
      c.fillRect(0, 0, 512, 384);
      c.fillStyle = "#963e29";
      c.fillRect(15, 15, 482, 354);
      c.fillStyle = "#eddfba";
      c.fillRect(30, 30, 452, 324);
      c.strokeStyle = "#963e29";
      c.lineWidth = 4;
      c.strokeRect(42, 42, 428, 300);
      c.textAlign = "center";
      c.fillStyle = "#893f2a";
      c.font = "bold 39px serif";
      c.fillText("SAFETY MATCHES", 256, 92);
      c.beginPath();
      c.arc(256, 193, 69, 0, Math.PI * 2);
      c.stroke();
      for (let i = -1; i <= 1; i++) {
        c.fillStyle = "#8c6b3e";
        c.fillRect(245 + i * 30, 161 + Math.abs(i) * 10, 8, 79);
        c.fillStyle = "#923b27";
        c.beginPath();
        c.arc(249 + i * 30, 157 + Math.abs(i) * 10, 9, 0, Math.PI * 2);
        c.fill();
      }
      c.font = "bold 35px serif";
      c.fillStyle = "#893f2a";
      c.fillText("10 MATCHES", 256, 309);
      for (let i = 0; i < 500; i++) {
        c.fillStyle = "rgba(67,46,25,0.12)";
        c.fillRect(rand() * 512, rand() * 384, 1 + rand() * 3, 1);
      }
    });
    const top = this.attach(
      CreatePlane("studio_matchbox_print", { width: 0.101, height: 0.073 }, this.scene),
      detail,
      [0, 0.0165, 0],
      label,
    );
    top.rotation.set(Math.PI / 2, Math.PI / 2, 0);
    const hit = this.box(
      detail,
      "matchbox_pickup_volume",
      [0.16, 0.065, 0.12],
      [0, 0.012, 0],
      this.paper,
    );
    hit.visibility = 0;
  }

  private buildLetters(): void {
    const tie = this.scene.getMeshByName("letters_string");
    if (!tie) return;
    tie.visibility = 0;
    for (let i = 0; i < 5; i++) {
      const sheet = this.scene.getMeshByName(`letter_${i}`);
      if (sheet) sheet.material = this.paper;
    }
    const root = new TransformNode("studio_letters_detail", this.scene);
    root.position.copyFrom(tie.getAbsolutePosition());
    root.setParent(tie);
    const envelope = this.label("letters_envelope", 768, 512, (c) => {
      c.fillStyle = "#d0bb91";
      c.fillRect(0, 0, 768, 512);
      c.strokeStyle = "#b9a17d";
      c.lineWidth = 3;
      c.beginPath();
      c.moveTo(0, 0);
      c.lineTo(384, 230);
      c.lineTo(768, 0);
      c.stroke();
      c.fillStyle = "#393e3b";
      c.font = "italic 46px serif";
      c.fillText("Sora", 290, 297);
      c.font = "italic 25px serif";
      c.fillText("Phnom Penh", 288, 347);
      c.strokeStyle = "#596a65";
      c.lineWidth = 6;
      c.strokeRect(650, 38, 78, 98);
      c.beginPath();
      c.arc(632, 130, 51, 0, Math.PI * 2);
      c.stroke();
    });
    const top = this.attach(
      CreatePlane("studio_letter_address", { width: 0.186, height: 0.144 }, this.scene),
      root,
      [0, 0.022, 0],
      envelope,
    );
    top.rotation.set(Math.PI / 2, Math.PI / 2, 0);
    const cotton = this.mat("red_cotton_tie", "#78372f", 0.96);
    this.tube(
      root,
      "letters_cotton_wrap",
      [
        [-0.108, 0.025, 0],
        [0.108, 0.025, 0],
        [0.109, -0.02, 0],
        [-0.108, -0.02, 0],
        [-0.108, 0.025, 0],
      ],
      0.0014,
      cotton,
    );
    this.tube(
      root,
      "letters_cotton_crossing",
      [
        [0, 0.025, -0.085],
        [0, 0.025, 0.085],
        [0, -0.02, 0.085],
        [0, -0.02, -0.085],
        [0, 0.025, -0.085],
      ],
      0.0014,
      cotton,
    );
    this.tube(
      root,
      "letters_cotton_knot",
      [
        [0, 0.027, 0],
        [-0.018, 0.03, -0.01],
        [-0.022, 0.03, 0.009],
        [0.02, 0.03, -0.006],
        [0.018, 0.029, 0.012],
        [0, 0.027, 0],
        [0.026, 0.028, 0.021],
      ],
      0.0013,
      cotton,
    );
  }

  private buildWallSconce(): void {
    const root = new TransformNode("studio_writing_sconce", this.scene);
    root.position.set(-0.06, 1.65, -2.5);
    root.rotation.y = -Math.PI / 2;
    this.cylinder(root, "sconce_rosette", 0.11, 0.012, [0, 0, 0], this.darkBrass).rotation.x =
      Math.PI / 2;
    this.tube(
      root,
      "sconce_gooseneck",
      [
        [0, 0, 0.01],
        [0, 0.02, 0.08],
        [0, 0.015, 0.17],
        [0, -0.025, 0.21],
      ],
      0.009,
      this.brass,
    );
    const shade = this.lathe(
      root,
      "sconce_shade",
      [
        [0.018, 0.02],
        [0.025, 0.008],
        [0.052, -0.055],
        [0.071, -0.074],
        [0.073, -0.083],
        [0.067, -0.084],
        [0.046, -0.06],
        [0.019, 0],
      ],
      [0, -0.02, 0.21],
      this.ceramic,
    );
    shade.rotation.x = 0.22;
    const bulb = this.mat("sconce_bulb", "#f3dfb2", 0.38);
    bulb.emissiveColor.set(0.8, 0.52, 0.23);
    this.cylinder(root, "sconce_bulb", 0.025, 0.04, [0, -0.074, 0.2], bulb);
    this.tube(
      root,
      "sconce_wiring",
      [
        [0, -0.04, 0.007],
        [0, -0.23, 0.007],
        [0.006, -0.38, 0.007],
      ],
      0.0025,
      this.black,
    );
    this.box(root, "sconce_switch", [0.03, 0.05, 0.016], [0.006, -0.39, 0.012], this.ceramic);
  }

  private buildBankersLamp(): void {
    for (const mesh of this.scene.meshes)
      if (/^desk_lamp_(?:base|stem|shade|bulb)/.test(mesh.name)) mesh.setEnabled(false);
    const root = new TransformNode("studio_bankers_lamp", this.scene);
    root.position.set(-2.05, 0.9, -0.77);
    this.lathe(
      root,
      "banker_weighted_base",
      [
        [0, 0],
        [0.085, 0],
        [0.09, 0.009],
        [0.081, 0.023],
        [0.053, 0.032],
        [0.025, 0.035],
      ],
      [0, 0, 0],
      this.brass,
    );
    this.cylinder(root, "banker_column", 0.018, 0.25, [0, 0.16, 0], this.brass);
    this.ring(root, "banker_base_collar", 0.036, 0.006, [0, 0.041, 0], this.darkBrass, false);
    this.tube(
      root,
      "banker_shade_bracket",
      [
        [0, 0.27, 0],
        [0, 0.31, 0.015],
        [0, 0.31, 0.07],
      ],
      0.008,
      this.brass,
    );
    const green = this.mat("banker_green_glass", "#28593e", 0.2);
    green.clearCoat.isEnabled = true;
    green.clearCoat.intensity = 0.8;
    green.clearCoat.roughness = 0.13;
    const positions: number[] = [],
      indices: number[] = [],
      normals: number[] = [],
      uvs: number[] = [];
    for (let i = 0; i <= 32; i++) {
      const a = (i / 32) * Math.PI;
      for (const x of [-0.16, 0.16]) {
        positions.push(x, 0.31 + Math.sin(a) * 0.075, 0.07 + Math.cos(a) * 0.075);
        uvs.push(x < 0 ? 0 : 1, i / 32);
      }
      if (i < 32) {
        const k = i * 2;
        indices.push(k, k + 1, k + 3, k, k + 3, k + 2);
      }
    }
    VertexData.ComputeNormals(positions, indices, normals);
    const data = new VertexData();
    data.positions = positions;
    data.indices = indices;
    data.normals = normals;
    data.uvs = uvs;
    const shade = new Mesh("studio_banker_glass_shade", this.scene);
    data.applyToMesh(shade);
    green.backFaceCulling = false;
    this.attach(shade, root, [0, 0, 0], green);
    for (const x of [-0.16, 0.16]) {
      const path: number[][] = [];
      for (let i = 0; i <= 24; i++) {
        const a = (i / 24) * Math.PI;
        path.push([x, 0.31 + Math.sin(a) * 0.075, 0.07 + Math.cos(a) * 0.075]);
      }
      this.tube(root, "shade_brass_binding", path, 0.0025, this.brass);
    }
    this.tube(
      root,
      "lamp_braided_lead",
      [
        [0, 0.013, -0.06],
        [0.09, 0.009, -0.13],
        [0.16, 0.003, -0.17],
        [0.18, -0.35, -0.18],
        [0.2, -0.8, -0.16],
      ],
      0.003,
      this.black,
    );
  }

  private buildWorkingDetails(): void {
    // A ruler with engraved divisions, pen holder and stained porcelain cup.
    const ruler = new TransformNode("studio_drafting_ruler", this.scene);
    ruler.position.set(-3.38, 0.965, -1.03);
    ruler.rotation.y = -0.14;
    this.box(ruler, "ruler", [0.31, 0.003, 0.027], [0, 0, 0], this.drawerWood);
    for (let i = 0; i <= 30; i++)
      this.box(
        ruler,
        "ruler_engraving",
        [0.00065, 0.0003, i % 5 === 0 ? 0.014 : 0.007],
        [-0.15 + i * 0.01, 0.0017, -0.004],
        this.black,
      );
    const cup = new TransformNode("studio_brush_cup", this.scene);
    cup.position.set(-0.22, 0.78, -1.92);
    this.lathe(
      cup,
      "brush_pot",
      [
        [0.026, 0],
        [0.03, 0.008],
        [0.034, 0.082],
        [0.036, 0.088],
        [0.032, 0.09],
        [0.029, 0.016],
      ],
      [0, 0, 0],
      this.ceramic,
    );
    this.ring(cup, "brush_pot_ink_stain", 0.065, 0.002, [0, 0.083, 0], this.black, false);
    for (let i = 0; i < 4; i++) {
      const pen = this.cylinder(
        cup,
        "wooden_dip_pen",
        0.004,
        0.17,
        [(i - 1.5) * 0.009, 0.12, 0],
        i % 2 ? this.walnut : this.darkBrass,
      );
      pen.rotation.z = (i - 1.5) * 0.13;
    }
    // Paper edges, string and wax distinguish correspondence from a flat white block.
    for (let i = 0; i < 4; i++) {
      const envelope = this.box(
        null,
        "desk_envelope",
        [0.12, 0.0015, 0.08],
        [-0.23 + i * 0.002, 0.783 + i * 0.002, -2.82 + i * 0.003],
        this.paper,
      );
      envelope.rotation.y = 0.08;
    }
    this.tube(
      null,
      "envelope_fold",
      [
        [-0.29, 0.791, -2.85],
        [-0.23, 0.791, -2.81],
        [-0.17, 0.791, -2.85],
      ],
      0.0005,
      this.drawerWood,
    );
    // Grounding details: old surface wiring, skirting nail heads and rug fringe.
    this.tube(
      null,
      "door_surface_wiring",
      [
        [-5.94, 0.22, -2.99],
        [-5.94, 2.76, -2.99],
        [-5.94, 2.76, -4.72],
      ],
      0.004,
      this.darkBrass,
    );
    const switchRoot = new TransformNode("studio_door_switch", this.scene);
    switchRoot.position.set(-5.945, 1.22, -3.02);
    switchRoot.rotation.y = Math.PI / 2;
    this.slab(switchRoot, "bakelite_switch_plate", 0.075, 0.11, 0.012, [0, 0, 0], this.black);
    this.cylinder(
      switchRoot,
      "switch_toggle",
      0.017,
      0.023,
      [0, 0.006, 0.018],
      this.ceramic,
    ).rotation.x = 0.6;
    for (const z of [-1.71, -3.49])
      for (let i = 0; i < 36; i++) {
        const x = -2.03 - i * 0.06;
        this.tube(
          null,
          "rug_cotton_fringe",
          [
            [x, 0.007, z],
            [x + 0.006, 0.004, z + (z > -2 ? 0.045 : -0.045)],
          ],
          0.0015,
          this.paper,
        );
      }
    for (let i = 0; i < 7; i++) {
      const nail = this.cylinder(
        null,
        "skirting_nail",
        0.004,
        0.002,
        [-0.023, 0.08, -0.6 - i * 0.64],
        this.darkBrass,
      );
      nail.rotation.z = Math.PI / 2;
    }
  }
}
