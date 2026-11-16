import { TelephoneCord } from "@/player/TelephoneCord";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { VertexData } from "@babylonjs/core/Meshes/mesh.vertexData";
import { CreateBox } from "@babylonjs/core/Meshes/Builders/boxBuilder";
import { CreateCylinder } from "@babylonjs/core/Meshes/Builders/cylinderBuilder";
import { CreateTube } from "@babylonjs/core/Meshes/Builders/tubeBuilder";
import { CreatePlane } from "@babylonjs/core/Meshes/Builders/planeBuilder";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { Scene } from "@babylonjs/core/scene";
import type { Area } from "@/core/areaLoader";
import { mergeStaticMeshes } from "@/render/staticBatcher";
import { seededRandom } from "@/audio/synth";

/** Close-range studio craftsmanship. Existing anchors, colliders and story IDs remain authoritative. */
export class StudioDetails {
  /** How far the drawer pulls out: two thirds of its 0.42 m depth, so it stays on its runners. */
  readonly drawerTravel = 0.3;
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
  private cord!: TelephoneCord;

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

  /**
   * The same rotary wall telephone that hangs in the village house's hall
   * (`WallTelephone`), so the instrument Sora answers in Phnom Penh is the one
   * she meets again at the funeral house.
   */
  /**
   * The telephone is modelled in Blender (tools/areas/ep1_area_studio.py): a French
   * magneto wall set with its earpiece on the switch hook. Here: the cloth cord from
   * the case to the earpiece, which follows Sora's hand during the call, and one
   * invisible target over the whole instrument so the gaps round it still count.
   */
  private buildPhone(anchor: TransformNode): void {
    const terminal = this.scene.getTransformNodeByName("telephone_cord_terminal");
    const rest = this.scene.getTransformNodeByName("telephone_cord_rest");
    if (!terminal || !rest) throw new Error("[Studio] telephone cord anchors missing");
    const cord = this.mat("telephone_cloth_cord", "#2c2620", 0.85);
    this.cord = new TelephoneCord(this.scene, "studio_phone_cord", terminal, rest, cord, 0.0035);
    anchor.computeWorldMatrix(true);
    const { min, max } = anchor.getHierarchyBoundingVectors(true);
    const size = max.subtract(min);
    const hit = CreateBox(
      "phone_pickup_volume",
      { width: size.x + 0.04, height: size.y + 0.04, depth: size.z + 0.04 },
      this.scene,
    );
    hit.position.copyFrom(Vector3.Center(min, max));
    hit.visibility = 0;
    hit.setParent(anchor);
  }

  updateTelephoneCord(heldEnd: Vector3 | null = null): void {
    this.cord.update(heldEnd);
  }

  private buildDrawer(drawer: TransformNode): void {
    if (drawer instanceof Mesh) drawer.visibility = 0;
    this.scene.getMeshByName("drawer_knob")?.setEnabled(false);
    // The case the drawer runs in, hung under the desk top: without it the open
    // drawer had nothing round or under it and seemed to float beside the desk.
    const front = drawer.getAbsolutePosition();
    const at = (x: number, y: number, z: number) => [front.x + x, front.y + y, front.z + z];
    this.box(null, "drawer_case_floor", [0.46, 0.014, 0.53], at(0.24, -0.059, 0), this.walnut);
    for (const z of [-0.258, 0.258]) {
      this.box(null, "drawer_case_side", [0.46, 0.115, 0.014], at(0.24, -0.002, z), this.walnut);
      // Hardwood runners the drawer's sides slide on.
      this.box(
        null,
        "drawer_case_runner",
        [0.44, 0.012, 0.02],
        at(0.24, -0.046, z * 0.93),
        this.drawerWood,
      );
    }
    this.box(null, "drawer_case_back", [0.014, 0.115, 0.53], at(0.465, -0.002, 0), this.walnut);
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
    // Near the front of the drawer, so it is in plain sight once the drawer is open.
    box.setAbsolutePosition(new Vector3(-0.55, 0.65, -2.63));
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
    // Brought forward with the matchbox, to where the drawer opens.
    for (const node of [
      tie,
      ...[0, 1, 2, 3, 4].map((i) => this.scene.getMeshByName(`letter_${i}`)),
    ])
      node?.setAbsolutePosition(node.getAbsolutePosition().add(new Vector3(-0.08, 0, 0)));
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
}
