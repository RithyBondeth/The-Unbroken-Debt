import type { Scene } from "@babylonjs/core/scene";
import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { VertexData } from "@babylonjs/core/Meshes/mesh.vertexData";
import { CreateCylinder } from "@babylonjs/core/Meshes/Builders/cylinderBuilder";
import { PointLight } from "@babylonjs/core/Lights/pointLight";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { Quaternion, Vector3 } from "@babylonjs/core/Maths/math.vector";
import { PhysicsBody } from "@babylonjs/core/Physics/v2/physicsBody";
import { PhysicsShapeBox } from "@babylonjs/core/Physics/v2/physicsShape";
import { PhysicsMotionType } from "@babylonjs/core/Physics/v2/IPhysicsEnginePlugin";
import type { AudioSystem } from "@/audio/AudioSystem";
import { seededRandom } from "@/audio/synth";
import { limitLightToRange } from "@/render/renderSetup";
import { RelicCraft } from "@/shared/RelicCraft";
import { pavilionCloth } from "@/audio/sounds/atmosphereSounds";
import { whispers } from "../audio/vigilSounds";

type XYZ = readonly [number, number, number];

/**
 * The guests' tent in the east of the yard, opposite the cooking shelter, open
 * towards the funeral pavilion (Babylon metres; Blender x 6.4–11.4, y 0.8–6.4).
 */
const X0 = -11.4,
  X1 = -6.4,
  Z0 = -6.4,
  Z1 = -0.8;
const XC = (X0 + X1) / 2;
const EAVE = 2.3,
  RIDGE = 3.35;
/** The two raised bamboo platforms (kré): centre x, and their shared centre and length along z. */
const TABLES = [-7.95, -9.85];
const TABLE_Z = (Z0 + Z1) / 2,
  TABLE_LENGTH = 3.0,
  TABLE_WIDTH = 1.05,
  TABLE_HEIGHT = 0.42;

/**
 * A second shelter for the mourners who came to sit with the dead, as a 1930s
 * village raised it: a bamboo frame under palm thatch laid in courses, lined
 * with white cotton, and two raised bamboo platforms (kré) spread with reed
 * mats, where the guests sat cross-legged round low trays of rice and tea.
 * Nobody is here. The tea has gone cold, a stool lies on its side, cups are
 * knocked over, and at the head of the near platform one bowl of rice has three
 * incense sticks stood upright in it: food set for the dead. A corner of the
 * white lining has torn and flaps. The first time Sora steps under it the mats
 * murmur with guests who are not there, and the oil lamp gutters out.
 */
export class GuestTent {
  readonly root: TransformNode;
  private readonly c: RelicCraft;
  private readonly lantern: TransformNode;
  private readonly globe: Mesh;
  private readonly light: PointLight;
  private readonly flames: Mesh[] = [];
  private readonly flap: TransformNode;
  private time = 0;
  /** Seconds left of the lantern guttering out, after the murmur. */
  private gutter = 0;
  private murmured = false;
  private murmurAt = -1;
  private sounds: { murmur: StaticSound | null; cloth: StaticSound | null } = {
    murmur: null,
    cloth: null,
  };

  constructor(
    private readonly scene: Scene,
    ground: (x: number, z: number) => number,
  ) {
    const c = (this.c = new RelicCraft(scene));
    const y = ground(XC, TABLE_Z);
    this.root = c.root("guest_tent", [0, y, 0]);
    const m = {
      bamboo: this.material("M_bamboo", "#8a7a4e", "wood"),
      linen: this.material("M_funeral_linen", "#cfcbbd", "cloth"),
      // Mourning is white here: aged undyed cotton where the pavilion once had black.
      aged: this.material("M_cotton_dirty", "#8a8476", "cloth"),
      thatch: this.material("M_wet_thatch", "#5b4a31", "wood"),
      mat: this.material("M_reed_mat", "#a08b5c", "paper"),
      clay: this.material("M_clay", "#6a3b22", "wood"),
      tin: c.mat("guest_tent_tin", "#3a3833", 0.55, 0.6),
      wood: this.material("M_funeral_wood", "#5a3a22", "wood"),
      bench: this.material("M_worn_wood", "#4a3a2a", "wood"),
      porcelain: this.material("M_funeral_porcelain", "#c8c8bc", "paper"),
      rice: this.material("M_rice", "#d8d0b4", "paper"),
      incense: this.material("M_incense", "#7a2a1c", "wood"),
      wax: this.material("M_candle_wax", "#d8cfae", "paper"),
      rattan: this.material("M_rattan", "#7a6038", "wood"),
      tea: c.mat("guest_tent_cold_tea", "#4f3118", 0.15),
      // Its own smoked glass chimney, lit from inside by the wick (update() dims it).
      globe: c.mat("guest_tent_lamp_glass", "#6b5a3c", 0.25),
    };
    m.globe.emissiveColor = new Color3(1, 0.68, 0.36);
    const flame = c.mat("guest_tent_flame", "#000000", 1);
    flame.emissiveColor = new Color3(1, 0.62, 0.26);
    flame.unlit = true;
    const ember = c.mat("guest_tent_ember", "#000000", 1);
    ember.emissiveColor = new Color3(0.9, 0.22, 0.05);
    ember.unlit = true;

    this.buildFrame(m.bamboo, m.linen, m.rattan);
    this.buildRoof(m.linen, m.aged);
    this.buildThatch(m.thatch);
    this.flap = this.buildFlap(m.linen);
    this.buildBackCloth(m.linen, m.aged);
    for (const [k, x] of TABLES.entries()) this.buildTable(k, x, m, flame, ember);

    // The lantern hangs from the ridge between the tables, on a rattan cord.
    this.lantern = c.root("guest_tent_lantern", [XC, RIDGE - 0.06, TABLE_Z], this.root);
    c.tube(
      this.lantern,
      "guest_tent_lantern_cord",
      [
        [0, 0, 0],
        [0, -0.62, 0],
      ],
      0.006,
      m.rattan,
    );
    // A tin oil lamp: a wire bail, a vented cap, a glass chimney over the wick,
    // and the tin fount below it.
    c.ring(this.lantern, "guest_tent_lantern_bail", 0.16, 0.004, [0, -0.7, 0], m.tin).rotation.x =
      Math.PI / 2;
    c.cylinder(this.lantern, "guest_tent_lantern_cap", 0.1, 0.035, [0, -0.66, 0], m.tin);
    this.globe = c.sphere(
      this.lantern,
      "guest_tent_lantern_globe",
      [0.11, 0.17, 0.11],
      [0, -0.77, 0],
      m.globe,
    );
    c.cylinder(this.lantern, "guest_tent_lantern_collar", 0.09, 0.02, [0, -0.86, 0], m.tin);
    c.sphere(this.lantern, "guest_tent_lantern_fount", [0.15, 0.08, 0.15], [0, -0.9, 0], m.tin);
    this.light = new PointLight("guest_tent_lantern_light", Vector3.Zero(), scene);
    this.light.parent = this.globe;
    this.light.diffuse = new Color3(1, 0.7, 0.42);
    this.light.specular = new Color3(0.25, 0.18, 0.1);
    this.light.range = 6.5;
    this.light.intensity = 0;
    this.light.shadowEnabled = false;
    this.light.renderPriority = 2;
    for (const mesh of c.meshes) {
      mesh.isPickable = false;
      mesh.receiveShadows = true;
    }
    limitLightToRange(
      this.light,
      c.meshes.filter((mesh) => mesh.parent !== this.lantern),
    );
  }

  /** The scene's own material by name, or a painted stand-in when it isn't loaded. */
  private material(name: string, colour: string, kind: "wood" | "cloth" | "paper"): PBRMaterial {
    const found = this.scene.getMaterialByName(name);
    if (found instanceof PBRMaterial) return found;
    const stand = this.c.surface(`guest_${name}`, colour, kind);
    stand.backFaceCulling = kind !== "cloth";
    stand.twoSidedLighting = kind === "cloth";
    return stand;
  }

  private buildFrame(bamboo: PBRMaterial, band: PBRMaterial, rattan: PBRMaterial): void {
    const c = this.c;
    const zs = [Z0, (Z0 + Z1) / 2, Z1];
    for (const x of [X0, X1])
      for (const z of zs) {
        c.cylinder(
          this.root,
          "guest_tent_post",
          0.085,
          EAVE + 0.1,
          [x, (EAVE + 0.1) / 2, z],
          bamboo,
        );
        // A strip of white cotton knotted round every post, the colour of mourning.
        c.cylinder(this.root, "guest_tent_post_mourning_band", 0.1, 0.16, [x, 1.55, z], band);
        // Rattan lashed where the post meets the eave plate.
        for (const y of [EAVE - 0.06, EAVE + 0.02])
          c.cylinder(this.root, "guest_tent_lashing", 0.098, 0.035, [x, y, z], rattan);
        this.solid([0.12, EAVE, 0.12], [x, EAVE / 2, z]);
      }
    for (const z of [Z0, Z1])
      c.cylinder(this.root, "guest_tent_ridge_post", 0.08, RIDGE, [XC, RIDGE / 2, z], bamboo);
    const pole = (from: XYZ, to: XYZ) =>
      c.tube(this.root, "guest_tent_pole", [from, to], 0.035, bamboo);
    pole([XC, RIDGE, Z0 - 0.2], [XC, RIDGE, Z1 + 0.2]);
    for (const x of [X0, X1]) pole([x, EAVE, Z0 - 0.2], [x, EAVE, Z1 + 0.2]);
    for (const z of [Z0, Z1]) {
      pole([X0 - 0.1, EAVE, z], [X1 + 0.1, EAVE, z]);
      pole([X0, EAVE, z], [XC, RIDGE, z]);
      pole([X1, EAVE, z], [XC, RIDGE, z]);
    }
  }

  /** The white lining under the thatch, sagging, the back one torn at its north corner. */
  private buildRoof(linen: PBRMaterial, valance: PBRMaterial): void {
    const half = (X1 - X0) / 2 + 0.3;
    for (const side of [-1, 1]) {
      const torn = side < 0;
      this.cloth(
        `guest_tent_roof_${side}`,
        (u, v) => {
          const bay = (u * 2) % 1;
          const sag = 0.11 * Math.sin(Math.PI * bay) ** 2 * (0.3 + 0.7 * v);
          return [
            XC + side * half * v,
            RIDGE + 0.04 - (RIDGE - EAVE + 0.18) * v - sag,
            Z0 - 0.3 + (Z1 - Z0 + 0.6) * u,
          ];
        },
        28,
        12,
        linen,
        // A ragged hole where the cloth has torn away from the eave.
        torn ? (u, v) => u > 0.78 && v > 0.42 + 0.25 * Math.sin(u * 37) ** 2 : undefined,
      );
      // A scalloped valance of older cotton along each eave.
      this.cloth(
        `guest_tent_valance_${side}`,
        (u, v) => {
          const z = Z0 - 0.3 + (Z1 - Z0 + 0.6) * u;
          const drop = 0.1 + 0.2 * Math.abs(Math.sin(Math.PI * u * 9));
          return [XC + side * (half + 0.01), EAVE - 0.14 - drop * v, z];
        },
        90,
        2,
        valance,
        torn ? (u) => u > 0.8 : undefined,
      );
    }
  }

  /** The torn piece, hanging from the eave and lifting in the wind. */
  private buildFlap(linen: PBRMaterial): TransformNode {
    const half = (X1 - X0) / 2 + 0.3;
    const hinge = this.c.root(
      "guest_tent_flap",
      [XC - half * 0.62, EAVE + 0.32, Z1 - 0.15],
      this.root,
    );
    this.cloth(
      "guest_tent_torn_cloth",
      (u, v) => [
        -0.05 * Math.sin(v * 3 + u),
        -1.25 * v - 0.12 * Math.sin(u * Math.PI),
        (u - 0.5) * (0.95 - 0.55 * v) + 0.06 * Math.sin(v * 9),
      ],
      10,
      14,
      linen,
      // Its lower edge ripped ragged.
      (u, v) => v > 0.78 + 0.18 * Math.sin(u * 29) ** 2,
      hinge,
    );
    return hinge;
  }

  /** The back wall, away from the pavilion: white cloth in folds, gathered at its posts. */
  private buildBackCloth(linen: PBRMaterial, gathered: PBRMaterial): void {
    this.cloth(
      "guest_tent_back_cloth",
      (u, v) => [
        X0 - 0.04 + 0.05 * Math.sin(u * 50),
        EAVE - 0.08 - (EAVE - 0.12) * v,
        Z0 + (Z1 - Z0) * u,
      ],
      64,
      10,
      linen,
    );
    for (const z of [Z0, (Z0 + Z1) / 2, Z1])
      this.cloth(
        "guest_tent_back_curtain",
        (u, v) => {
          const width =
            v < 0.6 ? 0.42 - 0.3 * Math.sin((Math.PI * v) / 1.2) : 0.12 + 0.3 * (v - 0.6);
          return [
            X0 + 0.04 + 0.02 * Math.sin(u * 20),
            EAVE - 0.06 - (EAVE - 0.14) * v,
            z + (u - 0.5) * width,
          ];
        },
        8,
        16,
        gathered,
      );
  }

  /**
   * Palm thatch laid in overlapping courses over each slope, every course's lower
   * edge ragged where the fronds end, and a capping of bent fronds on the ridge.
   */
  private buildThatch(thatch: PBRMaterial): void {
    const r = seededRandom(4433);
    const half = (X1 - X0) / 2 + 0.55;
    const drop = RIDGE - EAVE + 0.36;
    const run = Math.hypot(half, drop);
    const za = Z0 - 0.55,
      zb = Z1 + 0.55;
    const cols = Math.round((zb - za) / 0.06);
    for (const side of [-1, 1]) {
      // Along the slope from the ridge (d = 0) to the eave edge (d = run), lifted off it.
      const nx = (side * drop) / run,
        ny = half / run;
      const at = (z: number, d: number, lift: number): XYZ => [
        XC + (side * half * d) / run + nx * lift,
        RIDGE + 0.12 - (drop * d) / run + ny * lift,
        z,
      ];
      const positions: number[] = [],
        uvs: number[] = [],
        indices: number[] = [];
      let course = 0;
      for (let d = run; d > 0.12; d -= 0.21, course++) {
        const base = positions.length / 3;
        for (let i = 0; i <= cols; i++) {
          const z = za + ((zb - za) * i) / cols + (r() - 0.5) * 0.015;
          const low = d + r() * 0.07 + 0.03 * Math.sin(i * 0.7 + course);
          for (const [dd, lift] of [
            [low, 0.13 + 0.01 * (i % 3)],
            [low - 0.25, 0.1],
            [low - 0.55, 0.075],
          ] as const) {
            positions.push(...at(z, dd, lift));
            uvs.push(z * 0.9, dd * 0.9);
          }
        }
        for (let i = 0; i < cols; i++) {
          const q = base + i * 3;
          if (side > 0)
            indices.push(
              q,
              q + 3,
              q + 1,
              q + 1,
              q + 3,
              q + 4,
              q + 1,
              q + 4,
              q + 2,
              q + 2,
              q + 4,
              q + 5,
            );
          else
            indices.push(
              q,
              q + 1,
              q + 3,
              q + 1,
              q + 4,
              q + 3,
              q + 1,
              q + 2,
              q + 4,
              q + 2,
              q + 5,
              q + 4,
            );
        }
      }
      this.customMesh(`guest_tent_thatch_${side}`, positions, uvs, indices, thatch);
      // Fronds frayed from the eave course, hanging.
      for (let k = 0; k < 60; k++) {
        const z = za + r() * (zb - za);
        const top = at(z, run + 0.02, 0.12);
        const length = 0.06 + r() * 0.18;
        this.c.tube(
          this.root,
          "guest_tent_thatch_fray",
          [top, [top[0] + side * 0.03, top[1] - length, top[2] + (r() - 0.5) * 0.04]],
          0.005,
          thatch,
        );
      }
    }
    // The ridge capping: fronds bent over the ridge pole.
    const positions: number[] = [],
      uvs: number[] = [],
      indices: number[] = [];
    for (let i = 0; i <= cols; i++) {
      const z = za + ((zb - za) * i) / cols;
      for (let j = 0; j <= 6; j++) {
        const a = (j / 6 - 0.5) * 2.4;
        const rr = 0.26 + (j === 0 || j === 6 ? r() * 0.04 : 0);
        positions.push(XC + Math.sin(a) * rr, RIDGE + 0.17 + Math.cos(a) * rr * 0.6, z);
        uvs.push(z * 0.9, j / 6);
      }
    }
    for (let i = 0; i < cols; i++)
      for (let j = 0; j < 6; j++) {
        const q = i * 7 + j;
        indices.push(q, q + 1, q + 7, q + 1, q + 8, q + 7);
      }
    this.customMesh("guest_tent_thatch_ridge", positions, uvs, indices, thatch);
  }

  private customMesh(
    name: string,
    positions: number[],
    uvs: number[],
    indices: number[],
    material: PBRMaterial,
  ): Mesh {
    const data = new VertexData();
    data.positions = positions;
    data.indices = indices;
    data.uvs = uvs;
    const normals: number[] = [];
    VertexData.ComputeNormals(positions, indices, normals);
    data.normals = normals;
    const mesh = new Mesh(name, this.scene);
    data.applyToMesh(mesh);
    return this.c.finish(mesh, this.root, [0, 0, 0], material);
  }

  private buildTable(
    k: number,
    x: number,
    m: Record<string, PBRMaterial>,
    flame: PBRMaterial,
    ember: PBRMaterial,
  ): void {
    const c = this.c;
    const t = c.root(`guest_tent_table_${k}`, [x, 0, TABLE_Z], this.root);
    const r = seededRandom(4410 + k);
    // A raised bamboo platform: a frame of poles on short posts, split bamboo
    // laid across it, a reed mat spread on top where the guests sat.
    const hw = TABLE_WIDTH / 2,
      hl = TABLE_LENGTH / 2;
    for (const sx of [-1, 1])
      for (const sz of [-1, 0, 1])
        c.cylinder(
          t,
          "guest_platform_post",
          0.07,
          TABLE_HEIGHT - 0.04,
          [sx * (hw - 0.05), (TABLE_HEIGHT - 0.04) / 2, sz * (hl - 0.06)],
          m.bamboo,
        );
    for (const sx of [-1, 1])
      c.tube(
        t,
        "guest_platform_rail",
        [
          [sx * (hw - 0.04), TABLE_HEIGHT - 0.06, -hl],
          [sx * (hw - 0.04), TABLE_HEIGHT - 0.06, hl],
        ],
        0.035,
        m.bamboo,
      );
    for (let i = 0; i < 16; i++) {
      const sx = -hw + 0.03 + ((TABLE_WIDTH - 0.06) * i) / 15;
      c.tube(
        t,
        "guest_platform_slat",
        [
          [sx, TABLE_HEIGHT - 0.025, -hl - 0.03],
          [sx + (r() - 0.5) * 0.01, TABLE_HEIGHT - 0.025, hl + 0.03],
        ],
        0.017,
        m.bamboo,
      );
    }
    this.cloth(
      "guest_platform_mat",
      (u, v) => [
        (v - 0.5) * (TABLE_WIDTH - 0.08),
        TABLE_HEIGHT + 0.004 + 0.003 * Math.sin(u * 37 + v * 5),
        (u - 0.5) * (TABLE_LENGTH - 0.12),
      ],
      30,
      6,
      m.mat,
      undefined,
      t,
    );
    this.solid([TABLE_WIDTH, TABLE_HEIGHT, TABLE_LENGTH], [x, TABLE_HEIGHT / 2, TABLE_Z]);
    // Low round trays down the middle, the guests' places round them.
    for (const z of [-0.75, 0.75]) {
      c.cylinder(t, "guest_tray", 0.62, 0.025, [0, TABLE_HEIGHT + 0.02, z], m.wood);
      c.ring(t, "guest_tray_rim", 0.62, 0.02, [0, TABLE_HEIGHT + 0.035, z], m.rattan);
    }
    // A low stool by the far platform, knocked over.
    if (k === 1) {
      const stool = c.root("guest_fallen_stool", [hw + 0.45, 0.12, 0.4], t);
      c.box(stool, "guest_stool_seat", [0.3, 0.03, 0.22], [0, 0, 0], m.bench);
      for (const sx of [-1, 1])
        c.box(stool, "guest_stool_leg", [0.03, 0.22, 0.2], [sx * 0.12, -0.11, 0], m.bench);
      stool.rotation.set(0, 0.5, Math.PI / 2);
      this.solid([0.3, 0.3, 0.3], [x + hw + 0.45, 0.15, TABLE_Z + 0.4]);
    }

    // Places for eight: bowls of rice, cups of tea gone cold. Some cups are over.
    const top = TABLE_HEIGHT + 0.033;
    for (const side of [-1, 1])
      for (const z of [-1.05, -0.35, 0.35, 1.05]) {
        const px = side * 0.16 + (r() - 0.5) * 0.03,
          pz = z * 0.9 + (r() - 0.5) * 0.06;
        this.vessel(t, "guest_bowl", 0.13, 0.055, 0.05, [px, top + 0.025, pz], m.porcelain);
        c.sphere(t, "guest_bowl_rice", [0.11, 0.04, 0.11], [px, top + 0.05, pz], m.rice);
        const cx = px - side * 0.1,
          cz = pz + 0.11;
        const over = r() < 0.3;
        const cup = this.vessel(
          t,
          "guest_tea_cup",
          0.06,
          0.04,
          0.05,
          [cx, top + (over ? 0.028 : 0.025), cz],
          m.porcelain,
        );
        if (over) {
          cup.rotation.set(0, r() * 3, Math.PI / 2);
          // Cold tea run across the cloth.
          const spill = c.cylinder(
            t,
            "guest_tea_spill",
            0.16 + r() * 0.1,
            0.002,
            [cx + side * 0.05, top + 0.001, cz + 0.03],
            m.tea,
          );
          spill.scaling.z = 0.55;
        } else c.cylinder(t, "guest_tea", 0.048, 0.002, [cx, top + 0.046, cz], m.tea);
      }
    // A clay teapot between the trays.
    const pot = c.sphere(t, "guest_teapot", [0.15, 0.11, 0.15], [0, top + 0.05, 0.02], m.clay);
    c.cylinder(t, "guest_teapot_lid", 0.06, 0.02, [0, top + 0.11, 0.02], m.clay);
    pot.rotation.y = r() * 3;
    c.tube(
      t,
      "guest_teapot_spout",
      [
        [0.07, top + 0.05, 0.02],
        [0.13, top + 0.1, 0.02],
      ],
      0.012,
      m.clay,
    );
    c.ring(t, "guest_teapot_handle", 0.09, 0.012, [-0.08, top + 0.07, 0.02], m.rattan).rotation.x =
      Math.PI / 2;

    // A candle burnt low in a saucer of its own wax.
    const candleZ = k === 0 ? -0.7 : 0.75;
    c.cylinder(t, "guest_candle_saucer", 0.1, 0.012, [0, top + 0.006, candleZ], m.porcelain);
    c.cylinder(t, "guest_candle", 0.032, 0.08, [0, top + 0.052, candleZ], m.wax);
    const candleFlame = c.sphere(
      t,
      "guest_candle_flame",
      [0.016, 0.04, 0.016],
      [0, top + 0.112, candleZ],
      flame,
    );
    this.flames.push(candleFlame);

    if (k === 0) {
      // At the head of the near table, a place nobody sits at: its rice has three
      // incense sticks stood upright in it, the way food is set for the dead.
      const hz = -TABLE_LENGTH / 2 + 0.22;
      this.vessel(t, "guest_dead_bowl", 0.14, 0.06, 0.055, [0, top + 0.028, hz], m.porcelain);
      c.sphere(t, "guest_dead_rice", [0.12, 0.05, 0.12], [0, top + 0.056, hz], m.rice);
      for (const [dx, dz] of [
        [-0.025, 0],
        [0.02, 0.015],
        [0.005, -0.02],
      ]) {
        const stick = c.cylinder(
          t,
          "guest_dead_incense",
          0.004,
          0.24,
          [dx, top + 0.18, hz + dz],
          m.incense,
        );
        stick.rotation.z = dx * 1.2;
        c.sphere(
          t,
          "guest_dead_incense_ember",
          [0.007, 0.012, 0.007],
          [dx + dx * 0.14, top + 0.3, hz + dz],
          ember,
        );
      }
      this.vessel(
        t,
        "guest_dead_cup",
        0.06,
        0.04,
        0.05,
        [0.14, top + 0.025, hz + 0.04],
        m.porcelain,
      );
    }
  }

  /**
   * A cloth surface over (u, v) in 0–1, from `at` (relative to `parent`, or the
   * tent); the cloth materials draw both sides. `hole` drops quads, for tears and
   * scalloped edges.
   */
  private cloth(
    name: string,
    at: (u: number, v: number) => XYZ,
    nu: number,
    nv: number,
    material: PBRMaterial,
    hole?: (u: number, v: number) => boolean,
    parent: TransformNode = this.root,
  ): Mesh {
    // The weave at the same scale as the pavilion's cloth, whatever this piece's size.
    const span = (a: XYZ, b: XYZ) => Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]) * 0.9;
    const across = span(at(0, 0.5), at(1, 0.5)),
      down = span(at(0.5, 0), at(0.5, 1));
    const positions: number[] = [];
    const uvs: number[] = [];
    for (let j = 0; j <= nv; j++)
      for (let i = 0; i <= nu; i++) {
        const p = at(i / nu, j / nv);
        positions.push(...p);
        uvs.push((i / nu) * across, (j / nv) * down);
      }
    const indices: number[] = [];
    for (let j = 0; j < nv; j++)
      for (let i = 0; i < nu; i++) {
        if (hole?.((i + 0.5) / nu, (j + 0.5) / nv)) continue;
        const a = j * (nu + 1) + i,
          b = a + nu + 1;
        indices.push(a, b, a + 1, a + 1, b, b + 1);
      }
    const data = new VertexData();
    data.positions = positions;
    data.indices = indices;
    data.uvs = uvs;
    const normals: number[] = [];
    VertexData.ComputeNormals(positions, indices, normals);
    data.normals = normals;
    const mesh = new Mesh(name, this.scene);
    data.applyToMesh(mesh);
    return this.c.finish(mesh, parent, [0, 0, 0], material);
  }

  /** A bowl or cup: wider at the lip than the foot. */
  private vessel(
    parent: TransformNode,
    name: string,
    lip: number,
    foot: number,
    height: number,
    at: XYZ,
    material: PBRMaterial,
  ): Mesh {
    const mesh = CreateCylinder(
      name,
      { diameterTop: lip, diameterBottom: foot, height, tessellation: 32 },
      this.scene,
    );
    return this.c.finish(mesh, parent, at, material);
  }

  private solid(size: XYZ, at: XYZ): void {
    const anchor = new TransformNode("guest_tent_body", this.scene);
    anchor.position.set(at[0], this.root.position.y + at[1], at[2]);
    anchor.metadata = { surface: "teak" };
    const body = new PhysicsBody(anchor, PhysicsMotionType.STATIC, false, this.scene);
    body.shape = new PhysicsShapeBox(
      Vector3.Zero(),
      Quaternion.Identity(),
      new Vector3(...size),
      this.scene,
    );
  }

  async makeSounds(audio: AudioSystem): Promise<void> {
    const rate = audio.context.sampleRate;
    const centre = new Vector3(XC, this.root.position.y + 0.9, TABLE_Z);
    this.sounds.murmur = await audio.spatialSound(
      "guest_tent_murmur",
      audio.buffer(whispers(rate, seededRandom(4420)), rate),
      "threat",
      centre,
      { minDistance: 2.5, maxDistance: 18, volume: 0.75 },
    );
    this.sounds.cloth = await audio.spatialSound(
      "guest_tent_torn_cloth",
      audio.buffer(pavilionCloth(rate, seededRandom(4421)), rate),
      "ambience",
      this.flap.getAbsolutePosition(),
      { loop: true, minDistance: 2, maxDistance: 20, volume: 0.32 },
    );
    this.sounds.cloth.play();
  }

  /** `eye` is Sora's eye; `level` the funeral's lamps (they go out with the pavilion's). */
  update(dt: number, eye: Vector3, level: number, quiet: boolean): void {
    const t = (this.time += dt);
    // The torn cloth lifts and drops in the gusts.
    this.flap.rotation.x = 0.18 * Math.sin(t * 1.7) + 0.1 * Math.sin(t * 4.3 + 1);
    this.flap.rotation.z = 0.08 * Math.sin(t * 2.3 + 0.5);
    this.lantern.rotation.x = 0.05 * Math.sin(t * 0.9);
    this.lantern.rotation.z = 0.04 * Math.sin(t * 0.7 + 2);

    const under = eye.x > X0 && eye.x < X1 && eye.z > Z0 && eye.z < Z1;
    if (under && !this.murmured && !quiet) {
      // Guests talking low over their tea, all round her, then nobody.
      this.murmured = true;
      this.sounds.murmur?.play();
      this.murmurAt = t;
    }
    if (this.murmurAt >= 0 && t - this.murmurAt > 2.6) {
      this.murmurAt = -1;
      this.sounds.murmur?.stop();
      this.gutter = 1.8;
    }
    this.gutter = Math.max(0, this.gutter - dt);
    const flicker = 0.82 + 0.1 * Math.sin(t * 11.3) + 0.08 * Math.sin(t * 23.1 + 2);
    const out = this.gutter > 0 ? (this.gutter > 1.5 ? 0.3 * Math.random() : 0) : 1;
    this.light.intensity = 1.4 * level * flicker * out;
    (this.globe.material as PBRMaterial).emissiveIntensity = level * out;
    for (const [i, f] of this.flames.entries()) {
      const lit = level * (i === 0 && this.murmured ? 0 : out);
      f.setEnabled(lit > 0.05);
      f.scaling.y = 0.8 + 0.3 * Math.sin(t * (13 + i * 4));
    }
  }
}
