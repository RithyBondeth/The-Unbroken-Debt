import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import type { AssetContainer } from "@babylonjs/core/assetContainer";
import { LoadAssetContainerAsync } from "@babylonjs/core/Loading/sceneLoader";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import type { Mesh } from "@babylonjs/core/Meshes/mesh";
import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import { CreateBox } from "@babylonjs/core/Meshes/Builders/boxBuilder";
import { CreateSphere } from "@babylonjs/core/Meshes/Builders/sphereBuilder";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { PointLight } from "@babylonjs/core/Lights/pointLight";
import { ShadowGenerator } from "@babylonjs/core/Lights/Shadows/shadowGenerator";
import { RenderTargetTexture } from "@babylonjs/core/Materials/Textures/renderTargetTexture";
import "@babylonjs/core/Lights/Shadows/shadowGeneratorSceneComponent";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { Scene } from "@babylonjs/core/scene";
import type { Game } from "@/core/Game";
import { realiseInstances } from "@/core/areaLoader";
import { addStaticBox } from "@/core/physics";
import { boardCreak, rattlingBreath, seededRandom } from "@/audio/synth";
import type { DreadScore } from "@/audio/DreadScore";
import { spiritRattle } from "../audio/presenceSounds";
import { ShrineResponse } from "./ShrineResponse";
import type { SavePointAppearance } from "@/systems/saves/SavePoint";

const templates = new WeakMap<Scene, AssetContainer>();

/** The three wicks marked in the asset (tools/areas/build-phra-phum.py). */
const WICKS = ["left", "right", "inner"] as const;
type Wick = (typeof WICKS)[number];

/**
 * The family's Preah Phum: a carved teak spirit house of the 1930s, its red
 * lacquer and gilt worn to grey wood, on a turned post over a laterite block
 * (public/assets/ep1/phra_phum.glb). Two candles burn on the porch; inside,
 * the soot-black chamber is empty but for one candle. Paying respects saves:
 * the porch candles sink, something knocks inside, and the candle in the
 * chamber leans out toward Sora and drowns before it rights itself.
 */
export class PhraPhum implements SavePointAppearance {
  readonly root: TransformNode;
  readonly hint = "hint.saveShrine" as const;
  readonly hintMeshes: readonly AbstractMesh[];
  /** The left porch candle: it alone casts the shrine's cached shadow. */
  readonly light: PointLight;
  private readonly companionLight: PointLight;
  private readonly innerLight: PointLight;
  private readonly response = new ShrineResponse();
  private readonly flames = new Map<Wick, Mesh>();
  private readonly ember: PBRMaterial;
  private readonly innerEmber: PBRMaterial;
  private sound: StaticSound | null = null;
  private creak: StaticSound | null = null;
  private breath: StaticSound | null = null;
  private time = 0;
  private readonly shadows: ShadowGenerator | null;

  static async prepare(scene: Scene): Promise<void> {
    if (templates.has(scene)) return;
    const asset = await LoadAssetContainerAsync(
      `${import.meta.env.BASE_URL}assets/ep1/phra_phum.glb`,
      scene,
    );
    realiseInstances(asset);
    asset.removeAllFromScene();
    for (const material of asset.materials)
      if (material instanceof PBRMaterial) material.maxSimultaneousLights = 8;
    templates.set(scene, asset);
    scene.onDisposeObservable.addOnce(() => asset.dispose());
  }

  constructor(
    private readonly game: Game,
    position: Vector3,
  ) {
    const scene = game.scene;
    const template = templates.get(scene);
    if (!template) throw new Error("Prepare the spirit house before building it");
    this.root = new TransformNode("house_front_right_phra_phum", scene);
    this.root.position.copyFrom(position);
    const copy = template.instantiateModelsToScene((name) => name, false, {
      doNotInstantiate: true,
    });
    for (const node of copy.rootNodes) node.parent = this.root;
    this.root.computeWorldMatrix(true);
    const meshes = this.root.getChildMeshes(false);
    const wicks = new Map<Wick, Vector3>();
    for (const node of this.root.getDescendants(false)) {
      const wick = WICKS.find((w) => node.name === `phra_phum_wick_${w}`);
      if (!wick || !(node instanceof TransformNode)) continue;
      node.computeWorldMatrix(true);
      wicks.set(wick, node.getAbsolutePosition().subtract(position));
    }
    if (wicks.size !== WICKS.length)
      throw new Error("The spirit house is missing its candle wicks");
    for (const mesh of meshes) {
      mesh.receiveShadows = true;
      // Veils of web are seen through; they never stop the interaction ray.
      if (mesh.name.includes("cobweb")) mesh.isPickable = false;
    }
    this.hintMeshes = meshes.filter((mesh) => mesh.material?.name.includes("offering_clay"));

    this.ember = new PBRMaterial("phra_phum_candle_light", scene);
    this.ember.unlit = true;
    this.ember.emissiveColor.set(2.6, 0.95, 0.16);
    this.innerEmber = this.ember.clone("phra_phum_inner_candle_light");
    for (const wick of WICKS) {
      const flame = CreateSphere(`phra_phum_flame_${wick}`, { diameter: 1, segments: 10 }, scene);
      flame.parent = this.root;
      flame.position.copyFrom(wicks.get(wick)!.add(new Vector3(0, 0.011, 0)));
      flame.scaling.set(0.012, 0.036, 0.012);
      flame.material = wick === "inner" ? this.innerEmber : this.ember;
      flame.isPickable = false;
      this.flames.set(wick, flame);
    }

    // One low collider preserves walking clearance and cannot trap Sora in the doorway.
    const collider = CreateBox(
      "phra_phum_solid_pedestal",
      { width: 1.34, height: 1.2, depth: 1.05 },
      scene,
    );
    collider.parent = this.root;
    collider.position.y = 0.6;
    collider.isVisible = false;
    collider.isPickable = false;
    addStaticBox(collider, "teak");

    const lit = meshes.filter((mesh) => mesh.isVisible);
    const candle = (name: string, wick: Wick, intensity: number, range: number) => {
      const light = new PointLight(name, wicks.get(wick)!.add(new Vector3(0, 0.012, 0)), scene);
      light.parent = this.root;
      light.diffuse.set(1, 0.5, 0.16);
      light.specular.set(0.5, 0.25, 0.07);
      light.intensity = intensity;
      light.range = range;
      light.includedOnlyMeshes = lit;
      light.shadowEnabled = false;
      return light;
    };
    // Two porch candles give asymmetric grazing light; only the left one casts a
    // cached, shrine-only shadow map. The chamber's candle lights the black inside.
    this.light = candle("phra_phum_votive_light", "left", 0.28, 3.2);
    this.light.shadowMinZ = 0.035;
    this.light.shadowMaxZ = 3.2;
    this.companionLight = candle("phra_phum_right_candle", "right", 0.13, 2.3);
    this.companionLight.diffuse.set(1, 0.43, 0.12);
    this.innerLight = candle("phra_phum_inner_candle", "inner", 0.07, 1.4);
    this.shadows =
      game.preset.shadowedFlames > 0
        ? new ShadowGenerator(Math.min(512, game.preset.flameShadowMapSize), this.light)
        : null;
    this.light.shadowEnabled = this.shadows !== null;
    if (this.shadows) {
      this.shadows.usePoissonSampling = true;
      this.shadows.bias = 0.0006;
      this.shadows.normalBias = 0.002;
      this.shadows.darkness = 0.12;
      const map = this.shadows.getShadowMap()!;
      map.renderList = lit.filter((mesh) => !mesh.name.includes("cobweb"));
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
      // Something inside draws on the chamber's candle: it leans out and drowns.
      draw = this.response.turn;
    const flicker = 0.94 + Math.sin(this.time * 13.7) * Math.sin(this.time * 8.9) * 0.08;
    const companionFlicker = 0.9 + Math.sin(this.time * 11.3 + 2) * Math.sin(this.time * 7.1) * 0.1;
    const innerFlicker = 0.92 + Math.sin(this.time * 9.1 + 4) * Math.sin(this.time * 15.3) * 0.08;
    this.light.intensity = 0.28 * (1 - darkness * 0.965) * flicker;
    this.companionLight.intensity = 0.13 * (1 - darkness * 0.985) * companionFlicker;
    this.innerLight.intensity = 0.07 * (1 - draw * 0.97) * innerFlicker * (1 - darkness * 0.4);
    this.light.diffuse.set(1, 0.5 - darkness * 0.17, 0.16 - darkness * 0.1);
    this.ember.emissiveColor.set(
      2.6 * (1 - darkness * 0.98),
      0.95 * (1 - darkness),
      0.16 * (1 - darkness),
    );
    this.innerEmber.emissiveColor.set(2.6 * (1 - draw * 0.9), 0.95 * (1 - draw), 0.16 * (1 - draw));
    for (const [wick, flame] of this.flames) {
      if (wick === "inner") {
        flame.scaling.y =
          0.036 * (innerFlicker + Math.sin(this.time * 19) * 0.06) * (1 - draw * 0.8);
        // Leaning out of the doorway (+Z), toward whoever stands at the shrine.
        flame.rotation.x = Math.sin(this.time * 5.3) * 0.04 + draw * 0.9;
        continue;
      }
      const wickFlicker = wick === "left" ? flicker : companionFlicker;
      flame.scaling.y =
        0.036 *
        (wickFlicker + Math.sin(this.time * 17 + (wick === "left" ? 0 : 1)) * 0.08) *
        (1 - darkness * 0.97);
      flame.rotation.z =
        Math.sin(this.time * 6.1 + (wick === "left" ? 0 : 1)) * 0.05 + darkness * 0.45;
    }
  }
}
