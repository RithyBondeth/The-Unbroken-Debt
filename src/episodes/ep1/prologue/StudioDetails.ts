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
    this.buildSketchbook();
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

  /**
   * What Sora takes is kept out of the bake (bake_studio_lightmap.py, TAKEN), so taking
   * it leaves no dark print behind. Each instead gets a soft contact shadow of its own,
   * parented to it so it goes when the thing does, and an invisible box a few
   * centimetres bigger than it all round, so one press of E takes it from any angle.
   */
  groundPickups(): void {
    const groups: {
      owner: TransformNode | null;
      others: TransformNode[];
      margin: number;
      /** Supporting surface height (floor/table/krama/drawer top) so the contact shadow is never buried. */
      supportY?: number;
      /** Optional mesh-name filter so overhanging straps/ribbons don't skew the seated contact footprint. */
      skipShadow?: RegExp;
      /** Subtle directional shadow offset in world XZ (e.g. away from an overhead wall sconce). */
      offsetX?: number;
      offsetZ?: number;
    }[] = [
      {
        owner: this.node("interact_satchel"),
        others: [],
        margin: 0.06,
        supportY: 0.582,
        skipShadow: /shoulder_strap/i,
      },
      {
        owner: this.node("interact_sketchbook"),
        others: [],
        margin: 0.07,
        supportY: 0.7812,
        skipShadow: /bookmark|pencil/i,
        offsetX: -0.012,
      },
      {
        owner: this.node("matchbox"),
        others: [],
        margin: 0,
        supportY: 0.6334,
      },
      {
        owner: this.node("letters_string"),
        others: [0, 1, 2, 3, 4].flatMap((i) => this.node(`letter_${i}`) ?? []),
        // No bigger box: the bundle is large, and one would cover the matchbox beside it.
        margin: 0,
        supportY: 0.6334,
      },
    ];
    for (const {
      owner,
      others,
      margin,
      supportY,
      skipShadow,
      offsetX = 0,
      offsetZ = 0,
    } of groups) {
      if (!owner) continue;
      const parts = [owner, ...others];
      const { min, max } = visibleBounds(parts);
      if (!Number.isFinite(min.x)) continue;
      const size = max.subtract(min);
      const centre = Vector3.Center(min, max);
      // Match the item's horizontal yaw so angled props (like the satchel on the bed) get a fitted shadow.
      const world = owner.getWorldMatrix();
      const forward = Vector3.TransformNormal(Vector3.Forward(), world);
      let yaw = 0;
      if (Math.hypot(forward.x, forward.z) > 0.25) {
        yaw = Math.atan2(forward.x, forward.z);
      } else {
        const right = Vector3.TransformNormal(Vector3.Right(), world);
        if (Math.hypot(right.x, right.z) > 0.25) yaw = Math.atan2(-right.z, right.x);
      }
      const cos = Math.cos(yaw);
      const sin = Math.sin(yaw);
      let lxMin = Infinity,
        lxMax = -Infinity,
        lzMin = Infinity,
        lzMax = -Infinity;
      for (const part of parts) {
        const meshes = [
          ...("getTotalVertices" in part ? [part as Mesh] : []),
          ...part.getChildMeshes(false),
        ];
        for (const mesh of meshes) {
          if (mesh.visibility <= 0 || !mesh.isVisible || mesh.getTotalVertices() === 0) continue;
          if (skipShadow && skipShadow.test(mesh.name)) continue;
          const corners = mesh.getBoundingInfo().boundingBox.vectorsWorld;
          for (const v of corners) {
            const dx = v.x - centre.x;
            const dz = v.z - centre.z;
            const rx = dx * cos - dz * sin;
            const rz = dx * sin + dz * cos;
            if (rx < lxMin) lxMin = rx;
            if (rx > lxMax) lxMax = rx;
            if (rz < lzMin) lzMin = rz;
            if (rz > lzMax) lzMax = rz;
          }
        }
      }
      // Recentre the contact shadow on the actual seated footprint (important when overhanging straps exist).
      const localCx = Number.isFinite(lxMin) ? (lxMin + lxMax) / 2 : 0;
      const localCz = Number.isFinite(lzMin) ? (lzMin + lzMax) / 2 : 0;
      const shadowCx = centre.x + localCx * cos + localCz * sin + offsetX;
      const shadowCz = centre.z - localCx * sin + localCz * cos + offsetZ;
      const shadowW = Number.isFinite(lxMin) ? (lxMax - lxMin) * 1.24 + 0.042 : size.x * 1.28;
      const shadowD = Number.isFinite(lzMin) ? (lzMax - lzMin) * 1.24 + 0.042 : size.z * 1.28;
      const shadowY = supportY !== undefined ? supportY : min.y + 0.0016;
      const shadow = CreatePlane(
        `${owner.name}_contact_shadow`,
        { width: shadowW, height: shadowD },
        this.scene,
      );
      shadow.rotation.set(Math.PI / 2, yaw, 0);
      shadow.position.set(shadowCx, shadowY, shadowCz);
      shadow.material = this.contactShadow();
      shadow.isPickable = false;
      shadow.receiveShadows = false;
      shadow.setParent(owner);
      if (margin > 0) {
        const hit = CreateBox(
          `${owner.name}_pickup_volume`,
          {
            width: size.x + margin * 2,
            height: size.y + margin * 1.5,
            depth: size.z + margin * 2,
          },
          this.scene,
        );
        hit.position.set(centre.x, centre.y + margin * 0.25, centre.z);
        hit.visibility = 0;
        hit.setParent(owner);
      }
    }

    // The hurricane lantern hangs on a brass hook against the north timber partition wall (Z = -6.12);
    // add a soft vertical wall contact shadow parented to `interact_lamp` so it lifts cleanly with the lamp.
    const lamp = this.node("interact_lamp");
    if (lamp) {
      const { min, max } = visibleBounds([lamp]);
      if (Number.isFinite(min.x)) {
        const size = max.subtract(min);
        const centre = Vector3.Center(min, max);
        const wallShadow = CreatePlane(
          "interact_lamp_contact_shadow",
          { width: size.x * 1.7 + 0.04, height: size.y * 1.25 + 0.04 },
          this.scene,
        );
        wallShadow.position.set(centre.x, centre.y, -6.1225);
        wallShadow.material = this.contactShadow(0.62);
        wallShadow.isPickable = false;
        wallShadow.receiveShadows = false;
        wallShadow.setParent(lamp);
      }
    }
  }

  private shadowMaterials = new Map<number, PBRMaterial>();

  /**
   * Soft rounded-rectangle ambient occlusion shadow with explicit PBRMATERIAL_ALPHABLEND
   * (without transparencyMode, Babylon PBRMaterial enables ALPHATEST and discards feathered
   * shadow edges below 0.5 alpha).
   */
  private contactShadow(alpha = 0.84): PBRMaterial {
    const existing = this.shadowMaterials.get(alpha);
    if (existing) return existing;
    const size = 128;
    const tex = new DynamicTexture(`T_studio_contact_shadow_${alpha}`, size, this.scene, true);
    const c = tex.getContext() as unknown as CanvasRenderingContext2D;
    c.clearRect(0, 0, size, size);
    const roundedRect = (x: number, y: number, w: number, h: number, r: number) => {
      const rr = Math.min(r, w / 2, h / 2);
      c.beginPath();
      c.moveTo(x + rr, y);
      c.lineTo(x + w - rr, y);
      c.quadraticCurveTo(x + w, y, x + w, y + rr);
      c.lineTo(x + w, y + h - rr);
      c.quadraticCurveTo(x + w, y + h, x + w - rr, y + h);
      c.lineTo(x + rr, y + h);
      c.quadraticCurveTo(x, y + h, x, y + h - rr);
      c.lineTo(x, y + rr);
      c.quadraticCurveTo(x, y, x + rr, y);
      c.closePath();
    };
    // 1) Soft feathered outer penumbra around all four sides and corners of the item.
    const layers = 16;
    for (let i = 0; i < layers; i++) {
      const t = i / (layers - 1);
      const inset = 3 + t * 23;
      const w = size - inset * 2;
      const radius = 24 * (1 - t * 0.45);
      const stepAlpha = 0.04 + 0.14 * t * t;
      c.fillStyle = `rgba(0,0,0,${stepAlpha.toFixed(3)})`;
      roundedRect(inset, inset, w, w, radius);
      c.fill();
    }
    // 2) Tight dark contact crease directly under the item perimeter so it sits heavy on the surface.
    c.fillStyle = "rgba(0,0,0,0.86)";
    roundedRect(22, 22, size - 44, size - 44, 10);
    c.fill();
    tex.hasAlpha = true;
    tex.getAlphaFromRGB = false;
    tex.update();
    const mat = new PBRMaterial(`M_studio_contact_shadow_${alpha}`, this.scene);
    mat.albedoColor = Color3.Black();
    mat.emissiveColor = Color3.Black();
    mat.unlit = true;
    mat.disableLighting = true;
    mat.opacityTexture = tex;
    mat.alpha = alpha;
    mat.transparencyMode = PBRMaterial.PBRMATERIAL_ALPHABLEND;
    mat.backFaceCulling = false;
    mat.disableDepthWrite = true;
    mat.zOffset = -2;
    this.shadowMaterials.set(alpha, mat);
    return mat;
  }

  private node(name: string): TransformNode | null {
    return this.scene.getMeshByName(name) ?? this.scene.getTransformNodeByName(name);
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

  /**
   * Upgrades Sora's 1932 artist sketchbook (`interact_sketchbook`) from flat untextured
   * boards to a rich quarter-bound Phnom Penh field book: woven charcoal buckram linen,
   * pebbled oxblood leather spine with raised bands & gold fillet trim, aged cotton-rag
   * handwritten bookplate, striated watercolor-paper edges, patinated brass corner guards,
   * ribbed crimson elastic strap, silk bookmark ribbon, and a cedar sketching pencil.
   */
  private buildSketchbook(): void {
    const sk = this.node("interact_sketchbook");
    if (!sk) return;
    sk.computeWorldMatrix(true);

    // 1. Woven charcoal-slate buckram bookcloth with thread cross-weave, worn edges & blind-debossed frame
    const clothMat = this.label("sketchbook_buckram", 512, 512, (c) => {
      const rand = seededRandom(19321);
      c.fillStyle = "#1c211e";
      c.fillRect(0, 0, 512, 512);
      // Horizontal and vertical linen bookcloth threads
      for (let y = 0; y < 512; y += 2) {
        c.fillStyle = y % 4 === 0 ? "rgba(255,248,232,0.045)" : "rgba(0,0,0,0.12)";
        c.fillRect(0, y, 512, 1);
      }
      for (let x = 0; x < 512; x += 2) {
        c.fillStyle = x % 4 === 0 ? "rgba(240,234,215,0.04)" : "rgba(0,0,0,0.1)";
        c.fillRect(x, 0, 1, 512);
      }
      // Subtle organic cloth mottling and artist handling wear near fore-edge
      for (let i = 0; i < 2400; i++) {
        const x = rand() * 512;
        const y = rand() * 512;
        c.fillStyle =
          i % 3 === 0
            ? `rgba(74, 82, 72, ${(0.03 + rand() * 0.05).toFixed(3)})`
            : `rgba(8, 10, 9, ${(0.04 + rand() * 0.07).toFixed(3)})`;
        c.fillRect(x, y, 1 + rand() * 4, 1 + rand() * 3);
      }
      // Worn lighter rub around outer edges & dark vignette shadow into the binding hinge
      const edge = c.createRadialGradient(270, 256, 120, 256, 256, 355);
      edge.addColorStop(0, "rgba(42,48,43,0.12)");
      edge.addColorStop(0.75, "rgba(18,22,19,0.06)");
      edge.addColorStop(1, "rgba(6,8,7,0.42)");
      c.fillStyle = edge;
      c.fillRect(0, 0, 512, 512);
      // Blind-debossed double tooling frame on the linen cover
      c.strokeStyle = "rgba(6, 8, 7, 0.72)";
      c.lineWidth = 3;
      c.strokeRect(20, 22, 472, 468);
      c.strokeStyle = "rgba(190, 178, 148, 0.14)";
      c.lineWidth = 1.5;
      c.strokeRect(24, 26, 464, 460);
      c.strokeStyle = "rgba(6, 8, 7, 0.45)";
      c.lineWidth = 1.5;
      c.strokeRect(32, 34, 448, 444);
      // Subtle faded charcoal smudge near lower-right fore-edge from artist's thumb
      const thumb = c.createRadialGradient(420, 385, 6, 420, 385, 56);
      thumb.addColorStop(0, "rgba(12, 13, 12, 0.28)");
      thumb.addColorStop(1, "rgba(12, 13, 12, 0)");
      c.fillStyle = thumb;
      c.fillRect(350, 320, 140, 140);
    });
    clothMat.roughness = 0.88;

    // 2. Pebbled dark chestnut/oxblood morocco leather for the quarter-binding & spine
    const leatherMat = this.label("sketchbook_morocco", 256, 512, (c) => {
      const rand = seededRandom(19322);
      c.fillStyle = "#3a1e15";
      c.fillRect(0, 0, 256, 512);
      // Natural morocco pebble grain + subtle vertical hinge creases
      for (let i = 0; i < 3600; i++) {
        const x = rand() * 256;
        const y = rand() * 512;
        const r = 1 + rand() * 2.4;
        c.fillStyle =
          i % 2 === 0
            ? `rgba(88, 52, 34, ${(0.06 + rand() * 0.1).toFixed(3)})`
            : `rgba(18, 8, 5, ${(0.08 + rand() * 0.14).toFixed(3)})`;
        c.beginPath();
        c.arc(x, y, r, 0, Math.PI * 2);
        c.fill();
      }
      // Hinge groove darkening along the spine joint
      const crease = c.createLinearGradient(0, 0, 256, 0);
      crease.addColorStop(0, "rgba(15, 7, 4, 0.48)");
      crease.addColorStop(0.22, "rgba(92, 54, 34, 0.12)");
      crease.addColorStop(0.75, "rgba(20, 10, 6, 0.22)");
      crease.addColorStop(1, "rgba(10, 5, 3, 0.52)");
      c.fillStyle = crease;
      c.fillRect(0, 0, 256, 512);
    });
    leatherMat.roughness = 0.56;
    leatherMat.clearCoat.isEnabled = true;
    leatherMat.clearCoat.intensity = 0.16;
    leatherMat.clearCoat.roughness = 0.52;

    // 3. Striated deckled cream watercolor-paper edges for the page block
    const pagesMat = this.label("sketchbook_page_block", 256, 128, (c) => {
      const rand = seededRandom(19323);
      c.fillStyle = "#c4b28f";
      c.fillRect(0, 0, 256, 128);
      for (let y = 0; y < 128; y += 2) {
        const dark = 0.08 + rand() * 0.22;
        c.fillStyle =
          y % 8 === 0
            ? `rgba(62, 46, 28, ${(dark + 0.14).toFixed(3)})`
            : `rgba(88, 68, 42, ${dark.toFixed(3)})`;
        c.fillRect(0, y, 256, 1);
      }
      for (let i = 0; i < 450; i++) {
        c.fillStyle = `rgba(90, 66, 38, ${(0.04 + rand() * 0.08).toFixed(3)})`;
        c.fillRect(rand() * 256, rand() * 128, 2 + rand() * 14, 1);
      }
    });
    pagesMat.roughness = 0.94;

    // 4. Aged cotton-rag cover bookplate with antique sepia border & handwritten Phnom Penh title
    //    Warm parchment (#baa681) never blows out to flat white under the writing sconce or rim highlight.
    const bookplateMat = this.label("sketchbook_bookplate", 512, 384, (c) => {
      const rand = seededRandom(19324);
      c.fillStyle = "#bca882";
      c.fillRect(0, 0, 512, 384);
      // Warm tea-stained paper edge darkening
      const vig = c.createRadialGradient(256, 192, 95, 256, 192, 315);
      vig.addColorStop(0, "rgba(218, 202, 168, 0.22)");
      vig.addColorStop(0.75, "rgba(155, 132, 94, 0.12)");
      vig.addColorStop(1, "rgba(74, 56, 34, 0.45)");
      c.fillStyle = vig;
      c.fillRect(0, 0, 512, 384);
      // Paper fibers and faint foxing specks
      for (let i = 0; i < 900; i++) {
        c.fillStyle =
          i % 7 === 0
            ? `rgba(112, 78, 42, ${(0.08 + rand() * 0.12).toFixed(3)})`
            : `rgba(70, 52, 32, ${(0.04 + rand() * 0.08).toFixed(3)})`;
        c.fillRect(rand() * 512, rand() * 384, 1 + rand() * 3, 1 + rand() * 2);
      }
      // Double antique sepia ink border with tiny inset corner ticks
      c.strokeStyle = "#3f2e1f";
      c.lineWidth = 4;
      c.strokeRect(18, 18, 476, 348);
      c.lineWidth = 1.6;
      c.strokeRect(28, 28, 456, 328);
      for (const [cx, cy] of [
        [28, 28],
        [484, 28],
        [28, 356],
        [484, 356],
      ]) {
        c.fillStyle = "#3f2e1f";
        c.beginPath();
        c.arc(cx, cy, 4, 0, Math.PI * 2);
        c.fill();
      }
      // Subtle ruled pencil guidelines + sepia calligraphy
      c.strokeStyle = "rgba(63, 46, 31, 0.25)";
      c.lineWidth = 1.2;
      c.beginPath();
      c.moveTo(76, 178);
      c.lineTo(436, 178);
      c.moveTo(116, 250);
      c.lineTo(396, 250);
      c.stroke();

      c.textAlign = "center";
      c.fillStyle = "#2b2016";
      c.font = "italic 62px Georgia, serif";
      c.fillText("Sora", 256, 148);
      // Small hand-drawn lotus/diamond divider
      c.fillStyle = "#5c3b24";
      c.beginPath();
      c.moveTo(256, 169);
      c.lineTo(266, 178);
      c.lineTo(256, 187);
      c.lineTo(246, 178);
      c.closePath();
      c.fill();
      c.fillStyle = "#3a2b1d";
      c.font = "italic 30px Georgia, serif";
      c.fillText("Croquis · Phnom Penh", 256, 232);
      c.font = "24px Georgia, serif";
      c.fillStyle = "#4e3b28";
      c.fillText("1932", 256, 304);
    });
    bookplateMat.roughness = 0.94;

    // Re-skin existing GLB sketchbook meshes & hide the flat glowing blank label box
    for (const child of sk.getChildMeshes(false)) {
      if (/board_(up|low)/.test(child.name)) child.material = clothMat;
      else if (/quarter|spine/.test(child.name)) child.material = leatherMat;
      else if (/pages/.test(child.name)) child.material = pagesMat;
      else if (/label/.test(child.name)) child.visibility = 0;
    }

    // World-aligned detail root at the sketchbook's base centre (-0.30, 0.78, -2.16):
    // lx = -0.12 (near desk edge) .. +0.12 (wall edge)
    // ly = 0.000 (desk) .. +0.024 (front board top)
    // lz = -0.16 (north fore-edge) .. +0.16 (south spine)
    const root = new TransformNode("studio_sketchbook_detail", this.scene);
    root.position.copyFrom(sk.getAbsolutePosition());
    root.setParent(sk);

    // Clean UV-mapped linen top cover face (covers cloth portion lz = -0.158..+0.118)
    const coverTop = this.attach(
      CreatePlane("sketchbook_cover_cloth_top", { width: 0.276, height: 0.236 }, this.scene),
      root,
      [0, 0.02435, -0.02],
      clothMat,
    );
    coverTop.rotation.set(Math.PI / 2, Math.PI / 2, 0);

    // Slightly recessed aged bookplate backing & printed cotton-rag label
    const plateBacking = this.mat("sketchbook_plate_edge", "#221811", 0.9);
    this.box(
      root,
      "sketchbook_bookplate_rim",
      [0.074, 0.0006, 0.094],
      [0, 0.0245, -0.056],
      plateBacking,
    );
    const plate = this.attach(
      CreatePlane("sketchbook_bookplate_print", { width: 0.088, height: 0.068 }, this.scene),
      root,
      [0, 0.02495, -0.056],
      bookplateMat,
    );
    plate.rotation.set(Math.PI / 2, Math.PI / 2, 0);

    // Rounded leather spine cap + 4 raised leather spine bands + antique gold-leaf fillet trim
    const spineCap = this.cylinder(
      root,
      "sketchbook_spine_round",
      0.0252,
      0.241,
      [0, 0.012, 0.157],
      leatherMat,
    );
    spineCap.rotation.z = Math.PI / 2;
    for (const bx of [-0.084, -0.028, 0.028, 0.084]) {
      const band = this.cylinder(
        root,
        "sketchbook_spine_band",
        0.0276,
        0.0065,
        [bx, 0.012, 0.158],
        leatherMat,
      );
      band.rotation.z = Math.PI / 2;
    }
    const gilt = this.mat("sketchbook_gilt_fillet", "#9e8145", 0.42, 0.72);
    this.box(root, "sketchbook_gold_fillet_a", [0.237, 0.0007, 0.0018], [0, 0.02455, 0.1185], gilt);
    this.box(root, "sketchbook_gold_fillet_b", [0.237, 0.0007, 0.001], [0, 0.02455, 0.123], gilt);

    // Woven crimson-and-gold cloth headbands tucked at head & tail of the spine
    const crimson = this.mat("sketchbook_crimson_cloth", "#5a1b1b", 0.86);
    for (const sx of [-0.117, 0.117]) {
      this.box(root, "sketchbook_headband", [0.004, 0.017, 0.008], [sx, 0.012, 0.152], crimson);
    }

    // Two patinated antique brass corner protectors gripping the outer fore-edge corners
    for (const sx of [-1, 1]) {
      const ex = sx * 0.119;
      const fx = sx * 0.107;
      this.box(
        root,
        "sketchbook_corner_a",
        [0.024, 0.0018, 0.006],
        [fx, 0.0248, -0.1575],
        this.brass,
      );
      this.box(
        root,
        "sketchbook_corner_b",
        [0.006, 0.0018, 0.024],
        [ex - sx * 0.002, 0.0248, -0.148],
        this.brass,
      );
      this.box(
        root,
        "sketchbook_corner_edge_x",
        [0.024, 0.0055, 0.002],
        [fx, 0.0228, -0.1605],
        this.brass,
      );
      this.box(
        root,
        "sketchbook_corner_edge_z",
        [0.002, 0.0055, 0.024],
        [ex + sx * 0.0015, 0.0228, -0.148],
        this.brass,
      );
    }

    // Ribbed dark-burgundy woven elastic closure band wrapped around the fore-edge side
    const elastic = this.mat("sketchbook_elastic_band", "#3a1719", 0.9);
    const bandZ = -0.126;
    this.box(root, "sketchbook_elastic_top", [0.243, 0.0018, 0.014], [0, 0.0252, bandZ], elastic);
    for (const sx of [-0.121, 0.121]) {
      this.box(
        root,
        "sketchbook_elastic_side",
        [0.002, 0.025, 0.014],
        [sx, 0.0125, bandZ],
        elastic,
      );
    }

    // Crimson silk bookmark ribbon emerging from the bottom page edge onto the rosewood desk
    const silk = this.mat("sketchbook_bookmark_silk", "#6a1a1c", 0.52);
    silk.backFaceCulling = false;
    this.tube(
      root,
      "sketchbook_bookmark_ribbon",
      [
        [-0.114, 0.011, -0.032],
        [-0.124, 0.009, -0.034],
        [-0.136, 0.003, -0.042],
        [-0.152, 0.0018, -0.048],
        [-0.166, 0.0016, -0.042],
      ],
      0.0034,
      silk,
    );

    // Worn hexagonal artist's graphite sketching pencil tucked cleanly under the elastic band
    const pencilRoot = new TransformNode("studio_sketchbook_pencil", this.scene);
    pencilRoot.parent = root;
    pencilRoot.position.set(0.006, 0.0282, -0.112);
    pencilRoot.rotation.set(0, -0.06, Math.PI / 2);
    const cedarVarnish = this.mat("sketchbook_pencil_barrel", "#522518", 0.42);
    const rawCedar = this.mat("sketchbook_pencil_wood", "#b58b5b", 0.84);
    const graphite = this.mat("sketchbook_pencil_lead", "#1c1c1e", 0.34, 0.35);
    const eraser = this.mat("sketchbook_pencil_eraser", "#9c625b", 0.9);
    this.cylinder(pencilRoot, "sketchbook_pencil_shaft", 0.0074, 0.145, [0, 0, 0], cedarVarnish);
    this.cylinder(
      pencilRoot,
      "sketchbook_pencil_cone",
      0.0072,
      0.019,
      [0, 0.082, 0],
      rawCedar,
      0.0018,
    );
    this.cylinder(
      pencilRoot,
      "sketchbook_pencil_tip",
      0.0018,
      0.0055,
      [0, 0.094, 0],
      graphite,
      0.0004,
    );
    this.cylinder(
      pencilRoot,
      "sketchbook_pencil_ferrule",
      0.0077,
      0.013,
      [0, -0.079, 0],
      this.darkBrass,
    );
    this.cylinder(pencilRoot, "sketchbook_pencil_eraser", 0.0068, 0.008, [0, -0.089, 0], eraser);
    this.batchParts(root, pencilRoot);
  }
}

/** World bounds of what can be seen of `nodes` (invisible pickup volumes left out). */
function visibleBounds(nodes: TransformNode[]): { min: Vector3; max: Vector3 } {
  const min = new Vector3(Infinity, Infinity, Infinity);
  const max = new Vector3(-Infinity, -Infinity, -Infinity);
  for (const node of nodes) {
    node.computeWorldMatrix(true);
    const meshes = [
      ...("getTotalVertices" in node ? [node as Mesh] : []),
      ...node.getChildMeshes(false),
    ];
    for (const mesh of meshes) {
      if (mesh.visibility <= 0 || !mesh.isVisible || mesh.getTotalVertices() === 0) continue;
      mesh.computeWorldMatrix(true);
      const box = mesh.getBoundingInfo().boundingBox;
      min.minimizeInPlace(box.minimumWorld);
      max.maximizeInPlace(box.maximumWorld);
    }
  }
  return { min, max };
}
