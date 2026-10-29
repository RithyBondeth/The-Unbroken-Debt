import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { CreateSphere } from "@babylonjs/core/Meshes/Builders/sphereBuilder";
import { VertexData } from "@babylonjs/core/Meshes/mesh.vertexData";
import type { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { PointLight } from "@babylonjs/core/Lights/pointLight";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { Game } from "../../../core/Game";
import { addStaticBox } from "../../../core/Physics";
import { boardCreak, rattlingBreath, seededRandom } from "../../../audio/synth";
import { spiritRattle } from "../audio/presenceSounds";
import { ShrineWoodwork } from "./ShrineWoodwork";
import { ShrineResponse } from "./ShrineResponse";
import { ShrineEffigy } from "./ShrineEffigy";
import { RelicCraft } from "../act3/RelicCraft";
import type { SavePointAppearance } from "../../../systems/saves/SavePoint";

type XYZ = [number, number, number];

/** An original, weathered spirit house, based on the supplied phra phum reference.
 * The architecture is welcoming enough to approach; its empty doorway and the
 * figure inside make paying respects uneasy. No offering or resource is spent.
 */
export class PhraPhum implements SavePointAppearance {
  readonly root: TransformNode;
  readonly hint = "hint.saveShrine" as const;
  readonly light: PointLight;
  private readonly craft: RelicCraft;
  private readonly effigy: ShrineEffigy;
  private readonly response = new ShrineResponse();
  private readonly flames: Mesh[] = [];
  private readonly ribbons: TransformNode[] = [];
  private readonly ember: PBRMaterial;
  private sound: StaticSound | null = null;
  private creak: StaticSound | null = null;
  private breath: StaticSound | null = null;
  private time = 0;

  constructor(
    private readonly game: Game,
    position: Vector3,
  ) {
    const scene = game.scene;
    const c = (this.craft = new RelicCraft(scene));
    this.root = c.root("house_front_right_phra_phum", [0, 0, 0]);
    const gold = c.mat("phra_phum_tarnished_gold", "#ffffff");
    gold.albedoTexture = c.painted("phra_phum_cracked_gilding", (ctx) => {
      const random = seededRandom(59130);
      ctx.fillStyle = "#867044";
      ctx.fillRect(0, 0, 512, 512);
      // Exposed red ground, soot and rain streaks interrupt the gold leaf.
      for (let k = 0; k < 150; k++) {
        const x = random() * 512,
          y = random() * 512,
          radius = 2 + random() * 13;
        ctx.fillStyle = k % 3 === 0 ? "#473c29" : "#624733";
        ctx.beginPath();
        for (let i = 0; i < 9; i++) {
          const a = (i / 8) * Math.PI * 2,
            r = radius * (0.45 + random() * 0.55);
          const px = x + Math.cos(a) * r,
            py = y + Math.sin(a) * r;
          if (i === 0) ctx.moveTo(px, py);
          else ctx.lineTo(px, py);
        }
        ctx.fill();
        ctx.strokeStyle = "rgba(35,35,24,.20)";
        ctx.lineWidth = 0.5 + random() * 2;
        ctx.beginPath();
        ctx.moveTo(x, y);
        ctx.lineTo(x + random() * 5, y + random() * 55);
        ctx.stroke();
      }
      for (let k = 0; k < 350; k++) {
        const x = random() * 512,
          y = random() * 512;
        ctx.strokeStyle = k % 4 ? "rgba(36,29,18,.22)" : "rgba(220,187,112,.27)";
        ctx.lineWidth = 0.5;
        ctx.beginPath();
        ctx.moveTo(x, y);
        ctx.lineTo(x + random() * 17, y + random() * 3);
        ctx.stroke();
      }
    });
    gold.metallic = 0.2;
    gold.roughness = 0.84;
    const edge = c.mat("phra_phum_worn_gilt_edges", "#8b744b", 0.8, 0.22);
    const sourceWood = scene.getMaterialByName("M_house_teak");
    const timber =
      sourceWood instanceof PBRMaterial
        ? sourceWood.clone("M_phra_phum_weathered_teak")
        : c.surface("phra_phum_hand_hewn_teak", "#4b3022", "wood");
    timber.roughness = 0.86;
    timber.maxSimultaneousLights = 8;
    timber.backFaceCulling = false;
    timber.twoSidedLighting = true;
    const carving = timber.clone("M_phra_phum_freshly_exposed_carving");
    carving.albedoColor = carving.albedoColor.scale(1.18);
    carving.roughness = 0.78;
    const woodwork = new ShrineWoodwork(c, this.root);
    const stone = c.mat("phra_phum_old_laterite", "#ffffff", 0.98);
    stone.albedoTexture = c.painted("phra_phum_laterite_aggregate", (ctx) => {
      const random = seededRandom(59002);
      ctx.fillStyle = "#715847";
      ctx.fillRect(0, 0, 512, 512);
      for (let k = 0; k < 5000; k++) {
        ctx.fillStyle = k % 3 ? "rgba(37,28,22,.25)" : "rgba(167,137,100,.32)";
        ctx.beginPath();
        ctx.ellipse(
          random() * 512,
          random() * 512,
          0.5 + random() * 3,
          0.5 + random() * 2,
          random() * 6,
          0,
          Math.PI * 2,
        );
        ctx.fill();
      }
    });
    const mortar = c.mat("phra_phum_crumbling_lime_mortar", "#8c8070", 1);
    const red = timber.clone("M_phra_phum_faded_red_shingles");
    red.albedoColor = red.albedoColor.multiply(new Color3(0.78, 0.43, 0.32));
    const black = c.mat("phra_phum_recesses", "#080a08", 1);
    const ash = c.mat("phra_phum_ash", "#514b3f", 1);
    const faded = c.mat("phra_phum_dried_marigold", "#9f773b", 0.98);
    const dead = c.mat("phra_phum_dead_petals", "#4c3523", 1);
    const cloth = c.surface("phra_phum_unbleached_cotton", "#978b72", "cloth");
    const wax = c.mat("phra_phum_old_wax", "#c4aa77", 0.9);
    this.ember = c.mat("phra_phum_candle_light", "#ffffff");
    this.ember.unlit = true;
    this.ember.emissiveColor.set(2.6, 0.95, 0.16);

    // Small masonry footing and irregular brick courses beneath a timber house.
    c.box(this.root, "phra_phum_foot", [0.82, 0.1, 0.73], [0, 0.05, 0], stone);
    c.box(this.root, "phra_phum_lower_step", [0.69, 0.075, 0.62], [0, 0.1375, 0], stone);
    c.box(this.root, "phra_phum_mortar_core", [0.49, 0.75, 0.43], [0, 0.55, 0], mortar);
    for (let course = 0; course < 5; course++) {
      const y = 0.25 + course * 0.137;
      for (const side of [-1, 1]) {
        for (let k = 0; k < 2; k++) {
          const brick = c.box(
            this.root,
            "phra_phum_laterite_course",
            [0.248, 0.126, 0.17],
            [(k - 0.5) * 0.258, y, side * 0.19],
            stone,
          );
          brick.rotation.z = Math.sin(course * 5 + k + side) * 0.006;
        }
        c.box(
          this.root,
          "phra_phum_laterite_side",
          [0.13, 0.126, 0.37],
          [side * 0.205, y, 0],
          stone,
        );
      }
    }
    for (const [y, w, d, h] of [
      [0.9, 0.58, 0.53, 0.09],
      [0.97, 0.82, 0.7, 0.07],
      [1.055, 1.34, 1.05, 0.1],
    ])
      c.box(this.root, "phra_phum_platform_moulding", [w, h, d], [0, y, 0], timber);
    c.box(this.root, "phra_phum_terrace", [1.3, 0.035, 1.02], [0, 1.1225, 0], red);
    for (const x of [-0.635, 0.635])
      c.box(this.root, "phra_phum_terrace_rim", [0.035, 0.065, 1.03], [x, 1.16, 0], edge);
    c.box(this.root, "phra_phum_front_rim", [1.3, 0.065, 0.035], [0, 1.16, 0.505], edge);
    // A dark, truly recessed chamber. The entrance has no front wall or card.
    c.box(this.root, "phra_phum_inner_floor", [0.71, 0.08, 0.65], [0, 1.25, -0.06], timber);
    c.box(this.root, "phra_phum_back_wall", [0.65, 0.66, 0.055], [0, 1.61, -0.36], red);
    const chamber = timber.clone("M_phra_phum_soot_darkened_chamber");
    chamber.albedoColor = chamber.albedoColor.scale(0.34);
    // Recessed individual boards retain the chamber's depth in lantern light.
    for (let k = 0; k < 7; k++)
      c.box(
        this.root,
        "phra_phum_chamber_back_board",
        [0.087, 0.59, 0.018],
        [(k - 3) * 0.089, 1.62, -0.321 + Math.sin(k * 4.3) * 0.002],
        chamber,
      );
    c.box(
      this.root,
      "phra_phum_chamber_back_rail",
      [0.61, 0.025, 0.028],
      [0, 1.37, -0.301],
      carving,
    );
    for (const side of [-1, 1]) {
      c.box(this.root, "phra_phum_side_wall", [0.04, 0.64, 0.57], [side * 0.325, 1.61, -0.05], red);
      for (const z of [-0.32, 0.28]) {
        this.pillar(side * 0.355, z, timber, timber);
        c.box(
          this.root,
          "phra_phum_tenon_cap",
          [0.12, 0.055, 0.12],
          [side * 0.355, 1.94, z],
          timber,
        );
      }
      for (const y of [1.37, 1.82])
        this.sphere(
          this.root,
          "phra_phum_wooden_joinery_peg",
          [0.009, 0.009, 0.004],
          [side * 0.355, y, 0.311],
          black,
        );
      for (let k = 0; k < 4; k++) this.pillar(side * 0.57, -0.39 + k * 0.24, timber, timber, true);
      c.tube(
        this.root,
        "phra_phum_side_brace",
        [
          [side * 0.35, 1.34, -0.29],
          [side * 0.35, 1.84, 0.24],
        ],
        0.013,
        timber,
      );
    }
    woodwork.entrance(timber, carving, edge, black);
    // Three steep, richly carved gables and lateral wings follow the supplied
    // Phra Phum silhouette. Tarnished gilding survives over red lacquered wood.
    for (const [half, depth, base, rise] of [
      [0.66, 1.04, 1.98, 0.62],
      [0.49, 0.8, 2.28, 0.55],
      [0.33, 0.57, 2.56, 0.45],
    ])
      woodwork.roof(half, depth, base, rise, red, timber, gold, edge);
    for (const side of [-1, 1]) {
      const wing = c.root(`phra_phum_roof_wing_${side}`, [side * 0.43, 0, -0.02], this.root);
      wing.rotation.y = (side * Math.PI) / 2;
      new ShrineWoodwork(c, wing).roof(0.29, 0.4, 2.02, 0.37, red, timber, gold, edge);
    }
    // Ringed prasat-like spire: a broad stepped foot, tall narrowing drums,
    // lotus shoulders, and a slender carved spear, rather than a short pin.
    for (let k = 0; k < 3; k++)
      c.box(
        this.root,
        "phra_phum_spire_stepped_foot",
        [0.27 - k * 0.035, 0.034, 0.27 - k * 0.035],
        [0, 3.018 + k * 0.034, 0],
        gold,
      );
    for (let k = 0; k < 10; k++) {
      const y = 3.12 + k * 0.034,
        radius = 0.103 - k * 0.0062;
      c.cylinder(this.root, "phra_phum_spire_carved_drum", radius * 2, 0.028, [0, y, 0], gold);
      c.ring(
        this.root,
        "phra_phum_spire_beaded_collar",
        radius * 2.09,
        0.009,
        [0, y + 0.016, 0],
        edge,
      );
    }
    c.tube(
      this.root,
      "phra_phum_spire_spear",
      [
        [0, 3.44, 0],
        [0, 3.57, 0],
        [0, 3.76, 0],
      ],
      0.009,
      gold,
    );
    for (const side of [-1, 1]) {
      woodwork.leaf([side * 0.025, 3.48, 0.006], 0.16, 0.032, side * -0.5, gold);
      woodwork.leaf([side * 0.018, 3.59, 0.006], 0.105, 0.023, side * -0.6, gold);
    }

    // A purpose-built wooden carving: one weathered material over the entire
    // figure, empty gouged sockets, and a rigid head seated on a timber neck.
    this.effigy = new ShrineEffigy(scene, this.root);
    c.box(this.root, "phra_phum_figure_plinth", [0.36, 0.025, 0.27], [0, 1.29, -0.11], timber);
    // Ash, spent incense, uneven wax, and withered offerings, all real geometry.
    c.cylinder(this.root, "phra_phum_incense_bowl", 0.17, 0.055, [0, 1.17, 0.39], gold);
    c.cylinder(this.root, "phra_phum_incense_ash", 0.145, 0.008, [0, 1.2, 0.39], ash);
    const random = seededRandom(59132);
    for (let k = 0; k < 9; k++) {
      const x = (random() - 0.5) * 0.1,
        z = 0.39 + (random() - 0.5) * 0.09;
      c.tube(
        this.root,
        "phra_phum_spent_incense",
        [
          [x, 1.2, z],
          [x + (random() - 0.5) * 0.015, 1.24 + random() * 0.14, z],
        ],
        0.0019,
        dead,
      );
    }
    for (const side of [-1, 1]) {
      const x = side * 0.44;
      c.cylinder(this.root, "phra_phum_candle_dish", 0.12, 0.018, [x, 1.15, 0.35], gold);
      c.cylinder(this.root, "phra_phum_candle", 0.047, 0.11, [x, 1.21, 0.35], wax);
      for (let k = 0; k < 4; k++)
        this.sphere(
          this.root,
          "phra_phum_wax_drip",
          [0.008, 0.025 + random() * 0.04, 0.009],
          [x + Math.cos(k * 1.7) * 0.022, 1.21, 0.35 + Math.sin(k * 1.7) * 0.022],
          wax,
        );
      const flame = this.sphere(
        this.root,
        "phra_phum_flame",
        [0.014, 0.041, 0.014],
        [x, 1.285, 0.35],
        this.ember,
      );
      flame.isPickable = false;
      this.flames.push(flame);
      this.garland(side, faded, dead, cloth);
    }
    // Surface damage at actual masonry scale, not a repeating crack decal.
    c.tube(
      this.root,
      "phra_phum_pedestal_crack",
      [
        [0.07, 0.91, 0.197],
        [0.08, 0.77, 0.198],
        [0.04, 0.66, 0.198],
        [0.06, 0.53, 0.198],
      ],
      0.002,
      black,
    );
    this.mergeStatic();
    this.root.position.copyFrom(position);
    // One low collider preserves walking clearance and cannot trap Sora in the doorway.
    const collider = c.box(
      this.root,
      "phra_phum_solid_pedestal",
      [1.34, 1.2, 1.05],
      [0, 0.6, 0],
      stone,
    );
    collider.isVisible = false;
    collider.isPickable = false;
    addStaticBox(collider, "stone");
    const light = (this.light = new PointLight(
      "phra_phum_votive_light",
      new Vector3(0, 1.4, 0.4),
      scene,
    ));
    light.parent = this.root;
    light.diffuse.set(1, 0.57, 0.2);
    light.specular.set(0.8, 0.5, 0.2);
    light.intensity = 0.34;
    light.range = 3.4;
    light.shadowEnabled = false;
    light.includedOnlyMeshes = this.root.getChildMeshes();
    scene.onBeforeRenderObservable.add(() => this.update(game.deltaSeconds));
  }

  async makeSounds(): Promise<void> {
    const audio = this.game.audio;
    if (!audio) return;
    const rate = audio.context.sampleRate;
    this.sound = await audio.spatialSound(
      "phra_phum_response",
      audio.buffer(spiritRattle(rate, seededRandom(59133)), rate),
      "sfx",
      this.root.position.add(new Vector3(0, 1.55, 0)),
      { minDistance: 1, maxDistance: 12, volume: 0.22 },
    );
    this.sound.playbackRate = 0.72;
    this.creak = await audio.spatialSound(
      "phra_phum_inside_knock",
      audio.buffer(boardCreak(rate, seededRandom(59134)), rate),
      "threat",
      this.root.position.add(new Vector3(0.24, 1.83, 0)),
      { minDistance: 1, maxDistance: 12, volume: 0.32 },
    );
    this.breath = await audio.spatialSound(
      "phra_phum_cavity_breath",
      audio.buffer(rattlingBreath(rate, seededRandom(59135)), rate),
      "threat",
      this.root.position.add(new Vector3(0, 1.57, -0.1)),
      { minDistance: 1, maxDistance: 12, volume: 0.38 },
    );
    this.breath.playbackRate = 0.8;
  }

  get interacting(): boolean {
    return this.response.active;
  }
  get silence(): number {
    return this.response.silence;
  }
  saving(): void {
    this.response.begin();
  }
  settled(success: boolean): void {
    this.response.settle(success);
    if (!success) {
      this.sound?.stop();
      this.creak?.stop();
      this.breath?.stop();
    }
  }

  private update(dt: number): void {
    this.time += dt;
    if ((this.game.threatActive || this.game.cutscene) && this.response.active) {
      this.response.cancel();
      this.sound?.stop();
      this.creak?.stop();
      this.breath?.stop();
    }
    for (const cue of this.response.update(dt)) {
      if (cue === "knock") this.creak?.play();
      if (cue === "breath") this.breath?.play();
      if (cue === "ring") this.sound?.play();
    }
    const darkness = this.response.darkness,
      turn = this.response.turn;
    const flicker = 1 + Math.sin(this.time * 13.7) * Math.sin(this.time * 8.9) * 0.07;
    this.light.intensity = 0.34 * (1 - darkness * 0.965) * flicker;
    this.light.diffuse.set(1, 0.57 - darkness * 0.2, 0.2 - darkness * 0.12);
    this.ember.emissiveColor.set(
      2.6 * (1 - darkness * 0.98),
      0.95 * (1 - darkness),
      0.16 * (1 - darkness),
    );
    for (const [i, flame] of this.flames.entries()) {
      flame.scaling.y =
        0.041 * (flicker + Math.sin(this.time * 17 + i) * 0.08) * (1 - darkness * 0.97);
      flame.rotation.z = Math.sin(this.time * 6.1 + i) * 0.05 + darkness * 0.45;
    }
    this.effigy.update(turn);
    for (const [i, ribbon] of this.ribbons.entries())
      ribbon.rotation.z = Math.sin(this.time * 0.7 + i * 1.8) * (0.008 + turn * 0.035);
  }

  private pillar(x: number, z: number, gold: PBRMaterial, edge: PBRMaterial, rail = false): void {
    const c = this.craft,
      y = rail ? 1.25 : 1.61,
      h = rail ? 0.2 : 0.64;
    const width = rail ? 0.029 : 0.055;
    c.box(this.root, "phra_phum_square_timber_post", [width, h, width], [x, y, z], gold);
    for (const dy of [-h * 0.44, h * 0.44])
      c.box(
        this.root,
        "phra_phum_mortise_collar",
        [width * 1.4, 0.027, width * 1.4],
        [x, y + dy, z],
        edge,
      );
  }

  private garland(side: number, flower: PBRMaterial, dead: PBRMaterial, cloth: PBRMaterial): void {
    const c = this.craft,
      x = side * 0.55;
    const root = c.root("phra_phum_hanging_garland", [x, 1.21, 0.52], this.root);
    this.ribbons.push(root);
    const random = seededRandom(1340 + side);
    for (const [material, dying] of [
      [flower, false],
      [dead, true],
    ] as const) {
      const positions: number[] = [],
        indices: number[] = [],
        uvs: number[] = [];
      for (let k = 0; k < 26; k++) {
        if ((k % 7 === 0) !== dying || k === 19) continue;
        const centre = new Vector3(Math.sin(k * 0.4) * 0.012, -0.045 - k * 0.019, 0);
        for (let petal = 0; petal < 7; petal++) {
          const a = (petal / 7) * Math.PI * 2 + k,
            r = 0.018 + random() * 0.008;
          const n = positions.length / 3;
          positions.push(
            centre.x,
            centre.y,
            centre.z,
            centre.x + Math.cos(a - 0.36) * r,
            centre.y - 0.008,
            centre.z + Math.sin(a - 0.36) * r,
            centre.x + Math.cos(a) * r * 1.25,
            centre.y + 0.007,
            centre.z + Math.sin(a) * r * 1.25,
            centre.x + Math.cos(a + 0.36) * r,
            centre.y - 0.008,
            centre.z + Math.sin(a + 0.36) * r,
          );
          indices.push(n, n + 1, n + 2, n, n + 2, n + 3);
          uvs.push(0, 0, 0, 1, 1, 1, 1, 0);
        }
      }
      material.backFaceCulling = false;
      this.surface("phra_phum_withered_flower_petals", positions, indices, uvs, root, material);
    }
    const positions: number[] = [],
      indices: number[] = [],
      uvs: number[] = [];
    for (let j = 0; j <= 24; j++) {
      const t = j / 24,
        bend = Math.sin(t * 7 + side) * 0.014;
      for (const sign of [-1, 1]) {
        positions.push(
          0.045 * side + bend + sign * 0.018 * (1 - 0.2 * t),
          -t * 0.66,
          Math.sin(t * 12) * 0.02,
        );
        uvs.push(sign > 0 ? 1 : 0, t * 4);
      }
      if (j < 24) {
        const a = j * 2;
        indices.push(a, a + 2, a + 1, a + 1, a + 2, a + 3);
      }
    }
    cloth.backFaceCulling = false;
    this.surface("phra_phum_torn_ribbon", positions, indices, uvs, root, cloth);
  }

  private sphere(
    parent: TransformNode,
    name: string,
    size: XYZ,
    at: XYZ,
    material: PBRMaterial,
  ): Mesh {
    const mesh = this.craft.finish(
      CreateSphere(name, { diameter: 1, segments: 10 }, this.game.scene),
      parent,
      at,
      material,
    );
    mesh.scaling.set(...size);
    return mesh;
  }

  private surface(
    name: string,
    positions: number[],
    indices: number[],
    uvs: number[],
    parent: TransformNode,
    material: PBRMaterial,
  ): void {
    const normals: number[] = [];
    VertexData.ComputeNormals(positions, indices, normals);
    const data = new VertexData();
    data.positions = positions;
    data.indices = indices;
    data.normals = normals;
    data.uvs = uvs;
    const mesh = new Mesh(name, this.game.scene);
    data.applyToMesh(mesh);
    mesh.parent = parent;
    mesh.material = material;
    this.craft.meshes.push(mesh);
  }

  private mergeStatic(): void {
    const groups = new Map<PBRMaterial, Mesh[]>();
    for (const mesh of this.craft.meshes) {
      mesh.receiveShadows = true;
      const staticParent =
        mesh.parent === this.root || mesh.parent?.name.startsWith("phra_phum_roof_wing_");
      if (!staticParent || this.flames.includes(mesh)) continue;
      const mat = mesh.material as PBRMaterial,
        group = groups.get(mat) ?? [];
      group.push(mesh);
      groups.set(mat, group);
    }
    for (const [material, meshes] of groups) {
      const merged = Mesh.MergeMeshes(meshes, true, true);
      if (!merged) continue;
      merged.name = `phra_phum_${material.name}`;
      merged.setParent(this.root);
      merged.receiveShadows = true;
    }
  }
}
