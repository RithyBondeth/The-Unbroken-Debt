import type { Game } from "@/core/Game";
import type { Scene } from "@babylonjs/core/scene";
import { LoadAssetContainerAsync } from "@babylonjs/core/Loading/sceneLoader";
import type { AssetContainer } from "@babylonjs/core/assetContainer";
import { registerBuiltInLoaders } from "@babylonjs/loaders/dynamic";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { StandardMaterial } from "@babylonjs/core/Materials/standardMaterial";
import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import { MirrorTexture } from "@babylonjs/core/Materials/Textures/mirrorTexture";
import { RenderTargetTexture } from "@babylonjs/core/Materials/Textures/renderTargetTexture";
import { FreeCamera } from "@babylonjs/core/Cameras/freeCamera";
import type { Texture } from "@babylonjs/core/Materials/Textures/texture";
import { RawTexture } from "@babylonjs/core/Materials/Textures/rawTexture";
import { Color3, Color4 } from "@babylonjs/core/Maths/math.color";
import { Plane } from "@babylonjs/core/Maths/math.plane";
import { Quaternion, Vector3 } from "@babylonjs/core/Maths/math.vector";
import { CreateBox } from "@babylonjs/core/Meshes/Builders/boxBuilder";
import { CreateCylinder } from "@babylonjs/core/Meshes/Builders/cylinderBuilder";
import { CreatePlane } from "@babylonjs/core/Meshes/Builders/planeBuilder";
import { PointLight } from "@babylonjs/core/Lights/pointLight";
import type { MorphTarget } from "@babylonjs/core/Morph/morphTarget";
import { taxiDriverFace, type DriverFace } from "./taxiDriver";
import { HemisphericLight } from "@babylonjs/core/Lights/hemisphericLight";
import { DirectionalLight } from "@babylonjs/core/Lights/directionalLight";
import { SpotLight } from "@babylonjs/core/Lights/spotLight";
import { ShadowGenerator } from "@babylonjs/core/Lights/Shadows/shadowGenerator";
import { realiseInstances } from "@/core/areaLoader";
import { mergeStaticMeshes } from "@/render/staticBatcher";
import { addStaticBox } from "@/core/physics";
import { buildTaxiRoadside } from "./taxiRoadside";
import { StormSky } from "@/render/weather/StormSky";
import { MocapFigure } from "@/shared/entities/MocapFigure";
import { Preay } from "../entities/Preay";
import { NIGHT_LOOK } from "@/render/nightLook";
import { applyRainWetness } from "@/render/surfaceDetail";
import { TaxiWeather } from "./TaxiWeather";
import { applyFoliageWind } from "@/render/FoliageWind";
import { gradeJungle } from "../act1/jungleGrade";
import { TaxiRain } from "./TaxiRain";
import {
  TAXI_FOREST_START,
  TAXI_GROUND_DROP,
  TAXI_PADDY_END,
  TAXI_PADDY_WATER,
  taxiDistance,
  taxiRoadPose,
  taxiRoadX,
  taxiRouteChunkVisible,
  taxiSpeed,
  taxiWiperAngle,
} from "./taxiMotion";
import {
  TAXI_MIRROR,
  taxiElectrics,
  taxiFlinch,
  taxiMirrorRiderAt,
  taxiSpiritAt,
  taxiSwerve,
} from "./taxiApparitions";
import { TaxiMist } from "./TaxiMist";
import { buildTaxiFarForest, thickenTaxiUnderstorey } from "./taxiForestDepth";
import { ageTaxiCabin } from "./taxiCabinWear";
import { TaxiGlassMarks } from "./TaxiGlassMarks";

/** A layer the player's camera never draws (its mask is the default 0x0FFFFFFF). */
const MIRROR_ONLY = 0x10000000;
/** Leaf materials the headlamps reach, and how much deeper and greener they are graded here. */
const FOLIAGE_IN_THE_LAMPS =
  /^(M_forest_leaf|fern_02|shrub_02|M_bamboo_leaves|M_palm_fan|M_forest_grass|M_taxi_rice|banana_leef)$/;
const HEADLAMP_LEAF_TINT = new Color3(0.5, 0.56, 0.36);

/**
 * A position the cabin GLB marks with an empty (build-taxi.py `anchor`): lamps, glass,
 * wipers, mirror, dials and Sora's eyes, measured from the Rosalie itself.
 */
function anchorAt(scene: Scene, name: string, fallback: Vector3): Vector3 {
  const node = scene.getTransformNodeByName(`taxi_anchor_${name}`);
  if (!node) return fallback;
  node.computeWorldMatrix(true);
  return node.getAbsolutePosition().clone();
}

/**
 * The roadside meshes a small light can reach (route frame, at load): a candle or a lamp
 * lights only these, not every pixel of the forest.
 */
function within(meshes: readonly AbstractMesh[], at: Vector3, range: number): AbstractMesh[] {
  return meshes.filter((m) => {
    const box = m.getBoundingInfo().boundingBox;
    const nearest = Vector3.Clamp(at, box.minimumWorld, box.maximumWorld);
    return Vector3.Distance(nearest, at) < range;
  });
}

/** The five period instruments across the Rosalie's cluster: centre, as a fraction of its width. */
const DIALS = [0.115, 0.3, 0.5, 0.7, 0.885] as const;

/** The fog behind the car as the rear-view mirror shows it (linear). */
const MIRROR_FOG = [0.055, 0.072, 0.098] as const;

/** Authored cabin, Act I foliage/materials, physical headlights and the same storm grade. */
export class TaxiVisuals {
  readonly route: TransformNode;
  private readonly routeChunks: {
    mesh: AbstractMesh;
    minZ: number;
    maxZ: number;
    active: boolean;
    /** How far ahead it stays on: across the open paddies, all the way to the haze. */
    ahead: number;
  }[] = [];
  /** The oil lamp in the stilt house's window, and its flicker. */
  private readonly houseLamp: PointLight | null = null;
  /** Hanging warm practical bulbs under the roadside wooden shops and Khmer 90s poster boards. */
  private readonly roadsideLamps: {
    light: PointLight;
    base: number;
    z: number;
    phase: number;
    isShop: boolean;
  }[] = [];
  /** The left lamp's shadows, and the roadside that may cast into them. */
  private headlampShadow: ShadowGenerator | null = null;
  private shadowCasters: AbstractMesh[] = [];
  private shadowStretch = Number.NaN;
  /** The candle at the Neak Ta's shrine. */
  private readonly shrineCandle: PointLight | null = null;
  private readonly mist: TaxiMist;
  private readonly headlamps: { light: SpotLight; power: number }[] = [];
  private readonly dash: PointLight;
  private readonly domeLight: PointLight;
  private readonly soraFill: PointLight;
  private readonly footwellLight: PointLight;
  private readonly roadBounce: PointLight;
  private readonly cabinShopSweep: PointLight;
  private readonly radioDialMat: PBRMaterial | null = null;
  private readonly domeGlassMat: PBRMaterial | null = null;
  private readonly footwellBulbMat: PBRMaterial | null = null;
  private readonly dials: StandardMaterial;
  /** The sculpted steering wheel pivot and its neutral quaternion, spun live with road turns & swerves. */
  private readonly wheel: TransformNode | null = null;
  private readonly wheelBase: Quaternion | null = null;
  private wheelAngle = 0;
  /** The form that stands by the road, and later runs at Sora's window. */
  /** The black Neak Ta on the road, moving on motion capture. */
  private readonly spirit: MocapFigure;
  /** Frames left to draw it out of sight below the road, so it compiles before it is needed. */
  private spiritWarm = 4;
  /**
   * Lightning through the windscreen and Sora's glass, falling on its face when it is at
   * the car: the storm's own light comes from above and behind it and leaves only a hole.
   */
  private readonly spiritFill: PointLight;
  /** What sits behind Sora: the same Neak Ta, drawn into the rear-view mirror only, never into the cabin. */
  private readonly rider: MocapFigure;
  private readonly riderLights: PointLight[] = [];
  private readonly riderEyes: StandardMaterial;
  private readonly glassMarks: TaxiGlassMarks | null = null;
  private readonly wipers: TransformNode[] = [];
  private readonly sky: StormSky;
  private readonly flash: DirectionalLight;
  private readonly rain: TaxiWeather;
  private readonly glass: TaxiRain;
  private readonly dialTexture: DynamicTexture;
  private dialIn = 0;
  private readonly mirror: RenderTargetTexture;
  private readonly waterRipples: Texture;
  private bonnetBeads: Texture | null = null;
  private readonly charm: TransformNode | null;
  private readonly charmSwing = { side: 0, sideRate: 0, pitch: 0, pitchRate: 0 };
  private readonly driver: TransformNode | null = null;
  private lastYaw = 0;
  private lastSpeed = 6.8;
  private readonly blinkTargets: MorphTarget[] = [];
  /** The driver's other baked shapes by name, eased towards taxiDriverFace each frame. */
  private readonly faceTargets = new Map<keyof DriverFace, MorphTarget[]>();
  private readonly face: DriverFace = { talk: 0, look_road: 0, look_sora: 0, nod: 0, grip: 0 };
  private blinkAt = -10;
  private nextBlink = 1.4;
  /** Sora's eyes above the cabin floor. */
  private readonly eyeHeight: number;

  private constructor(
    private readonly game: Game,
    private readonly cabinMeshes: AbstractMesh[],
    route: TransformNode,
    landscape: Mesh[],
    spiritAsset: AssetContainer,
  ) {
    const scene = game.scene;
    this.route = route;
    // Old growth is not a row of trees: plant the understorey twice, and carry the
    // forest on past the authored ranks with Episode 2's far tree cards.
    const ground = scene.getMaterialByName("M_wet_forest_floor");
    const forest: AbstractMesh[] = [
      ...landscape,
      ...thickenTaxiUnderstorey(landscape),
      ...buildTaxiFarForest(scene, route, game.wind, ground),
    ];
    for (const mesh of forest) {
      mesh.computeWorldMatrix(true);
      const box = mesh.getBoundingInfo().boundingBox;
      this.routeChunks.push({
        mesh,
        minZ: box.minimumWorld.z,
        maxZ: box.maximumWorld.z,
        active: true,
        ahead: box.minimumWorld.z < TAXI_PADDY_END + 10 ? 170 : 80,
      });
    }
    const materials = new Set(landscape.map((mesh) => mesh.material));
    // The roadside was painted before the old-growth palette: grade all of it.
    gradeJungle(
      [...materials].filter((m) => m !== null),
      false,
    );
    applyFoliageWind(
      [...materials].filter((m) => m !== null),
      game.wind,
    );
    // Under headlamps a few metres off, the village's pale leaf tint burns to white
    // paper once the haze is thin. Wet old-growth leaves stay a deep, cold green.
    for (const material of materials)
      if (material instanceof PBRMaterial && FOLIAGE_IN_THE_LAMPS.test(material.name))
        material.albedoColor.multiplyInPlace(HEADLAMP_LEAF_TINT);
    // The village's hanging moss and liana strands are a flat pale grey; wet, at night,
    // they are near black, and must not hang in the lamps like white rods.
    const moss = scene.getMaterialByName("M_forest_moss");
    if (moss instanceof PBRMaterial) {
      moss.albedoColor.set(0.03, 0.036, 0.026);
      moss.roughness = 0.8;
    }
    // Young rice and median grass stay deep, dark wet jungle green without specular headlight sparks.
    const rice = scene.getMaterialByName("M_taxi_rice");
    if (rice instanceof PBRMaterial) {
      rice.albedoColor.multiplyInPlace(new Color3(0.42, 0.55, 0.36));
      rice.roughness = 0.76;
      rice.specularIntensity = 0.1;
    }
    const grass = scene.getMaterialByName("M_forest_grass");
    if (grass instanceof PBRMaterial) {
      // Un-textured median grass defaults to pure white; grade to deep wet night-time jungle blades
      // so the twin 2400-intensity headlamps never turn center-crown tufts into bright white sparks.
      grass.albedoColor.set(0.032, 0.048, 0.022);
      grass.roughness = 0.88;
      grass.specularIntensity = 0.04;
      grass.clearCoat.isEnabled = false;
    }
    // Pitch-dark monsoon storm night: only the car's headlamps, passing roadside shop bulbs,
    // shrine candle and lightning bolts carve shapes out of the black jungle and rain.
    const hemi = new HemisphericLight("taxi_storm_bounce", new Vector3(0.2, 1, -0.3), scene);
    hemi.diffuse.set(0.32, 0.38, 0.54);
    hemi.groundColor.set(0.05, 0.06, 0.08);
    hemi.specular.set(0.015, 0.02, 0.03);
    hemi.intensity = NIGHT_LOOK.skyIntensity * 0.24;
    const moon = new DirectionalLight("taxi_moonlight", new Vector3(-0.25, -0.45, -0.85), scene);
    moon.diffuse = Color3.FromHexString("#6C8BC4");
    moon.specular.set(0.05, 0.07, 0.11);
    moon.intensity = NIGHT_LOOK.moonIntensity * 0.16;
    this.flash = new DirectionalLight("taxi_storm_flash", new Vector3(0.4, -1, 0.5), scene);
    this.flash.diffuse.set(0.76, 0.84, 1);
    this.flash.intensity = 0;
    this.sky = new StormSky(scene);
    const roadReflection = new MirrorTexture("taxi_standing_water_reflection", 256, scene, false);
    roadReflection.mirrorPlane = new Plane(0, 1, 0, 0.058 - TAXI_GROUND_DROP);
    roadReflection.refreshRate = 3;
    roadReflection.level = 0.38;
    roadReflection.blurKernel = 8;
    roadReflection.renderParticles = false;
    // At night the ruts' water shows the storm sky and the dark line of the crowns
    // against it, not the trunks: the far cards stand in for the forest, at a fraction
    // of its cost (the full roadside here doubled the frame every third frame).
    roadReflection.renderList = [
      ...forest.filter((m) => m.name.startsWith("taxi_far_forest")),
      this.sky.dome,
    ];
    // The flood over the paddies holds the storm sky, the palms and the houses; the
    // lightning turns whole fields white.
    const paddyReflection = new MirrorTexture("taxi_paddy_flood_reflection", 256, scene, false);
    paddyReflection.mirrorPlane = new Plane(0, 1, 0, -TAXI_PADDY_WATER);
    paddyReflection.refreshRate = 4;
    paddyReflection.level = 0.75;
    paddyReflection.blurKernel = 12;
    paddyReflection.renderParticles = false;
    paddyReflection.renderList = [
      ...forest.filter(
        (m) =>
          !/M_taxi_paddy_water|M_taxi_rice|M_taxi_dike_earth|M_forest_grass/.test(
            m.material?.name ?? "",
          ) && m.getBoundingInfo().boundingBox.minimumWorld.z < TAXI_FOREST_START + 30,
      ),
      this.sky.dome,
    ];
    const size = 128,
      normals = new Uint8Array(size * size * 4);
    for (let y = 0; y < size; y++)
      for (let x = 0; x < size; x++) {
        const a = ((x * 4 + y * 3) / size) * Math.PI * 2,
          b = ((-x * 5 + y * 7) / size) * Math.PI * 2,
          nx = -(Math.cos(a) * 4 - Math.cos(b) * 2.5) * 0.035,
          ny = -(Math.cos(a) * 3 + Math.cos(b) * 3.5) * 0.035,
          length = Math.hypot(nx, ny, 1),
          i = (y * size + x) * 4;
        normals.set(
          [
            127.5 + (nx / length) * 127.5,
            127.5 + (ny / length) * 127.5,
            127.5 + 127.5 / length,
            255,
          ],
          i,
        );
      }
    this.waterRipples = RawTexture.CreateRGBATexture(normals, size, size, scene, true, false);
    this.waterRipples.name = "taxi_shallow_water_ripples";
    this.waterRipples.level = 0.2;
    for (const mesh of landscape)
      if (mesh.material instanceof PBRMaterial && mesh.material.name === "M_puddle") {
        mesh.material.reflectionTexture = roadReflection;
        mesh.material.bumpTexture = this.waterRipples;
        mesh.material.albedoColor.set(0.055, 0.075, 0.085);
        // Still water: a tight glint of the lamps, not a white sheet.
        mesh.material.roughness = 0.06;
        mesh.material.specularIntensity = 0.45;
      } else if (
        mesh.material instanceof PBRMaterial &&
        mesh.material.name === "M_taxi_paddy_water"
      ) {
        mesh.material.reflectionTexture = paddyReflection;
        mesh.material.bumpTexture = this.waterRipples;
        mesh.material.albedoColor.set(0.03, 0.04, 0.045);
        mesh.material.roughness = 0.1;
      }
    // The sugar palms' scanned trunks are grey-black, not the Mexican palm's silver; their
    // leaves are cut out, never blended, so they sort against the rain.
    for (const material of materials)
      if (material instanceof PBRMaterial && /^Wash_|^Wahs_/.test(material.name)) {
        if (/trunk|fur|cut_stalk|crownshaft/.test(material.name))
          material.albedoColor.scaleInPlace(0.42);
        if (material.transparencyMode === PBRMaterial.PBRMATERIAL_ALPHABLEND)
          material.transparencyMode = PBRMaterial.PBRMATERIAL_ALPHATEST;
      }
    // One guttering candle stub left burning at the Neak Ta's shrine where the trees begin.
    const shrine = scene.getMeshByName("taxi_road_roadside_neakta_shrine");
    if (shrine) {
      shrine.computeWorldMatrix(true);
      const at = shrine.getBoundingInfo().boundingBox;
      const candle = new PointLight(
        "taxi_shrine_candle",
        new Vector3(at.centerWorld.x - 0.25, at.minimumWorld.y + 0.55, at.centerWorld.z - 0.2),
        scene,
      );
      candle.parent = route;
      candle.diffuse.set(1, 0.6, 0.28);
      candle.range = 4.5;
      candle.includedOnlyMeshes = within(forest, candle.position, candle.range);
      candle.intensity = 1.6;
      this.shrineCandle = candle;
    }
    // The oil lamp behind the stilt house's shutters, glowing softly out across the flooded paddies.
    const lampAt = scene.getTransformNodeByName("taxi_road_anchor_house_lamp");
    if (lampAt) {
      lampAt.computeWorldMatrix(true);
      const lamp = new PointLight(
        "taxi_house_oil_lamp",
        lampAt.getAbsolutePosition().clone(),
        scene,
      );
      lamp.parent = route;
      lamp.diffuse.set(1, 0.62, 0.3);
      lamp.specular.set(0.3, 0.2, 0.1);
      lamp.range = 11;
      lamp.intensity = 6;
      lamp.includedOnlyMeshes = within(forest, lamp.position, lamp.range);
      this.houseLamp = lamp;
    }
    // Warm flickering practical bulbs under the roadside wooden shops and Khmer 90s poster boards.
    for (const node of scene.transformNodes) {
      const shopMatch = /^taxi_road_anchor_(shop|poster)_lamp_(\d+)$/.exec(node.name);
      if (!shopMatch) continue;
      const isShop = shopMatch[1] === "shop";
      const idx = Number(shopMatch[2]);
      node.computeWorldMatrix(true);
      const pos = node.getAbsolutePosition().clone();
      const lamp = new PointLight(`taxi_${shopMatch[1]}_lamp_${idx}`, pos, scene);
      lamp.parent = route;
      lamp.diffuse.set(1, isShop ? 0.68 : 0.75, isShop ? 0.3 : 0.4);
      lamp.specular.set(0.35, 0.24, 0.12);
      lamp.range = isShop ? 11.5 : 8;
      const base = isShop ? 18 : 11;
      lamp.intensity = base;
      lamp.includedOnlyMeshes = within(forest, pos, lamp.range);
      lamp.setEnabled(false);
      this.roadsideLamps.push({
        light: lamp,
        base,
        z: pos.z,
        phase: idx * 2.17 + (isShop ? 0.5 : 3.9),
        isShop,
      });
    }
    // The bonnet's old lacquer under running rain: a hard wet clear coat, beaded and moving.
    for (const lacquer of scene.materials.filter((m) => m.name.startsWith("M_taxi_body_lacquer"))) {
      if (!(lacquer instanceof PBRMaterial)) continue;
      lacquer.clearCoat.isEnabled = true;
      lacquer.clearCoat.intensity = 1;
      lacquer.clearCoat.roughness = 0.06;
      const beads = this.waterRipples.clone();
      beads.uScale = beads.vScale = 7;
      beads.level = 0.5;
      lacquer.clearCoat.bumpTexture = beads;
      this.bonnetBeads = beads;
    }
    this.eyeHeight = anchorAt(scene, "sora_eye", new Vector3(0.27, 1.065, -0.06)).y;
    const wiperPivots = ["l", "r"].map((side) =>
      anchorAt(scene, `wiper_${side}`, new Vector3(side === "l" ? -0.23 : 0.23, 1.112, 0.455)).add(
        new Vector3(0, 0.032, 0),
      ),
    );
    this.glass = new TaxiRain(scene, {
      min: anchorAt(scene, "windscreen_min", new Vector3(-0.485, 0.875, 0.49)),
      max: anchorAt(scene, "windscreen_max", new Vector3(0.485, 1.115, 0.45)),
      wipers: wiperPivots,
      blade: 0.242,
    });
    const sideGlass = scene.materials.find((m) => m.name === "M_taxi_window_glass");
    if (sideGlass instanceof PBRMaterial) {
      sideGlass.albedoTexture = this.glass.sideTexture;
      sideGlass.emissiveTexture = this.glass.sideTexture;
      sideGlass.useAlphaFromAlbedoTexture = true;
      sideGlass.alpha = 0.65;
      sideGlass.emissiveColor.set(0.13, 0.17, 0.21);
    }

    // Warm practicals inside the dark cabin: cluster & valve radio glow, soft headlamp road bounce
    // across the wheel and driver, plus a warm amber sweep whenever the cab passes a roadside shop.
    const cabinSolid = cabinMeshes.filter((m) => m.material?.name !== "M_taxi_window_glass");
    const cluster = anchorAt(scene, "dials", new Vector3(0, 0.72, 0.508));
    const dash = new PointLight(
      "taxi_dashboard_glow",
      cluster.add(new Vector3(0.06, -0.01, -0.13)),
      scene,
    );
    dash.diffuse.set(0.95, 0.68, 0.32);
    dash.specular.set(0.06, 0.04, 0.02);
    dash.intensity = 0.16;
    dash.range = 1.15;
    dash.includedOnlyMeshes = cabinSolid;
    this.dash = dash;

    // Warm 1933 Art Deco ceiling dome lamp illuminating the tufted rear cabin, luggage & lotus tray
    // (sputters and dies together with the headlamps whenever a ghost closes in!).
    const domeLight = new PointLight("taxi_cabin_dome_light", new Vector3(0, 1.12, -0.54), scene);
    domeLight.diffuse.set(1, 0.78, 0.44);
    domeLight.specular.set(0.05, 0.04, 0.02);
    domeLight.intensity = 0.3;
    domeLight.range = 2.65;
    domeLight.includedOnlyMeshes = cabinSolid;
    this.domeLight = domeLight;

    // Soft natural interior bounce over Sora's cream blouse, hands on her thighs, satchel & shoes.
    const soraFill = new PointLight("taxi_sora_lap_fill", new Vector3(0.24, 0.94, 0.24), scene);
    soraFill.diffuse.set(0.95, 0.8, 0.56);
    soraFill.specular.set(0.03, 0.02, 0.015);
    soraFill.intensity = 0.14;
    soraFill.range = 1.4;
    soraFill.includedOnlyMeshes = cabinSolid;
    this.soraFill = soraFill;

    // Subtle shielded warm tungsten under-dash courtesy lamp sculpting the gearshift, ratchet
    // handbrake, pedals, firewall fusebox, brass sill plates, wet floor mats, and Sora's satchel.
    const footwellLight = new PointLight(
      "taxi_underdash_footwell_glow",
      new Vector3(0.01, 0.51, 0.48),
      scene,
    );
    footwellLight.diffuse.set(1, 0.72, 0.38);
    footwellLight.specular.set(0.14, 0.1, 0.05);
    footwellLight.intensity = 0.24;
    footwellLight.range = 1.45;
    footwellLight.includedOnlyMeshes = cabinSolid;
    this.footwellLight = footwellLight;

    const domeMat = scene.getMaterialByName("M_cab_dome_glass");
    if (domeMat instanceof PBRMaterial) this.domeGlassMat = domeMat;
    const footBulbMat = scene.getMaterialByName("M_cab_footwell_bulb");
    if (footBulbMat instanceof PBRMaterial) this.footwellBulbMat = footBulbMat;

    const roadBounce = new PointLight(
      "taxi_headlamp_cabin_bounce",
      new Vector3(0, 1.04, 0.86),
      scene,
    );
    roadBounce.diffuse.set(0.84, 0.72, 0.48);
    roadBounce.specular.set(0.06, 0.05, 0.03);
    roadBounce.intensity = 0.16;
    roadBounce.range = 2.4;
    roadBounce.includedOnlyMeshes = cabinSolid;
    this.roadBounce = roadBounce;

    const cabinShopSweep = new PointLight(
      "taxi_cabin_shop_sweep",
      new Vector3(-0.9, 1.05, 0.4),
      scene,
    );
    cabinShopSweep.diffuse.set(1, 0.68, 0.28);
    cabinShopSweep.specular.set(0.14, 0.1, 0.05);
    cabinShopSweep.intensity = 0;
    cabinShopSweep.range = 2.6;
    cabinShopSweep.includedOnlyMeshes = cabinSolid;
    this.cabinShopSweep = cabinShopSweep;

    const radioMat = scene.getMaterialByName("M_cab_radio_dial");
    if (radioMat instanceof PBRMaterial) this.radioDialMat = radioMat;

    for (const side of ["l", "r"]) {
      const x = side === "l" ? -0.6 : 0.6;
      const headlamp = new SpotLight(
        `taxi_headlight_${side}`,
        // In the Rosalie's own lamp bowls, either side of the radiator shell.
        anchorAt(scene, `headlamp_${side}`, new Vector3(x * 0.72, 0.485, 1.74)),
        new Vector3(x < 0 ? -0.075 : 0.075, -0.085, 1).normalize(),
        1.06,
        1.85,
        scene,
      );
      headlamp.diffuse.set(1, 0.82, 0.5);
      headlamp.specular.set(0.55, 0.45, 0.28);
      headlamp.intensity = x < 0 ? 1750 : 2400;
      headlamp.range = 48;
      headlamp.renderPriority = 8;
      headlamp.excludedMeshes = [...cabinMeshes, this.glass.glass];
      this.headlamps.push({ light: headlamp, power: headlamp.intensity });
      if (x < 0) {
        const shadow = new ShadowGenerator(game.preset.name === "low" ? 512 : 1024, headlamp);
        shadow.usePercentageCloserFiltering = true;
        shadow.bias = 0.001;
        shadow.normalBias = 0.025;
        // Only what stands in the beam casts: the stretch of road the lamps reach,
        // chosen again as the car moves on (see update).
        this.shadowCasters = landscape.filter(
          (mesh) => (mesh.metadata as { batchGroup?: string } | null)?.batchGroup !== "distant",
        );
        this.headlampShadow = shadow;
      }
    }
    const metal =
      scene.materials.find((m) => m.name === "M_cab_aged_chrome") ??
      scene.materials.find((m) => m.name === "M_taxi_aged_nickel") ??
      new PBRMaterial("taxi_wiper_nickel", scene);
    const rubber = scene.materials.find((m) => m.name === "M_taxi_rubber") ?? metal;
    // Authentic 1933 Citroën Rosalie header-mounted vacuum wipers: slender stamped-nickel
    // spring arm bolted into the top windscreen frame, hinged saddle bridge with claws, and
    // a razor-thin black rubber squeegee blade pressed flush against the exterior glass.
    for (const [i, at] of wiperPivots.entries()) {
      const pivot = new TransformNode(`taxi_wiper_pivot_${i}`, scene);
      pivot.position.set(at.x, at.y, at.z + 0.014);
      pivot.rotation.x = -0.166;
      const part = (mesh: Mesh, mat: typeof metal) => {
        mesh.parent = pivot;
        mesh.material = mat;
        mesh.isPickable = false;
      };
      // Chrome pivot cap & spring-tension hinge mounted cleanly on the header shaft
      const cap = CreateCylinder(
        `taxi_wiper_pivot_cap_${i}`,
        { diameter: 0.014, height: 0.011, tessellation: 14 },
        scene,
      );
      cap.rotation.x = Math.PI / 2;
      cap.position.set(0, 0, 0.002);
      part(cap, metal);

      const collar = CreateBox(
        `taxi_wiper_collar_${i}`,
        { width: 0.0075, height: 0.026, depth: 0.0055 },
        scene,
      );
      collar.position.set(0, -0.014, 0.006);
      part(collar, metal);

      // Slender flat stamped-nickel spring arm (not a bulky rod)
      const arm = CreateBox(
        `taxi_wiper_sprung_arm_${i}`,
        { width: 0.0036, height: 0.146, depth: 0.0022 },
        scene,
      );
      arm.position.set(0, -0.088, 0.0085);
      part(arm, metal);

      // Centre hinged saddle clip connecting arm to wiper blade spine
      const saddle = CreateBox(
        `taxi_wiper_saddle_${i}`,
        { width: 0.0062, height: 0.016, depth: 0.0055 },
        scene,
      );
      saddle.position.set(0, -0.156, 0.0065);
      part(saddle, metal);

      // Sleek tapered nickel spine + upper/lower claw clips gripping the rubber blade
      const spine = CreateBox(
        `taxi_wiper_spine_${i}`,
        { width: 0.0028, height: 0.172, depth: 0.0032 },
        scene,
      );
      spine.position.set(0, -0.156, 0.0055);
      part(spine, metal);

      for (const cy of [-0.086, -0.226]) {
        const claw = CreateBox(
          `taxi_wiper_claw_${i}_${cy}`,
          { width: 0.0046, height: 0.007, depth: 0.0048 },
          scene,
        );
        claw.position.set(0, cy, 0.0042);
        part(claw, metal);
      }

      // Razor-thin black rubber squeegee blade pressed cleanly against the wet glass
      const blade = CreateBox(
        `taxi_wiper_rubber_blade_${i}`,
        { width: 0.0017, height: 0.184, depth: 0.0048 },
        scene,
      );
      blade.position.set(0, -0.156, 0.0026);
      part(blade, rubber);
      this.wipers.push(pivot);
    }
    this.dialTexture = new DynamicTexture(
      "taxi_analogue_gauges",
      { width: 1024, height: 256 },
      scene,
      false,
    );
    this.dialTexture.hasAlpha = true;
    const dials = new StandardMaterial("taxi_instrument_glass_and_print", scene);
    dials.diffuseTexture = this.dialTexture;
    dials.emissiveTexture = this.dialTexture;
    dials.useAlphaFromDiffuseTexture = true;
    dials.emissiveColor.set(0.45, 0.36, 0.2);
    dials.disableLighting = true;
    dials.specularColor = Color3.Black();
    this.dials = dials;
    // Recessed cleanly inside the 5 3D chrome gauge bezels in front of taxi_dash_cluster_plate.
    const instruments = CreatePlane("taxi_instrument_face", { width: 0.33, height: 0.082 }, scene);
    instruments.position.set(cluster.x, cluster.y, cluster.z - 0.0135);
    instruments.material = dials;
    instruments.isPickable = false;
    this.paintDials(6.8);
    // The rear-view mirror, as the driver set it: angled cleanly down the centreline of the
    // back seat so Sora sees the rear glass—and the ghost looming face-on right behind her.
    const glassAt = anchorAt(scene, "mirror", new Vector3(0, 1.102, 0.398));
    const mirrorEye = new FreeCamera(
      "taxi_rear_view_eye",
      glassAt.add(new Vector3(0, 0, -0.02)),
      scene,
    );
    mirrorEye.setTarget(new Vector3(0.08, 0.96, -1.15));
    // Vertical field: frames the back seat and fills the mirror when she lunges between the front seats.
    mirrorEye.fov = 0.34;
    mirrorEye.minZ = 0.05;
    mirrorEye.maxZ = 8;
    // Only the RTT renders through it; it must not take part in input or the main view.
    mirrorEye.inputs.clear();
    mirrorEye.layerMask = 0x0fffffff | MIRROR_ONLY;
    this.mirror = new RenderTargetTexture("taxi_rear_view", { width: 512, height: 212 }, scene);
    this.mirror.activeCamera = mirrorEye;
    // Through the rear and side glass: the night fog behind the car.
    this.mirror.clearColor = new Color4(...MIRROR_FOG, 1);
    // A plain colour pass: the SSAO pre-pass belongs to the player's camera only.
    this.mirror.noPrePassRenderer = true;
    scene.customRenderTargets.push(this.mirror);
    // A touch brighter than the cabin seen directly: eyes adjust to the small bright glass.
    this.mirror.level = 2.0;
    this.mirror.refreshRate = 3;
    this.mirror.renderParticles = false;
    this.mirror.renderList = cabinMeshes.filter((m) => !/mirror|taxi_charm/.test(m.name));
    // The same shape as the glass (its projection follows the target's size), mirrored left to right.
    this.mirror.uScale = -1;
    this.mirror.uOffset = 1;
    this.mirror.vScale = -1;
    this.mirror.vOffset = 1;
    // Unlit: the glass shows the back seat as the camera there sees it, and the
    // player's camera grades it with the rest of the night.
    const mirrorMaterial = new StandardMaterial("taxi_mirror_silver", scene);
    // (Unlit, a standard material shows emissive × its diffuse texture.)
    mirrorMaterial.diffuseTexture = this.mirror;
    mirrorMaterial.emissiveColor.set(0.96, 0.98, 0.97);
    mirrorMaterial.specularColor = Color3.Black();
    mirrorMaterial.disableLighting = true;
    // The authored glass is wound away from the cabin; show it from Sora's side.
    mirrorMaterial.backFaceCulling = false;
    const face = cabinMeshes.find((m) => m.name.includes("taxi_mirror_surface"));
    if (face) face.material = mirrorMaterial;
    this.rain = new TaxiWeather(scene, game.preset.name === "low");
    // The Preay (build-preay.py), as she is: her white dress is what the lamps find.
    this.spirit = new MocapFigure(spiritAsset, "taxi_preay");
    this.spirit.root.parent = route;
    this.spiritFill = new PointLight("taxi_spirit_flash_fill", new Vector3(0.5, 1.05, 0.2), scene);
    this.spiritFill.diffuse.set(0.76, 0.82, 0.98);
    this.spiritFill.specular.set(0.02, 0.02, 0.03);
    this.spiritFill.range = 3.2;
    this.spiritFill.intensity = 0;
    this.spiritFill.includedOnlyMeshes = this.spirit.meshes.filter((m) => m.getTotalVertices() > 0);
    // Shown once, behind the black of the opening, so its shaders are compiled before it is needed.
    this.spirit.pose("stand", 0);
    this.spirit.root.position.set(0, -50, 0);
    this.rider = new MocapFigure(spiritAsset, "taxi_mirror_rider");
    this.rider.setEnabled(false);
    for (const lamp of this.headlamps) lamp.light.excludedMeshes.push(...this.rider.meshes);
    this.mirror.renderList.push(...this.rider.meshes);
    // Three dedicated low-specular horror lights sculpting her pale gaunt face & white dress
    // while keeping her long wet black hair deeply jet-black (never grey/silver glare!).
    for (const [name, at, colour, range] of [
      ["taxi_mirror_rider_face", new Vector3(0.06, 1.02, 0.05), new Color3(0.84, 0.9, 1), 2.6],
      ["taxi_mirror_rider_rim", new Vector3(0.65, 1.08, -0.78), new Color3(0.58, 0.7, 0.95), 2.6],
      ["taxi_mirror_rider_dash", new Vector3(0.04, 0.72, 0.28), new Color3(0.95, 0.66, 0.34), 2.4],
    ] as const) {
      const light = new PointLight(name, at, scene);
      light.diffuse = colour;
      light.specular.set(0.02, 0.02, 0.03);
      light.range = range;
      light.intensity = 0;
      light.includedOnlyMeshes = this.rider.meshes;
      this.riderLights.push(light);
    }
    // Pale staring eyes catching the cold storm light inside the dark cabin.
    this.riderEyes = new StandardMaterial("M_taxi_mirror_rider_eyes", scene);
    this.riderEyes.disableLighting = true;
    this.riderEyes.diffuseColor.set(0, 0, 0);
    for (const mesh of this.rider.meshes) {
      if (/_eye_\d/.test(mesh.name)) mesh.material = this.riderEyes;
      mesh.layerMask = MIRROR_ONLY;
    }
    const soraGlass = cabinMeshes.find(
      (m): m is Mesh => m instanceof Mesh && m.name.startsWith("taxi_side_glass_sora"),
    );
    if (soraGlass) this.glassMarks = new TaxiGlassMarks(scene, soraGlass);
    this.mist = new TaxiMist(
      game,
      route,
      this.headlamps.map((h) => h.light),
    );
    ageTaxiCabin(scene);
    this.charm = scene.getTransformNodeByName("taxi_mirror_charm_pivot");
    if (this.charm) this.charm.rotationQuaternion ??= Quaternion.Identity();
    this.wheel = scene.getTransformNodeByName("taxi_steering_wheel_pivot");
    if (this.wheel) {
      this.wheel.rotationQuaternion ??= Quaternion.Identity();
      this.wheelBase = this.wheel.rotationQuaternion.clone();
    }
    // The driver's body as one piece, pivoting at his hips on the seat: the scanned body
    // gives the seat height (his own head is only head and neck).
    const anatomy =
      cabinMeshes.find((m) => m.name.includes("taxi_driver_body_scan")) ??
      cabinMeshes.find((m) => m.name.includes("taxi_driver_anatomy"));
    if (anatomy) {
      const box = anatomy.getBoundingInfo().boundingBox;
      const pivot = new TransformNode("taxi_driver_pivot", scene);
      pivot.position.set(box.centerWorld.x, box.minimumWorld.y + 0.42, box.centerWorld.z - 0.1);
      for (const mesh of cabinMeshes) if (/taxi_driver/.test(mesh.name)) mesh.setParent(pivot);
      this.driver = pivot;
      for (const mesh of cabinMeshes)
        if (/taxi_driver/.test(mesh.name) && mesh.morphTargetManager)
          for (let i = 0; i < mesh.morphTargetManager.numTargets; i++) {
            const target = mesh.morphTargetManager.getTarget(i);
            if (target.name === "blink") this.blinkTargets.push(target);
            else if (target.name in this.face) {
              const list = this.faceTargets.get(target.name as keyof DriverFace) ?? [];
              list.push(target);
              this.faceTargets.set(target.name as keyof DriverFace, list);
            }
          }
    }
    for (const material of scene.materials)
      if (material instanceof PBRMaterial) material.maxSimultaneousLights = 10;
    // Keep high simultaneous-light headroom and deeply matte hair/cloth shading on both ghost
    // figures AFTER the global cap so their face lights stay active and black hair stays pitch-black!
    for (const mesh of [...this.rider.meshes, ...this.spirit.meshes])
      if (mesh.material instanceof PBRMaterial) {
        mesh.material.maxSimultaneousLights = 16;
        mesh.material.roughness = 0.96;
        mesh.material.specularIntensity = 0.02;
        mesh.material.environmentIntensity = 0.18;
      }
    for (const mesh of cabinMeshes) {
      mesh.isPickable = false;
      mesh.receiveShadows = true;
    }
  }
  static async load(game: Game): Promise<TaxiVisuals> {
    registerBuiltInLoaders();
    const scene = game.scene,
      base = `${import.meta.env.BASE_URL}assets/ep1/`;
    const [cabin, roadside, spiritAsset] = await Promise.all([
      LoadAssetContainerAsync(`${base}ep1_taxi_cabin.glb`, scene),
      LoadAssetContainerAsync(`${base}ep1_taxi_roadside.glb`, scene),
      Preay.load(scene),
    ]);
    cabin.addAllToScene();
    for (const material of cabin.materials) {
      if (!(material instanceof PBRMaterial)) continue;
      if (material.name === "M_taxi_dashboard_walnut") {
        // Old varnished walnut: a dark grain under a clear lacquer that catches the lightning.
        material.albedoColor.scaleInPlace(1.6);
        material.clearCoat.isEnabled = true;
        material.clearCoat.intensity = 0.65;
        material.clearCoat.roughness = 0.18;
      }
      if (
        /^M_taxi_(driver_skin|driver_hands_scan|sora_skin_scan|driver_head_scan)$/.test(
          material.name,
        )
      ) {
        // Light through the ears and fingers; a soft sheen of sweat rather than plastic.
        material.subSurface.isTranslucencyEnabled = true;
        material.subSurface.translucencyIntensity = 0.35;
        material.subSurface.tintColor = new Color3(0.95, 0.45, 0.32);
        // The scanned face carries its own roughness map (wet eyes, lips, oily nose, cotton cap).
        if (material.name !== "M_taxi_driver_head_scan") {
          material.roughness = 0.62;
          material.specularIntensity = 0.22;
        }

        material.metallic = 0;
      }
      if (
        /^M_taxi_(driver_clothes_scan|driver_shirt_scan|sora_trousers_scan|sora_blouse_scan)$/.test(
          material.name,
        ) ||
        material.name === "M_cab_driver_krama"
      ) {
        // Woven cotton and wool: deeply matte so close cabin practicals never specular-blowout cloth.
        material.metallic = 0;
        material.roughness = 0.94;
        material.specularIntensity = 0.04;
      }
      if (material.name === "M_cab_walnut_polished") {
        material.clearCoat.isEnabled = true;
        material.clearCoat.intensity = 0.72;
        material.clearCoat.roughness = 0.14;
      }
      if (material.name === "M_cab_prayer_bead") {
        material.clearCoat.isEnabled = true;
        material.clearCoat.intensity = 0.65;
        material.clearCoat.roughness = 0.2;
      }
      if (material.name === "M_cab_takrut_bronze") {
        material.metallic = 0.88;
        material.roughness = 0.34;
      }
      if (material.name === "M_cab_leather_black" || material.name === "M_cab_leather_satchel") {
        material.metallic = 0;
        material.roughness = 0.56;
      }
      if (material.name === "M_cab_pillar_leatherette") {
        material.metallic = 0;
        material.roughness = 0.88;
        material.specularIntensity = 0.05;
      }
      if (material.name === "M_taxi_driver_eye") {
        material.clearCoat.isEnabled = true;
        material.clearCoat.intensity = 1;
        material.clearCoat.roughness = 0.04;
      }
    }
    for (const material of cabin.materials)
      if (material instanceof PBRMaterial && material.name === "M_taxi_window_glass")
        material.specularIntensity = 0.03;
    realiseInstances(cabin);
    // Six hundred small authored parts would each be drawn twice (scene and mirror):
    // batch the static trim by material, keeping apart what moves or is re-textured.
    const apart =
      /taxi_driver|taxi_charm|taxi_mirror_surface|taxi_instrument_face|taxi_side_glass_sora|taxi_steering_wheel|taxi_dash_radio_dial|taxi_cabin_dome_glass/;
    const trim = cabin.meshes.filter(
      (m): m is Mesh =>
        m instanceof Mesh &&
        m.getTotalVertices() > 0 &&
        !apart.test(m.name) &&
        !m.morphTargetManager,
    );
    const batched = mergeStaticMeshes(trim, {
      cellSize: 100,
      group: (mesh) => mesh.getVerticesDataKinds().sort().join(","),
    });
    const cabinMeshes = [
      ...batched,
      ...cabin.meshes.filter(
        (m) => m.getTotalVertices() > 0 && !m.isDisposed() && !trim.includes(m as Mesh),
      ),
    ];
    for (const material of roadside.materials)
      if (material instanceof PBRMaterial) {
        material.maxSimultaneousLights = 8;
        if (material.name === "M_taxi_khmer_posters") {
          // Real hand-painted Khmer 90s shop signs & posters: damp rain satin sheen, crisp colour.
          material.metallic = 0;
          material.roughness = 0.48;
          material.clearCoat.isEnabled = true;
          material.clearCoat.intensity = 0.35;
          material.clearCoat.roughness = 0.22;
        } else {
          applyRainWetness(material);
        }
      }
    const { root: route, landscape } = buildTaxiRoadside(roadside, scene);
    const floor = CreateBox("taxi_seated_floor", { width: 1.7, height: 0.1, depth: 2.7 }, scene);
    floor.position.y = -0.05;
    floor.isVisible = false;
    floor.isPickable = false;
    addStaticBox(floor, "teak");
    const eye = anchorAt(scene, "sora_eye", new Vector3(0.27, 1.065, -0.06));
    game.spawnPlayer(new Vector3(eye.x, 0, eye.z));
    game.player.config.standEyeHeight = eye.y;
    game.player.config.crouchEyeHeight = eye.y;
    game.player.headBobEnabled = false;
    game.player.pitch = 0.025;
    game.player.yaw = -0.12;
    scene.clearColor = new Color4(0.0022, 0.0032, 0.0052, 1);
    return new TaxiVisuals(game, cabinMeshes, route, landscape, spiritAsset);
  }
  configure(): void {
    const g = this.game;
    g.atmosphere.baseExposure = NIGHT_LOOK.baseExposure;
    g.atmosphere.maxExposure = NIGHT_LOOK.maxExposure;
    // Keep the cabin realistically dark and moody: instruments, road bounce & passing shop bulbs
    // sculpt the driver and interior rather than a flat headlight-like camera wash.
    g.atmosphere.nightSightIntensity = 0.08;
    g.atmosphere.nightSight.range = 2.6;
    g.atmosphere.nightSight.excludedMeshes.push(this.glass.glass);
    // Sora's eyes adjust to the cabin; outside is lit only by the lamps and the sky, so the
    // ferns at her window stay dark until the headlamps or the lightning find them.
    g.atmosphere.nightSight.includedOnlyMeshes = this.cabinMeshes.filter(
      (m) => m !== this.glass.glass && m.material?.name !== "M_taxi_window_glass",
    );
    // Far enough for the far tree cards on both sides; the haze closes beyond.
    g.camera.maxZ = 140;
    if (g.pipeline.fog) {
      g.pipeline.fog.density = NIGHT_LOOK.fogDensity;
      g.pipeline.fog.heightFalloff = 0.25;
      g.pipeline.fog.ambient.set(...NIGHT_LOOK.fogAmbient);
    } else {
      g.scene.fogDensity = NIGHT_LOOK.fogDensity;
      g.scene.fogColor.set(...NIGHT_LOOK.fogAmbient);
    }
    this.mist.configure();
  }
  update(dt: number, t: number, flash: number): void {
    const g = this.game,
      angle = taxiWiperAngle(t),
      distance = taxiDistance(t),
      speed = taxiSpeed(t);
    for (const chunk of this.routeChunks) {
      const active = taxiRouteChunkVisible(chunk.minZ, chunk.maxZ, distance, chunk.ahead);
      if (active !== chunk.active) {
        chunk.mesh.setEnabled(active);
        chunk.active = active;
      }
    }
    // The lamps' shadows come from the 40 m of roadside in front of the car.
    const stretch = Math.floor(distance / 6);
    if (this.headlampShadow && stretch !== this.shadowStretch) {
      this.shadowStretch = stretch;
      const list = this.headlampShadow.getShadowMap()!.renderList!;
      list.length = 0;
      for (const chunk of this.routeChunks)
        if (
          chunk.maxZ > distance - 2 &&
          chunk.minZ < distance + 40 &&
          this.shadowCasters.includes(chunk.mesh)
        )
          list.push(chunk.mesh);
    }
    // A swerve turns the car, so the world turns about the passenger instead of the route origin.
    const pose = taxiRoadPose(distance),
      swerve = taxiSwerve(t),
      c = Math.cos(swerve),
      s = Math.sin(swerve);
    this.route.rotation.y = pose.yaw + swerve;
    this.route.position.set(pose.x * c + pose.z * s, 0, -pose.x * s + pose.z * c);
    this.flash.intensity = flash * 3.8;
    if (this.shrineCandle)
      this.shrineCandle.intensity =
        1.6 * (0.7 + 0.18 * Math.sin(t * 13.3) + 0.12 * Math.sin(t * 31.1 + 2)) * (1 - flash * 0.5);
    if (this.houseLamp)
      this.houseLamp.intensity =
        6 * (0.82 + 0.1 * Math.sin(t * 9.1) + 0.08 * Math.sin(t * 23.7 + 1.3));
    // Animate warm shop & Khmer poster practicals only near the car, and sweep warm light across
    // the dark cabin as the taxi rolls past each roadside stall!
    let bestSweep = 0;
    let sweepZ = 0;
    let sweepSide = -1;
    for (const lamp of this.roadsideLamps) {
      const dz = lamp.z - distance;
      const near = Math.abs(dz) < 55;
      if (lamp.light.isEnabled() !== near) lamp.light.setEnabled(near);
      if (!near) continue;
      const flutter =
        0.86 +
        0.08 * Math.sin(t * 11.3 + lamp.phase) +
        0.06 * Math.sin(t * 27.1 + lamp.phase * 1.7);
      lamp.light.intensity = lamp.base * flutter;
      const closeness = Math.exp(-((dz / 6.5) ** 2)) * (lamp.isShop ? 1 : 0.45);
      if (closeness > bestSweep) {
        bestSweep = closeness;
        sweepZ = dz * 0.14;
        sweepSide = lamp.light.position.x < taxiRoadX(lamp.z) ? -1 : 1;
      }
    }
    this.cabinShopSweep.intensity = bestSweep * 0.58;
    this.cabinShopSweep.position.set(sweepSide * 1.05, 1.05, Math.max(-0.8, Math.min(1.1, sweepZ)));
    this.sky.update(flash, g.pipeline.main.imageProcessing.exposure, dt);
    for (const wiper of this.wipers) wiper.rotation.z = angle;
    this.glass.update(dt, angle, flash);
    this.waterRipples.uOffset = t * 0.009;
    this.waterRipples.vOffset = t * 0.006;
    // Rain running back along the bonnet in the wind of the car's speed.
    if (this.bonnetBeads) this.bonnetBeads.vOffset = -t * 0.05 * (speed / 6.8);
    this.rain.update(t, speed, flash);
    this.updateSpirit(t, flash);
    this.updateMirrorRider(t, flash);
    this.glassMarks?.update(t, flash);
    // The car's electrics fail when something is close: lamps, dome lamp, dash, radio and bounce together.
    const power = taxiElectrics(t);
    for (const lamp of this.headlamps) lamp.light.intensity = lamp.power * power;
    this.dash.intensity = 0.18 * (0.12 + 0.88 * power);
    this.domeLight.intensity = 0.3 * (0.06 + 0.94 * power);
    this.soraFill.intensity = 0.14 * (0.14 + 0.86 * power) + flash * 0.16;
    this.footwellLight.intensity = 0.24 * (0.08 + 0.92 * power) + flash * 0.12;
    this.roadBounce.intensity = 0.16 * power + flash * 0.42;
    this.roadBounce.diffuse.set(
      0.84 * (1 - flash * 0.3) + 0.65 * flash * 0.3,
      0.72 * (1 - flash * 0.3) + 0.78 * flash * 0.3,
      0.48 * (1 - flash * 0.5) + 1.0 * flash * 0.5,
    );
    this.dials.emissiveColor.set(0.58, 0.46, 0.25).scaleInPlace(0.12 + 0.88 * power);
    if (this.radioDialMat) this.radioDialMat.emissiveIntensity = 0.15 + 1.55 * power;
    if (this.domeGlassMat) this.domeGlassMat.emissiveIntensity = 0.08 + 2.2 * power;
    if (this.footwellBulbMat) this.footwellBulbMat.emissiveIntensity = 0.1 + 2.4 * power;
    this.mist.update(dt, t, distance, power, flash);
    this.updateCabinLife(dt, t, speed, flash);
    // Small suspension movement + visceral shock micro-jolt on haunt impacts.
    const bump = (Math.sin(t * 5.6) * 0.0028 + Math.sin(t * 9.9 + 0.7) * 0.0012) * (speed / 6.8);
    const flinch = taxiFlinch(t);
    const tremor = flinch * Math.sin(t * 48) * 0.0055;
    g.camera.position.y = g.player.feet.y + this.eyeHeight + bump - flinch * 0.018 + tremor;
    g.camera.rotation.z =
      (Math.sin(t * 1.15) * 0.003 + Math.sin(t * 3.1) * 0.001) * (speed / 6.8) +
      swerve * 0.3 +
      flinch * Math.sin(t * 34) * 0.012;
    this.dialIn -= dt;
    if (this.dialIn <= 0) {
      this.dialIn = 0.1;
      this.paintDials(speed);
    }
    g.atmosphere.update(dt, 0.22 + flash * 0.3);
  }
  /** Where the clockwork meter sits on the dash, for its ticking. */
  meterPosition(): Vector3 {
    const meter = this.game.scene.meshes.find((m) => m.name.startsWith("taxi_meter_case"));
    meter?.computeWorldMatrix(true);
    return meter
      ? meter.getBoundingInfo().boundingBox.centerWorld.clone()
      : new Vector3(0.27, 1.17, 1.13);
  }

  /**
   * The Neak Ta where the ride clock puts it, on the frame of its motion capture the clock
   * gives, its head turning to keep Sora in view. Between the flickers that show it, it is
   * switched off: it is somewhere in the dark, and only the sound says where.
   */
  private updateSpirit(t: number, flash: number): void {
    const pose = taxiSpiritAt(t),
      form = this.spirit;
    const atTheGlass =
      pose?.kind === "window" || (pose?.kind === "overtake" && pose.clip === "reach");
    if (pose?.kind === "bonnet") {
      this.spiritFill.position.set(0.18, 0.96, 2.25);
      this.spiritFill.range = 4.6;
      this.spiritFill.intensity = 0.35 + flash * 1.15;
    } else if (pose?.kind === "window") {
      // Positioned cleanly between Sora's passenger glass and the ghost's face outside so her
      // gaunt features & white dress read vividly while her black hair stays pitch-black!
      this.spiritFill.position.set(0.68, 1.06, -0.04);
      this.spiritFill.range = 2.6;
      this.spiritFill.intensity = 0.55 + flash * 1.65;
    } else if (atTheGlass) {
      this.spiritFill.position.set(0.58, 1.05, 0.12);
      this.spiritFill.range = 3.2;
      this.spiritFill.intensity = flash * 3.4;
    } else if (pose?.kind === "crossing") {
      this.spiritFill.position.set(0, 1.15, 4.8);
      this.spiritFill.range = 9.5;
      this.spiritFill.intensity = flash * 3.6;
    } else {
      this.spiritFill.intensity = 0;
    }
    if (this.spiritWarm > 0 && !pose) {
      this.spiritWarm--;
      form.setEnabled(true);
      return;
    }
    form.setEnabled(pose !== null && pose.visible);
    if (!pose || !pose.visible) return;
    form.root.position.set(pose.x, pose.y, pose.z);
    form.root.rotation.set(0, pose.heading, 0);
    form.pose(pose.clip, pose.clipTime, pose.clip !== "reach");
    form.root.computeWorldMatrix(true);
    form.lookAt(this.game.camera.globalPosition, pose.look);
  }

  /**
   * The in-car back-seat haunt: first appears silently behind Sora in the rear-view mirror while
   * the driver warns her, then lunges forward between the front seats—filling the entire mirror
   * frame AND manifesting physically inside the cabin if Sora turns her head!
   */
  private updateMirrorRider(t: number, flash: number): void {
    const pose = taxiMirrorRiderAt(t),
      form = this.rider;
    form.setEnabled(pose !== null);
    this.mirror.refreshRate = pose ? 1 : 3;
    // The fog behind the car; the lightning turns it cold silver-white.
    const [fr, fg, fb] = MIRROR_FOG;
    this.mirror.clearColor.set(fr + flash * 0.45, fg + flash * 0.52, fb + flash * 0.6, 1);
    const [faceKey, rim, dash] = this.riderLights;
    if (pose) {
      const p = pose.presence;
      const lungeBoost = pose.kind === "lean" ? 1.25 : 0.72;
      faceKey.intensity = p * (0.75 * lungeBoost + flash * 1.45);
      rim.intensity = p * (0.55 * lungeBoost + flash * 1.25);
      dash.intensity = p * (0.55 * taxiElectrics(t) + 0.16);
    } else {
      faceKey.intensity = 0;
      rim.intensity = 0;
      dash.intensity = 0;
    }
    if (!pose) return;
    // Seated phase haunts ONLY the mirror (vanishing if you turn around); snap-lunge manifests
    // physically INSIDE the cabin between the front seats as well as filling the mirror!
    const mask = pose.inCabin ? 0x0fffffff | MIRROR_ONLY : MIRROR_ONLY;
    for (const mesh of form.meshes) {
      mesh.layerMask = mask;
      mesh.visibility = pose.presence;
    }
    this.riderEyes.emissiveColor
      .set(0.78, 0.76, 0.72)
      .scaleInPlace(pose.presence * (0.8 + 0.2 * Math.sin(t * 2.3)) + flash * 0.9);
    form.root.position.set(pose.x, pose.y, pose.z);
    form.root.rotation.set(pose.lean, pose.kind === "lean" ? 0.02 : 0.06, 0);
    // Upright haunting stare framing her gaunt pale face, jet-black hair & white shoulders cleanly
    // inside the rear-view mirror just like the approved preview!
    form.pose(
      "stand",
      pose.kind === "lean"
        ? 1.8 + (t - TAXI_MIRROR.lean.from) * 0.5
        : t - TAXI_MIRROR.seated.from + 1.5,
    );
    form.root.computeWorldMatrix(true);
    // Lock her gaze directly into the rear-view mirror and straight at Sora.
    form.lookAt(
      pose.kind === "lean" ? new Vector3(0.06, 1.06, 0.36) : this.game.camera.globalPosition,
      pose.attention,
    );
  }

  /**
   * The cabin is not a still life: the charm on the mirror swings with every bend,
   * bump and stab of the brake, and the driver breathes, then flinches.
   */
  private updateCabinLife(dt: number, t: number, speed: number, flash: number): void {
    if (dt <= 0) return;
    const yaw = this.route.rotation.y,
      turnRate = (yaw - this.lastYaw) / dt,
      braking = (speed - this.lastSpeed) / dt;
    this.lastYaw = yaw;
    this.lastSpeed = speed;
    if (this.charm?.rotationQuaternion) {
      // A short pendulum (about 0.15 m) pushed by the car's turning and braking.
      const k = 64,
        damping = 1.4,
        swing = this.charmSwing,
        jolt = Math.sin(t * 9.9 + 0.7) * 0.6 * (speed / 6.8);
      swing.sideRate +=
        (-k * swing.side - damping * swing.sideRate - turnRate * speed * 4 + jolt) * dt;
      swing.side += swing.sideRate * dt;
      swing.pitchRate += (-k * swing.pitch - damping * swing.pitchRate + braking * 4) * dt;
      swing.pitch += swing.pitchRate * dt;
      swing.side = Math.max(-0.6, Math.min(0.6, swing.side));
      swing.pitch = Math.max(-0.5, Math.min(0.5, swing.pitch));
      Quaternion.FromEulerAnglesToRef(swing.pitch, 0, swing.side, this.charm.rotationQuaternion);
    }
    // Live steering wheel turn following road curvature, rut vibration and the driver's emergency swerves.
    if (this.wheel?.rotationQuaternion && this.wheelBase) {
      const targetAngle = Math.max(
        -0.95,
        Math.min(
          0.95,
          turnRate * 1.45 + taxiSwerve(t) * 6.5 + Math.sin(t * 7.3) * 0.025 * (speed / 6.8),
        ),
      );
      this.wheelAngle += (targetAngle - this.wheelAngle) * (1 - Math.exp(-dt * 14));
      this.wheelBase.multiplyToRef(
        Quaternion.RotationAxis(Vector3.Up(), this.wheelAngle),
        this.wheel.rotationQuaternion,
      );
    }
    // He blinks every few seconds, twice in quick succession now and then, and
    // screws his eyes half shut when something crosses the road.
    if (t < this.blinkAt) this.blinkAt = t - 1;
    if (t - this.blinkAt > this.nextBlink) {
      this.blinkAt = t;
      const beat = Math.sin(t * 12.9898) * 43758.5453;
      this.nextBlink = beat - Math.floor(beat) < 0.2 ? 0.32 : 2.2 + (beat - Math.floor(beat)) * 3.4;
    }
    const since = t - this.blinkAt,
      lid = since < 0.07 ? since / 0.07 : since < 0.22 ? 1 - (since - 0.07) / 0.15 : 0;
    for (const target of this.blinkTargets) target.influence = Math.max(lid, taxiFlinch(t) * 0.55);
    // Lips, glances, nods and his hand on the wheel follow the conversation.
    const want = taxiDriverFace(t),
      follow = 1 - Math.exp(-dt / 0.12);
    for (const name of Object.keys(this.face) as (keyof DriverFace)[]) {
      // The jaw follows syllables closely; the head turns more slowly.
      this.face[name] +=
        (want[name] - this.face[name]) *
        (name === "talk" ? Math.min(1, follow * 1.4) : follow * 0.6);
      for (const target of this.faceTargets.get(name) ?? []) target.influence = this.face[name];
    }
    if (this.driver) {
      const flinch = taxiFlinch(t);
      this.driver.rotation.x = Math.sin(t * 1.45) * 0.006 - flinch * 0.06 - flash * 0.01;
      this.driver.rotation.y = flinch * 0.05;
      this.driver.rotation.z = Math.sin(t * 0.37) * 0.004;
    }
  }

  /**
   * The cluster's five instruments as a 1930s French car carried them, ivory faces gone
   * the colour of tea: fuel, ammeter, the speedometer, oil pressure and the clock.
   */
  private paintDials(speed: number): void {
    const c = this.dialTexture.getContext() as CanvasRenderingContext2D;
    c.clearRect(0, 0, 1024, 256);
    const r = 74;
    const needle = (cx: number, a: number, length: number) => {
      c.strokeStyle = "#1a120a";
      c.lineWidth = 4;
      c.beginPath();
      c.moveTo(cx - Math.cos(a) * 12, 128 - Math.sin(a) * 12);
      c.lineTo(cx + Math.cos(a) * length, 128 + Math.sin(a) * length);
      c.stroke();
    };
    for (const [i, u] of DIALS.entries()) {
      const cx = u * 1024;
      // Nickel bezel, then the aged ivory face.
      c.fillStyle = "#4b4740";
      c.beginPath();
      c.arc(cx, 128, r + 6, 0, Math.PI * 2);
      c.fill();
      const face = c.createRadialGradient(cx - 18, 110, 8, cx, 128, r);
      face.addColorStop(0, "#cdbf9a");
      face.addColorStop(1, "#8f7f5c");
      c.fillStyle = face;
      c.beginPath();
      c.arc(cx, 128, r, 0, Math.PI * 2);
      c.fill();
      c.strokeStyle = "#2a2116";
      c.fillStyle = "#2a2116";
      c.lineWidth = 2;
      c.textAlign = "center";
      c.textBaseline = "middle";
      const ticks = i === 4 ? 12 : 10;
      for (let k = 0; k <= ticks; k++) {
        const a = i === 4 ? (k / 12) * Math.PI * 2 : Math.PI * 0.75 + (k / ticks) * Math.PI * 1.5,
          inner = r - (k % 2 === 0 ? 14 : 8);
        c.beginPath();
        c.moveTo(cx + Math.cos(a) * (r - 3), 128 + Math.sin(a) * (r - 3));
        c.lineTo(cx + Math.cos(a) * inner, 128 + Math.sin(a) * inner);
        c.stroke();
      }
      c.font = "15px Georgia";
      const label = ["ESSENCE", "AMPÈRES", "km/h", "HUILE", ""][i];
      if (label) c.fillText(label, cx, 128 + r * 0.45);
      if (i === 2) {
        c.font = "13px Georgia";
        for (let k = 0; k <= 10; k += 2) {
          const a = Math.PI * 0.75 + (k / 10) * Math.PI * 1.5;
          c.fillText(String(k * 10), cx + Math.cos(a) * (r - 26), 128 + Math.sin(a) * (r - 26));
        }
      }
      const value =
        i === 0 ? 0.31 : i === 1 ? 0.56 : i === 2 ? (speed * 3.6) / 100 : i === 3 ? 0.42 : 0;
      if (i === 4) {
        // The clock stopped long ago at twenty past eight, as the studio's did.
        needle(cx, -Math.PI / 2 + (8.33 / 12) * Math.PI * 2, r * 0.48);
        needle(cx, -Math.PI / 2 + (20 / 60) * Math.PI * 2, r * 0.72);
      } else needle(cx, Math.PI * 0.75 + Math.min(1, value) * Math.PI * 1.5, r - 16);
      c.fillStyle = "#1a120a";
      c.beginPath();
      c.arc(cx, 128, 6, 0, Math.PI * 2);
      c.fill();
    }
    this.dialTexture.update();
  }
}
