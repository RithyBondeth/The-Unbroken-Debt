import type { Scene } from "@babylonjs/core/scene";
import type { Area } from "../../../core/AreaLoader";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import { CreateBox } from "@babylonjs/core/Meshes/Builders/boxBuilder";
import { CreateCylinder } from "@babylonjs/core/Meshes/Builders/cylinderBuilder";
import { CreateTorus } from "@babylonjs/core/Meshes/Builders/torusBuilder";
import { CreateSphere } from "@babylonjs/core/Meshes/Builders/sphereBuilder";
import { CreatePlane } from "@babylonjs/core/Meshes/Builders/planeBuilder";
import { CreateTube } from "@babylonjs/core/Meshes/Builders/tubeBuilder";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import { Texture } from "@babylonjs/core/Materials/Textures/texture";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { seededRandom } from "../../../audio/synth";

/** Period props at real scale, with separate moving parts and hollow drawer geometry. */
export class DeskModels {
  readonly compartment: TransformNode;
  readonly panel: TransformNode;
  readonly key: TransformNode;
  readonly desk: TransformNode;
  readonly drawer: TransformNode;
  readonly journal: TransformNode;
  readonly portrait: TransformNode;
  readonly meshes: Mesh[] = [];
  readonly threadMeshes: Mesh[] = [];
  readonly intactThreadMeshes: Mesh[] = [];
  private readonly wood: PBRMaterial;
  private readonly edge: PBRMaterial;
  private readonly brass: PBRMaterial;
  private readonly iron: PBRMaterial;
  private readonly eyes: TransformNode[] = [];
  private readonly lids: Mesh[] = [];
  private readonly northThread: AbstractMesh[] = [];
  private readonly cords: Mesh[] = [];
  private readonly frays: TransformNode[] = [];
  private panelAmount = 0;
  private drawerAmount = 0;
  private eyeAmount = 0;
  private snapTime = 3;
  private broken = false;

  constructor(
    private readonly scene: Scene,
    area: Area,
  ) {
    this.wood = this.mat("teak", "#ffffff", 0.66);
    this.edge = this.mat("endgrain", "#3c2417", 0.6);
    this.brass = this.mat("aged_brass", "#9b7840", 0.52, 0.75);
    this.iron = this.mat("lock_iron", "#242420", 0.68, 0.6);
    this.woodGrain();
    this.compartment = this.root("altar_key_recess", new Vector3(0, 2.5, -21.365));
    this.panel = this.root(
      "altar_hinged_panel",
      new Vector3(-0.235, 0.26, 0.025),
      this.compartment,
    );
    this.key = this.root("sok_desk_key", new Vector3(0, 0.26, 0.031), this.compartment);
    this.buildCompartment();

    // The existing collider is retained; only the visible placeholder desk is replaced.
    for (const mesh of area.container.meshes)
      if (/^sok_desk(?:$|_|\.)/.test(mesh.name)) mesh.setEnabled(false);
    this.desk = this.root("sok_investigation_desk", new Vector3(-5.2, 2.5, -17.1));
    this.drawer = this.root("sok_locking_drawer", Vector3.Zero(), this.desk);
    this.journal = this.root("sok_journal_b", new Vector3(0.01, 0.608, 0.285), this.drawer);
    this.buildDesk();
    this.buildJournal();
    // Sok left his chair pulled aside to the free end of the desk; its carved back
    // must not occlude the drawer or the papers when Sora leans over them from the
    // room, and it must stay clear of the gramophone stand at (-5.4, -15.6).
    const chair = scene.getTransformNodeByName("prop_chinese_armchair");
    if (chair) {
      const at = chair.getAbsolutePosition();
      chair.setAbsolutePosition(new Vector3(-3.95, at.y, -17));
    }

    const photo = area.level.interactables.find((m) => m.name === "interact_portrait");
    if (!photo) throw new Error("[Desk investigation] missing funeral portrait");
    this.portrait = this.root("sok_animated_portrait", photo.position.clone());
    const old = scene.getTransformNodeByName("portrait_sok");
    const authoredFrame = !!old
      ?.getDescendants()
      .some((node) => node.name.startsWith("portrait_floral_surround"));
    // Keep the crafted frame and flowers; only the photograph needs animated eyes.
    if (authoredFrame) photo.node.setEnabled(false);
    else if (old) old.setEnabled(false);
    else photo.node.setEnabled(false);
    this.buildPortrait(authoredFrame);

    const cotton = this.mat("cotton", "#d4cdb7", 1);
    // The exported village combines all four sides into one thread_mesh. Replace
    // that mesh so the north side can actually disappear when the cord snaps.
    const importedThread = area.level.interactables.find((m) => m.name === "interact_thread");
    importedThread?.node.getChildMeshes().forEach((mesh) => mesh.setEnabled(false));
    const corners = [
      new Vector3(4, 2.3, -1),
      new Vector3(-4, 2.3, -1),
      new Vector3(-4, 2.3, -7),
      new Vector3(4, 2.3, -7),
    ];
    for (let i = 0; i < 4; i++) {
      const a = corners[i],
        b = corners[(i + 1) % 4];
      const path = Array.from({ length: 33 }, (_, k) => {
        const t = k / 32,
          point = Vector3.Lerp(a, b, t);
        point.y -= Vector3.Distance(a, b) * 0.03 * Math.sin(t * Math.PI);
        return point;
      });
      const cord = CreateTube(
        `protective_thread_side_${i}`,
        { path, radius: 0.004, tessellation: 8 },
        scene,
      );
      cord.material = cotton;
      this.intactThreadMeshes.push(cord);
      if (i === 2) this.northThread.push(cord);
    }
    for (const side of [-1, 1]) {
      const cord = CreateTube(
        `broken_thread_${side}`,
        {
          path: this.cordPath(side, 0),
          radius: 0.004,
          tessellation: 8,
          updatable: true,
        },
        scene,
      );
      cord.material = cotton;
      cord.setEnabled(false);
      this.cords.push(cord);
      this.threadMeshes.push(cord);
      const end = this.root(`thread_frayed_end_${side}`, Vector3.Zero());
      this.frays.push(end);
      for (let k = 0; k < 5; k++) {
        const fibre = CreateTube(
          `thread_fibre_${side}_${k}`,
          {
            path: [Vector3.Zero(), new Vector3((k - 2) * 0.004, -0.018 - k * 0.005, k * 0.002)],
            radius: 0.0007,
            tessellation: 4,
          },
          scene,
        );
        fibre.parent = end;
        fibre.material = cotton;
        fibre.isPickable = false;
      }
      end.setEnabled(false);
    }
  }

  get drawerReady(): boolean {
    return this.drawerAmount > 0.98;
  }

  restore(compartment: boolean, drawer: boolean, awake: boolean, broken: boolean): void {
    this.panelAmount = Number(compartment);
    this.drawerAmount = Number(drawer);
    this.eyeAmount = Number(awake);
    this.setBroken(broken, true);
    this.update(0, compartment, drawer, awake);
  }

  update(dt: number, compartment: boolean, drawer: boolean, awake: boolean): void {
    const ease = Math.min(1, dt * 5);
    this.panelAmount += (Number(compartment) - this.panelAmount) * ease;
    this.drawerAmount += (Number(drawer) - this.drawerAmount) * ease;
    this.eyeAmount += (Number(awake) - this.eyeAmount) * Math.min(1, dt * 1.8);
    this.panel.rotation.y = -1.75 * this.panelAmount;
    this.drawer.position.z = this.drawerAmount * 0.43;
    for (let k = 0; k < this.eyes.length; k++) {
      this.eyes[k].scaling.y = 0.08 + this.eyeAmount * 0.92;
      this.lids[k].scaling.y = 0.007 * Math.max(0.02, 1 - this.eyeAmount);
      this.lids[k].position.y = 0.0025 * this.eyeAmount;
    }
    if (this.broken && this.snapTime < 3) {
      this.snapTime = Math.min(3, this.snapTime + dt);
      this.poseThread();
    }
  }

  setBroken(broken: boolean, instant = false): void {
    this.broken = broken;
    this.snapTime = instant ? 3 : 0;
    this.northThread.forEach((mesh) => mesh.setEnabled(!broken));
    this.cords.forEach((mesh) => mesh.setEnabled(broken));
    this.frays.forEach((node) => node.setEnabled(broken));
    if (broken) this.poseThread();
  }

  private poseThread(): void {
    for (const [i, side] of [-1, 1].entries()) {
      const path = this.cordPath(side, Math.min(1, this.snapTime / 1.3));
      CreateTube(this.cords[i].name, { path, instance: this.cords[i] }, this.scene);
      this.frays[i].position.copyFrom(path.at(-1)!);
    }
  }

  private cordPath(side: number, drop: number): Vector3[] {
    return Array.from({ length: 25 }, (_, k) => {
      const t = k / 24;
      return new Vector3(
        side * (4 - t * (3.98 - drop * 0.38)),
        2.3 - 0.1 * Math.sin(t * Math.PI) - drop * 0.94 * t ** 2,
        -7 + Math.sin(t * 3) * drop * 0.05,
      );
    });
  }

  private root(name: string, at: Vector3, parent?: TransformNode): TransformNode {
    const root = new TransformNode(name, this.scene);
    root.position.copyFrom(at);
    if (parent) root.parent = parent;
    return root;
  }
  private mat(name: string, hex: string, roughness: number, metallic = 0): PBRMaterial {
    const mat = new PBRMaterial(`M_desk_${name}`, this.scene);
    mat.albedoColor = Color3.FromHexString(hex).toLinearSpace();
    mat.roughness = roughness;
    mat.metallic = metallic;
    mat.maxSimultaneousLights = 8;
    return mat;
  }
  private finish(mesh: Mesh, root: TransformNode, at: number[], mat: PBRMaterial): Mesh {
    mesh.parent = root;
    mesh.position.set(at[0], at[1], at[2]);
    mesh.material = mat;
    this.meshes.push(mesh);
    return mesh;
  }
  private box(
    root: TransformNode,
    name: string,
    size: number[],
    at: number[],
    mat = this.wood,
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
    mat = this.brass,
  ): Mesh {
    return this.finish(
      CreateCylinder(name, { diameter, height, tessellation: 24 }, this.scene),
      root,
      at,
      mat,
    );
  }
  private ring(root: TransformNode, name: string, diameter: number, at: number[]): Mesh {
    const ring = this.finish(
      CreateTorus(name, { diameter, thickness: 0.004, tessellation: 32 }, this.scene),
      root,
      at,
      this.brass,
    );
    ring.rotation.x = Math.PI / 2;
    return ring;
  }
  private screw(root: TransformNode, at: number[]): void {
    const head = this.cylinder(root, "slotted_screw", 0.007, 0.002, at);
    head.rotation.x = Math.PI / 2;
    this.box(
      root,
      "screw_slot",
      [0.004, 0.0008, 0.0008],
      [at[0], at[1], at[2] + 0.0013],
      this.iron,
    );
  }

  private buildCompartment(): void {
    this.box(
      this.compartment,
      "key_recess_shadow",
      [0.46, 0.18, 0.012],
      [0, 0.26, -0.003],
      this.iron,
    );
    for (const x of [-0.245, 0.245])
      this.box(
        this.compartment,
        "altar_recess_stile",
        [0.024, 0.23, 0.055],
        [x, 0.26, 0.012],
        this.edge,
      );
    for (const y of [0.15, 0.37])
      this.box(
        this.compartment,
        "altar_recess_rail",
        [0.51, 0.024, 0.055],
        [0, y, 0.012],
        this.edge,
      );
    this.box(this.panel, "altar_sliding_inset", [0.463, 0.184, 0.025], [0.235, 0, 0]);
    this.box(this.panel, "altar_raised_panel", [0.39, 0.12, 0.012], [0.235, 0, 0.017], this.edge);
    for (const y of [-0.059, 0.059]) {
      this.box(this.panel, "panel_hinge", [0.033, 0.028, 0.004], [0.012, y, 0.016], this.brass);
      this.screw(this.panel, [0.012, y, 0.019]);
    }
    this.ring(this.panel, "altar_pull_ring", 0.027, [0.418, -0.008, 0.029]);
    this.ring(this.key, "key_bow", 0.045, [-0.052, 0, 0]);
    const shaft = this.cylinder(this.key, "key_hollow_shaft", 0.006, 0.095, [0.007, 0, 0]);
    shaft.rotation.z = Math.PI / 2;
    for (const [x, y] of [
      [0.03, -0.01],
      [0.045, -0.014],
      [0.052, -0.008],
    ])
      this.box(this.key, "key_cut_ward", [0.008, Math.abs(y) * 2, 0.006], [x, y, 0], this.brass);
    this.cylinder(
      this.key,
      "key_hanging_peg",
      0.004,
      0.011,
      [-0.052, 0.018, 0],
      this.iron,
    ).rotation.x = Math.PI / 2;
  }

  private buildDesk(): void {
    this.box(this.desk, "desk_top_edge", [1.26, 0.044, 1.05], [0, 0.725, 0], this.edge);
    this.box(this.desk, "desk_top_inset", [1.2, 0.018, 0.99], [0, 0.756, 0]);
    for (const x of [-0.545, 0.545]) {
      for (const z of [-0.43, 0.43]) {
        this.box(this.desk, "desk_tapered_leg", [0.06, 0.61, 0.06], [x, 0.33, z]);
        this.box(this.desk, "desk_leg_collar", [0.075, 0.04, 0.075], [x, 0.57, z], this.edge);
        this.box(this.desk, "desk_foot", [0.068, 0.055, 0.068], [x, 0.0275, z], this.edge);
      }
      this.box(this.desk, "desk_side_apron", [0.04, 0.16, 0.9], [x, 0.63, 0]);
      this.box(this.desk, "desk_side_stretcher", [0.035, 0.04, 0.85], [x, 0.23, 0]);
    }
    this.box(this.desk, "desk_back_apron", [1.06, 0.16, 0.028], [0, 0.63, -0.44]);
    for (const x of [-0.435, 0.435])
      this.box(this.desk, "drawer_face_surround", [0.18, 0.15, 0.03], [x, 0.63, 0.49], this.edge);
    for (const x of [-0.335, 0.335])
      this.box(this.desk, "drawer_runner", [0.025, 0.025, 0.87], [x, 0.543, 0]);
    this.box(this.drawer, "drawer_base", [0.64, 0.012, 0.66], [0, 0.565, 0.17]);
    for (const x of [-0.315, 0.315])
      this.box(this.drawer, "drawer_side", [0.018, 0.13, 0.66], [x, 0.623, 0.17]);
    this.box(this.drawer, "drawer_back", [0.62, 0.13, 0.018], [0, 0.623, -0.15]);
    this.box(
      this.drawer,
      "drawer_front_moulding",
      [0.68, 0.15, 0.035],
      [0, 0.633, 0.51],
      this.edge,
    );
    this.box(this.drawer, "drawer_front_inset", [0.614, 0.104, 0.016], [0, 0.633, 0.535]);
    for (const x of [-0.3, 0.3])
      for (let k = 0; k < 4; k++)
        this.box(
          this.drawer,
          "drawer_dovetail",
          [0.02, 0.014, 0.004],
          [x, 0.59 + k * 0.024, 0.545],
          this.edge,
        );
    this.box(this.drawer, "lock_escutcheon", [0.034, 0.049, 0.003], [0, 0.642, 0.547], this.brass);
    this.box(this.drawer, "keyhole_stem", [0.004, 0.014, 0.002], [0, 0.639, 0.55], this.iron);
    const hole = this.cylinder(
      this.drawer,
      "keyhole_round",
      0.009,
      0.002,
      [0, 0.648, 0.55],
      this.iron,
    );
    hole.rotation.x = Math.PI / 2;
    for (const x of [-0.18, 0.18]) {
      this.ring(this.drawer, "brass_drop_handle", 0.045, [x, 0.618, 0.56]);
      this.screw(this.drawer, [x, 0.641, 0.553]);
    }
    this.screw(this.drawer, [0, 0.661, 0.551]);
  }

  private buildJournal(): void {
    const paper = this.mat("journal_paper", "#cbbb95", 0.98);
    const rand = seededRandom(1030);
    for (let k = 0; k < 9; k++) {
      const sheet = this.box(
        this.journal,
        "journal_b_sheet",
        [0.23, 0.001, 0.3],
        [(rand() - 0.5) * 0.008, k * 0.0011, 0],
        paper,
      );
      sheet.rotation.y = (rand() - 0.5) * 0.06;
    }
    const ink = this.mat("journal_b_ink", "#ffffff", 0.98);
    const tex = new DynamicTexture(
      "journal_b_diagrams",
      { width: 768, height: 1024 },
      this.scene,
      true,
    );
    const c = tex.getContext() as CanvasRenderingContext2D;
    c.fillStyle = "#cbbb95";
    c.fillRect(0, 0, 768, 1024);
    for (let k = 0; k < 7000; k++) {
      c.fillStyle = `rgba(65,43,25,${rand() * 0.09})`;
      c.fillRect(rand() * 768, rand() * 1024, 1 + rand() * 2, 1);
    }
    c.fillStyle = "#493a27";
    c.font = "38px 'Preah Vihear'";
    c.fillText("ត្រាទីមួយ", 70, 100);
    c.font = "24px 'Preah Vihear'";
    ["ហិបដែក — កូនសោបីបំណែក", "ពាងទឹកក្រោមផ្ទះ", "មុនម៉ោងបី", "កុំងាកក្រោយ"].forEach((s, i) =>
      c.fillText(s, 65, 180 + i * 75),
    );
    c.strokeStyle = "#58442e";
    c.lineWidth = 3;
    for (let i = 0; i < 3; i++) {
      const x = 160 + i * 215;
      c.beginPath();
      c.ellipse(x, 590, 65, 80, 0, 0, Math.PI * 2);
      c.stroke();
      c.beginPath();
      c.ellipse(x, 515, 45, 13, 0, 0, Math.PI * 2);
      c.stroke();
      c.strokeRect(x - 15, 568, 30, 10);
    }
    c.strokeRect(185, 760, 390, 150);
    c.beginPath();
    c.arc(380, 830, 36, 0, Math.PI * 2);
    c.stroke();
    c.fillText("សុខ", 575, 970);
    tex.update();
    ink.albedoTexture = tex;
    const page = CreatePlane(
      "journal_b_written_page",
      { width: 0.226, height: 0.296, sideOrientation: Mesh.DOUBLESIDE },
      this.scene,
    );
    this.finish(page, this.journal, [0, 0.0105, 0], ink);
    page.rotation.x = Math.PI / 2;
    const cord = this.box(
      this.journal,
      "paper_binding",
      [0.003, 0.014, 0.25],
      [-0.095, 0.007, 0],
      this.edge,
    );
    cord.rotation.y = 0.05;
  }

  private buildPortrait(authoredFrame: boolean): void {
    // The imported photo uses baked UVs. The new frame uses the original image
    // with plain portrait UVs, independent of the village's texture atlas.
    const photoMat = this.mat("framed_photograph", authoredFrame ? "#c9c5ba" : "#ffffff", 0.86);
    photoMat.albedoTexture = new Texture(
      `${import.meta.env.BASE_URL}assets/ep1/T_ep1_photo_sok_BC.png`,
      this.scene,
    );
    const photo = CreatePlane(
      "sok_portrait_photograph",
      { width: 0.3, height: 0.4, sideOrientation: Mesh.DOUBLESIDE },
      this.scene,
    );
    const faceDepth = authoredFrame ? 0.002 : 0.015;
    this.finish(photo, this.portrait, [0, 0, faceDepth], photoMat);
    photo.rotation.y = Math.PI;
    if (!authoredFrame) {
      this.box(
        this.portrait,
        "portrait_backboard",
        [0.385, 0.485, 0.025],
        [0, 0, -0.009],
        this.edge,
      );
      for (const [w, h, depth, offset] of [
        [0.38, 0.48, 0.035, 0],
        [0.35, 0.45, 0.018, 0.013],
        [0.32, 0.42, 0.009, 0.021],
      ]) {
        for (const x of [-w / 2, w / 2])
          this.box(
            this.portrait,
            "portrait_moulded_stile",
            [0.018, h, depth],
            [x, 0, offset],
            this.edge,
          );
        for (const y of [-h / 2, h / 2])
          this.box(
            this.portrait,
            "portrait_moulded_rail",
            [w + 0.018, 0.018, depth],
            [0, y, offset],
            this.edge,
          );
      }
      for (const x of [-0.18, 0.18])
        for (const y of [-0.23, 0.23]) {
          this.box(
            this.portrait,
            "portrait_brass_corner",
            [0.035, 0.004, 0.002],
            [x, y, 0.023],
            this.brass,
          );
          this.screw(this.portrait, [x, y, 0.025]);
        }
      const flower = this.mat("dried_jasmine", "#c5bda3", 1);
      const garland: Mesh[] = [];
      for (let k = 0; k < 44; k++) {
        const a = (k / 43) * Math.PI;
        const bead = CreateSphere(
          "portrait_jasmine_floret",
          { diameter: 0.018, segments: 6 },
          this.scene,
        );
        this.finish(
          bead,
          this.portrait,
          [-Math.cos(a) * 0.213, -0.14 + Math.sin(a) * 0.39, 0.042],
          flower,
        );
        bead.scaling.set(1, 0.75, 0.7);
        garland.push(bead);
      }
      const merged = Mesh.MergeMeshes(garland, true, true);
      if (merged) {
        merged.name = "portrait_jasmine_garland";
        merged.setParent(this.portrait, true);
        this.meshes.push(merged);
      }
    }
    const sclera = this.mat("portrait_eyes", "#b2a280", 0.94);
    const iris = this.mat("portrait_iris", "#302a20", 0.94);
    const skin = this.mat("portrait_eyelid", "#8e795a", 1);
    for (const u of [0.451, 0.583]) {
      const eye = this.root(
        "sok_portrait_eye",
        new Vector3((0.5 - u) * 0.3, 0.061, faceDepth + 0.0018),
        this.portrait,
      );
      this.eyes.push(eye);
      const white = CreateSphere("portrait_eye_inset", { diameter: 1, segments: 16 }, this.scene);
      this.finish(white, eye, [0, 0, 0], sclera);
      white.scaling.set(0.017, 0.006, 0.0016);
      const pupil = CreateSphere("portrait_dark_pupil", { diameter: 1, segments: 12 }, this.scene);
      this.finish(pupil, eye, [0, 0, 0.0013], iris);
      pupil.scaling.set(0.005, 0.0055, 0.0008);
      const lid = CreateSphere("portrait_closed_lid", { diameter: 1, segments: 16 }, this.scene);
      this.finish(lid, eye, [0, 0, 0.0022], skin);
      lid.scaling.set(0.018, 0.007, 0.001);
      // Lid scaling is on a second node so the photographed eye can unfold beneath it.
      const lidRoot = this.root("portrait_upper_lid", Vector3.Zero(), this.portrait);
      lidRoot.position.copyFrom(eye.position);
      lid.parent = lidRoot;
      this.lids.push(lid);
    }
    this.portrait.rotation.x = authoredFrame ? Math.PI / 18 : -0.12;
    if (authoredFrame) this.portrait.scaling.set(0.404 / 0.3, 0.56 / 0.4, 1);
  }

  private woodGrain(): void {
    const tex = new DynamicTexture("desk_teak_grain", 512, this.scene, true);
    const c = tex.getContext() as CanvasRenderingContext2D,
      rand = seededRandom(1029);
    c.fillStyle = "#61432d";
    c.fillRect(0, 0, 512, 512);
    for (let k = 0; k < 950; k++) {
      const x = rand() * 512;
      c.strokeStyle = `rgba(${rand() > 0.45 ? "169,119,65" : "24,15,9"},${0.03 + rand() * 0.12})`;
      c.lineWidth = 0.5 + rand();
      c.beginPath();
      c.moveTo(x, 0);
      c.bezierCurveTo(x + rand() * 14, 190, x - rand() * 11, 345, x, 512);
      c.stroke();
    }
    tex.update();
    this.wood.albedoTexture = tex;
  }
}
