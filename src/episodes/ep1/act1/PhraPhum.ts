import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import type { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import { CreateSphere } from "@babylonjs/core/Meshes/Builders/sphereBuilder";
import type { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { PointLight } from "@babylonjs/core/Lights/pointLight";
import { ShadowGenerator } from "@babylonjs/core/Lights/Shadows/shadowGenerator";
import { RenderTargetTexture } from "@babylonjs/core/Materials/Textures/renderTargetTexture";
import "@babylonjs/core/Lights/Shadows/shadowGeneratorSceneComponent";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { Game } from "../../../core/Game";
import { addStaticBox } from "../../../core/Physics";
import { boardCreak, rattlingBreath, seededRandom } from "../../../audio/synth";
import type { DreadScore } from "../audio/DreadScore";
import { spiritRattle } from "../audio/presenceSounds";
import { ShrineWoodwork } from "./ShrineWoodwork";
import { agedShrineTimber, mapShrineGrain, ShrineAgeing } from "./ShrineAgeing";
import { ShrineResponse } from "./ShrineResponse";
import { ShrineEffigy } from "./ShrineEffigy";
import { RelicCraft } from "../act3/RelicCraft";
import type { SavePointAppearance } from "../../../systems/saves/SavePoint";

type XYZ = [number, number, number];

/** A modest household spirit house: reclaimed boards, one plain roof and a
 * hewn post. The recessed wooden figure and candlelight keep it unsettling. */
export class PhraPhum implements SavePointAppearance {
  readonly root: TransformNode;
  readonly hint = "hint.saveShrine" as const;
  readonly hintMeshes: readonly AbstractMesh[];
  readonly light: PointLight;
  private readonly craft: RelicCraft;
  private readonly effigy: ShrineEffigy;
  private readonly response = new ShrineResponse();
  private readonly flames: Mesh[] = [];
  private readonly ember: PBRMaterial;
  private sound: StaticSound | null = null;
  private creak: StaticSound | null = null;
  private breath: StaticSound | null = null;
  private time = 0;
  private readonly companionLight: PointLight;
  private readonly shadows: ShadowGenerator | null;
  private shadowTurn = 0;

  constructor(
    private readonly game: Game,
    position: Vector3,
  ) {
    const scene = game.scene;
    const c = (this.craft = new RelicCraft(scene));
    this.root = c.root("house_front_right_phra_phum", [0, 0, 0]);
    const timber = agedShrineTimber(scene);
    const repair = timber.clone("M_phra_phum_reclaimed_repair_wood");
    repair.albedoColor.set(0.56, 0.51, 0.44);
    const red = timber.clone("M_phra_phum_smoke_weathered_shingles");
    red.albedoColor.set(0.43, 0.36, 0.28);
    const clay = c.mat("phra_phum_offering_clay", "#70503b", 0.98);
    const woodwork = new ShrineWoodwork(c, this.root);
    const ageing = new ShrineAgeing(c, this.root);
    const stone = c.mat("phra_phum_old_laterite_footing", "#51483b", 1);
    const black = c.mat("phra_phum_recesses", "#080a08", 1);
    const ash = c.mat("phra_phum_ash", "#514b3f", 1);
    const dead = c.mat("phra_phum_charred_incense", "#4c3523", 1);
    const wax = c.mat("phra_phum_old_wax", "#c4aa77", 0.9);
    this.ember = c.mat("phra_phum_candle_light", "#ffffff");
    this.ember.unlit = true;
    this.ember.emissiveColor.set(2.6, 0.95, 0.16);

    // A reused stone and one hewn post support a plain plank offering tray.
    c.box(this.root, "phra_phum_foot", [0.48, 0.08, 0.43], [0, 0.04, 0], stone);
    ageing.pedestal(timber, repair, black);
    for (const z of [-0.31, 0.31])
      c.box(this.root, "phra_phum_tray_cross_bearer", [1.22, 0.065, 0.07], [0, 1.045, z], timber);
    for (let k = 0; k < 5; k++)
      c.box(
        this.root,
        "phra_phum_offering_tray_board",
        [1.23, 0.045, 0.19],
        [0, 1.1025, (k - 2) * 0.194],
        k === 1 ? repair : timber,
      );
    for (const x of [-0.607, 0.607])
      c.box(this.root, "phra_phum_terrace_rim", [0.025, 0.045, 0.98], [x, 1.148, 0], timber);
    c.box(this.root, "phra_phum_front_rim", [1.23, 0.045, 0.025], [0, 1.148, 0.48], timber);
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
      timber,
    );
    for (const side of [-1, 1]) {
      c.box(this.root, "phra_phum_side_wall", [0.04, 0.64, 0.57], [side * 0.325, 1.61, -0.05], red);
      for (const z of [-0.32, 0.28]) {
        this.pillar(side * 0.355, z, timber);
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
    woodwork.household(timber, red, repair);

    // A purpose-built wooden carving: one weathered material over the entire
    // figure, empty gouged sockets, and a rigid head seated on a timber neck.
    this.effigy = new ShrineEffigy(scene, this.root);
    c.box(this.root, "phra_phum_figure_plinth", [0.36, 0.025, 0.27], [0, 1.29, -0.11], timber);
    // Ash, spent incense, uneven wax, and withered offerings, all real geometry.
    c.cylinder(this.root, "phra_phum_incense_bowl", 0.17, 0.055, [0, 1.17, 0.39], clay);
    c.cylinder(this.root, "phra_phum_incense_ash", 0.145, 0.008, [0, 1.2, 0.39], ash);
    const random = seededRandom(59132);
    for (let k = 0; k < 3; k++) {
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
      c.cylinder(this.root, "phra_phum_candle_dish", 0.12, 0.018, [x, 1.15, 0.35], clay);
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
    }
    const moss = c.surface("phra_phum_dry_joint_lichen", "#414733", "wood");
    const silk = c.mat("phra_phum_dusty_cobweb_silk", "#8d897b", 1);
    silk.alpha = 0.32;
    silk.backFaceCulling = false;
    ageing.dress(timber, black, moss, wax, silk);
    const woodMaterials = new Set([timber, repair, red, chamber]);
    for (const [i, mesh] of c.meshes.entries())
      if (woodMaterials.has(mesh.material as PBRMaterial)) mapShrineGrain(mesh, 1900 + i);
    this.mergeStatic();
    this.hintMeshes = this.root.getChildMeshes().filter((mesh) => mesh.material === clay);
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
    addStaticBox(collider, "teak");
    // Two candle positions produce asymmetric grazing light. Only the left
    // flame casts a cached, shrine-only shadow map; foliage never enters it.
    const meshes = this.root.getChildMeshes().filter((mesh) => mesh.isVisible);
    const light = (this.light = new PointLight(
      "phra_phum_votive_light",
      new Vector3(-0.44, 1.29, 0.35),
      scene,
    ));
    light.parent = this.root;
    light.diffuse.set(1, 0.5, 0.16);
    light.specular.set(0.6, 0.3, 0.08);
    light.intensity = 0.28;
    light.range = 3.2;
    light.shadowMinZ = 0.035;
    light.shadowMaxZ = 3.2;
    light.includedOnlyMeshes = meshes;
    const companion = (this.companionLight = new PointLight(
      "phra_phum_right_candle",
      new Vector3(0.44, 1.29, 0.35),
      scene,
    ));
    companion.parent = this.root;
    companion.diffuse.set(1, 0.43, 0.12);
    companion.specular.set(0.4, 0.18, 0.05);
    companion.intensity = 0.13;
    companion.range = 2.3;
    companion.shadowEnabled = false;
    companion.includedOnlyMeshes = meshes;
    this.shadows =
      game.preset.shadowedFlames > 0
        ? new ShadowGenerator(Math.min(512, game.preset.flameShadowMapSize), light)
        : null;
    light.shadowEnabled = this.shadows !== null;
    if (this.shadows) {
      this.shadows.usePoissonSampling = true;
      this.shadows.bias = 0.0006;
      this.shadows.normalBias = 0.002;
      this.shadows.darkness = 0.12;
      const map = this.shadows.getShadowMap()!;
      map.renderList = meshes.filter(
        (mesh) => mesh.material !== this.ember && mesh.material !== silk,
      );
      map.refreshRate = RenderTargetTexture.REFRESHRATE_RENDER_ONCE;
    }
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

  /** The act's stingers, once they are made (ActOne). */
  score: DreadScore | null = null;

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
      if (cue === "ring") {
        this.sound?.play();
        this.score?.sting("drop", 0.55);
      }
    }
    const darkness = this.response.darkness,
      turn = this.response.turn;
    const flicker = 0.94 + Math.sin(this.time * 13.7) * Math.sin(this.time * 8.9) * 0.08;
    const companionFlicker = 0.9 + Math.sin(this.time * 11.3 + 2) * Math.sin(this.time * 7.1) * 0.1;
    this.light.intensity = 0.28 * (1 - darkness * 0.965) * flicker;
    this.companionLight.intensity = 0.13 * (1 - darkness * 0.985) * companionFlicker;
    this.light.diffuse.set(1, 0.5 - darkness * 0.17, 0.16 - darkness * 0.1);
    this.ember.emissiveColor.set(
      2.6 * (1 - darkness * 0.98),
      0.95 * (1 - darkness),
      0.16 * (1 - darkness),
    );
    for (const [i, flame] of this.flames.entries()) {
      const wick = i === 0 ? flicker : companionFlicker;
      flame.scaling.y =
        0.041 * (wick + Math.sin(this.time * 17 + i) * 0.08) * (1 - darkness * 0.97);
      flame.rotation.z = Math.sin(this.time * 6.1 + i) * 0.05 + darkness * 0.45;
    }
    this.effigy.update(turn);
    // Brightness flicker reuses the cached map. Refresh only when the rigid
    // wooden head visibly moves, including its final return to the idle pose.
    if (Math.abs(turn - this.shadowTurn) > 0.04 || (turn === 0 && this.shadowTurn !== 0)) {
      this.shadowTurn = turn;
      this.shadows?.getShadowMap()?.resetRefreshCounter();
    }
  }

  private pillar(x: number, z: number, timber: PBRMaterial): void {
    this.craft.box(
      this.root,
      "phra_phum_square_timber_post",
      [0.055, 0.64, 0.055],
      [x, 1.61, z],
      timber,
    );
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

  private mergeStatic(): void {
    const groups = new Map<PBRMaterial, Mesh[]>();
    for (const mesh of this.craft.meshes) {
      mesh.receiveShadows = true;
      if (mesh.parent !== this.root || this.flames.includes(mesh)) continue;
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
