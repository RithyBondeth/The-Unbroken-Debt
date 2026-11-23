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
import { TaxiTallGrass } from "./TaxiTallGrass";
import { ageTaxiCabin } from "./taxiCabinWear";
import { TaxiGlassMarks } from "./TaxiGlassMarks";

/** A layer the player's camera never draws (its mask is the default 0x0FFFFFFF). */
const MIRROR_ONLY = 0x10000000;
/** Leaf materials the headlamps reach, graded to match ep1-refine's deep wet jungle palette. */
const FOLIAGE_IN_THE_LAMPS =
  /^(M_forest_leaf|fern_02|shrub_02|M_bamboo_leaves|M_palm_fan|M_forest_grass|M_taxi_rice|banana_leef|M_ep1_flora_|M_flora_|M_paddy_rice_)/;
const HEADLAMP_LEAF_TINT = new Color3(0.42, 0.5, 0.34);

/**
 * Whether a cabin mesh is visible behind the rear-view mirror (excludes exterior bodywork,
 * fenders, front dashboard/footwell, driver, and Sora to cut mirror RTT cost by ~80%).
 */
function isMirrorCabinMesh(mesh: AbstractMesh): boolean {
  if (
    /taxi_driver|taxi_sora|taxi_charm|mirror|gardeboue|body_lacquer|taxi_steering|taxi_dash_|taxi_meter_|taxi_underdash|taxi_firewall|taxi_trans_|taxi_gear_|taxi_handbrake|taxi_wing_mirror|taxi_wiper_motor|taxi_indicator|taxi_ignition|taxi_key_fob|taxi_rubber_floor|taxi_floor_mat|taxi_tracked_mud|taxi_footwell|taxi_kick_piping|taxi_cowl_vent|taxi_door_sill/.test(
      mesh.name,
    )
  )
    return false;
  if (
    /M_gardeboue|M_taxi_body_lacquer|M_taxi_headlamp|M_taxi_sora|M_taxi_driver|M_cab_radio|M_cab_meter|M_cab_footwell/.test(
      mesh.material?.name ?? "",
    )
  )
    return false;
  mesh.computeWorldMatrix(true);
  return mesh.getBoundingInfo().boundingBox.minimumWorld.z < 0.15;
}

/** Procedural organic radial alpha mask so road puddles feather naturally into wet laterite mud. */
function makePuddleEdgeMask(scene: Scene): RawTexture {
  const size = 128;
  const data = new Uint8Array(size * size * 4);
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const u = (x + 0.5) / size - 0.5;
      const v = (y + 0.5) / size - 0.5;
      const ang = Math.atan2(v, u);
      const r = Math.hypot(u, v) * 2;
      // Organic ruffled shoreline edge matching natural rain puddles in wheel ruts
      const edge =
        0.92 +
        0.045 * Math.sin(ang * 5 + 0.8) +
        0.025 * Math.sin(ang * 11 - 1.3) +
        0.015 * Math.cos(ang * 17 + 0.4);
      const t = Math.max(0, Math.min(1, (edge - r) / 0.36));
      const alpha = Math.round(t * t * (3 - 2 * t) * 238);
      const i = (y * size + x) * 4;
      data[i] = alpha;
      data[i + 1] = alpha;
      data[i + 2] = alpha;
      data[i + 3] = alpha;
    }
  }
  const tex = RawTexture.CreateRGBATexture(data, size, size, scene, true, false);
  tex.name = "taxi_puddle_edge_alpha";
  tex.hasAlpha = true;
  tex.wrapU = 0; // CLAMP_ADDRESSMODE
  tex.wrapV = 0;
  return tex;
}

/** Layered raindrop impact concentric rings + monsoon wind micro-ripples normal map. */
function makeRainRippleNormals(scene: Scene): RawTexture {
  const size = 256;
  const heights = new Float32Array(size * size);
  const drops = [
    [0.18, 0.24, 0.13, 1.0],
    [0.64, 0.19, 0.11, 0.85],
    [0.42, 0.58, 0.15, 0.95],
    [0.82, 0.67, 0.12, 0.8],
    [0.21, 0.81, 0.1, 0.75],
    [0.73, 0.41, 0.09, 0.7],
    [0.52, 0.88, 0.11, 0.82],
    [0.08, 0.52, 0.095, 0.72],
    [0.91, 0.14, 0.085, 0.68],
  ] as const;
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const u = x / size;
      const v = y / size;
      let h =
        Math.sin((u * 4 + v * 3) * Math.PI * 2) * 0.16 +
        Math.sin((-u * 6 + v * 5) * Math.PI * 2) * 0.12 +
        Math.cos((u * 9 - v * 8) * Math.PI * 2) * 0.07;
      for (const [cx, cy, rad, amp] of drops) {
        let dx = u - cx;
        let dy = v - cy;
        if (dx > 0.5) dx -= 1;
        if (dx < -0.5) dx += 1;
        if (dy > 0.5) dy -= 1;
        if (dy < -0.5) dy += 1;
        const d = Math.hypot(dx, dy);
        if (d < rad) {
          const k = d / rad;
          const env = (1 - k) * (1 - k) * Math.min(1, k * 6);
          h += Math.sin(k * Math.PI * 5) * env * amp * 0.55;
        }
      }
      heights[y * size + x] = h;
    }
  }
  const normals = new Uint8Array(size * size * 4);
  const strength = 0.55;
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const xm = (x - 1 + size) % size;
      const xp = (x + 1) % size;
      const ym = (y - 1 + size) % size;
      const yp = (y + 1) % size;
      const nx = -(heights[y * size + xp] - heights[y * size + xm]) * strength;
      const ny = -(heights[yp * size + x] - heights[ym * size + x]) * strength;
      const len = Math.hypot(nx, ny, 1);
      const i = (y * size + x) * 4;
      normals[i] = Math.round(127.5 + (nx / len) * 127.5);
      normals[i + 1] = Math.round(127.5 + (ny / len) * 127.5);
      normals[i + 2] = Math.round(127.5 + 127.5 / len);
      normals[i + 3] = 255;
    }
  }
  const tex = RawTexture.CreateRGBATexture(normals, size, size, scene, true, false);
  tex.name = "taxi_shallow_water_ripples";
  tex.level = 0.34;
  return tex;
}

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
const MIRROR_FOG = [0.042, 0.062, 0.088] as const;

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
  private readonly tallGrass: TaxiTallGrass;
  private readonly mist: TaxiMist;
  private readonly headlamps: { light: SpotLight; power: number }[] = [];
  private readonly dash: PointLight;
  private readonly domeLight: PointLight;
  private readonly mirrorCabinFill: PointLight;
  private mirrorFillTarget = 0;
  private mirrorRiderBoost = 0;
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
  private readonly paddyReflection: MirrorTexture;
  private paddyReflectionActive = true;
  private readonly waterRipples: Texture;
  private puddleRipples: Texture | null = null;
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
    const pbrMaterials = [...materials].filter((m): m is PBRMaterial => m instanceof PBRMaterial);
    for (const plugin of applyFoliageWind(pbrMaterials, game.wind)) {
      const owner = pbrMaterials.find((m) => m.pluginManager?.getPlugin("FoliageWind") === plugin);
      if (owner?.name.startsWith("M_paddy_rice_")) plugin.ground = TAXI_PADDY_WATER - 0.08;
      else if (owner?.name.startsWith("M_flora_")) plugin.ground = -0.39;
    }
    // Under headlamps and lightning a few metres off, pale leaf tints burn to flat pastel
    // cards. Wet old-growth leaves stay a deep, glossy dark green.
    for (const material of materials) {
      if (!(material instanceof PBRMaterial)) continue;
      if (FOLIAGE_IN_THE_LAMPS.test(material.name)) {
        if (material.name.startsWith("M_flora_") || material.name.startsWith("M_ep1_flora_")) {
          // ep1-refine scanned forest_tree_gn, banana_clump, and sugar_palm materials:
          // preserve their deep wet tropical green and bark palette, never washing out in headlamps!
          const isLeaf = /Cluster|Vines|Leaf|Material_5\d/.test(material.name);
          material.albedoColor.multiplyInPlace(
            isLeaf ? new Color3(0.58, 0.7, 0.5) : new Color3(0.54, 0.5, 0.46),
          );
          material.directIntensity = isLeaf ? 0.68 : 0.56;
          material.roughness = isLeaf ? 0.42 : 0.68;
          material.specularIntensity = isLeaf ? 0.28 : 0.16;
          if (material.transparencyMode === PBRMaterial.PBRMATERIAL_ALPHABLEND)
            material.transparencyMode = PBRMaterial.PBRMATERIAL_ALPHATEST;
        } else if (material.name.startsWith("M_paddy_rice_")) {
          // ep1-refine transplanted flooded rice hills (green & ripening golden-green):
          const isRipe = material.name.includes("ripe");
          material.albedoColor.multiplyInPlace(
            isRipe ? new Color3(0.95, 0.9, 0.65) : new Color3(0.8, 1.0, 0.68),
          );
          material.roughness = 0.56;
          material.specularIntensity = 0.24;
          material.directIntensity = 0.92;
          material.backFaceCulling = false;
          if (material.transparencyMode === PBRMaterial.PBRMATERIAL_ALPHABLEND)
            material.transparencyMode = PBRMaterial.PBRMATERIAL_ALPHATEST;
        } else {
          material.albedoColor.multiplyInPlace(HEADLAMP_LEAF_TINT);
          if (/^(fern_02|shrub_02|M_forest_leaf)$/.test(material.name)) {
            material.directIntensity = 0.62;
            material.roughness = 0.44;
            material.specularIntensity = 0.25;
          }
        }
      }
      if (material.name === "M_forest_grass") {
        // Deep wet night-time grass blades so close twin headlamps never turn median tufts neon-green.
        material.albedoColor.set(0.008, 0.014, 0.007);
        material.directIntensity = 0.3;
        material.roughness = 0.92;
        material.specularIntensity = 0.02;
        material.clearCoat.isEnabled = false;
      }
    }
    // The village's hanging moss and liana strands are a flat pale grey; wet, at night,
    // they are near black, and must not hang in the lamps like white rods.
    const moss = scene.getMaterialByName("M_forest_moss");
    if (moss instanceof PBRMaterial) {
      moss.albedoColor.set(0.03, 0.036, 0.026);
      moss.roughness = 0.8;
    }
    // Young rice in flooded fields: rich wet Cambodian paddy green matching ep1-refine without specular sparks.
    const rice = scene.getMaterialByName("M_taxi_rice");
    if (rice instanceof PBRMaterial) {
      rice.albedoColor.multiplyInPlace(new Color3(0.54, 0.72, 0.42));
      rice.roughness = 0.68;
      rice.specularIntensity = 0.14;
      rice.directIntensity = 0.65;
    }
    // Deep moody monsoon storm night matching ep1-refine's VILLAGE_NIGHT cool blue-slate mist & canopy bounce:
    // silhouettes of sugar palms, banana groves, and old-growth crowns separate cleanly against the blue-grey mist!
    const hemi = new HemisphericLight("taxi_storm_bounce", new Vector3(0.2, 1, -0.3), scene);
    hemi.diffuse.set(0.38, 0.46, 0.62);
    hemi.groundColor.set(0.06, 0.08, 0.11);
    hemi.specular.set(0.02, 0.026, 0.038);
    hemi.intensity = NIGHT_LOOK.skyIntensity * 0.46;
    const moon = new DirectionalLight("taxi_moonlight", new Vector3(-0.25, -0.45, -0.85), scene);
    moon.diffuse = Color3.FromHexString("#7A9AD4");
    moon.specular.set(0.06, 0.08, 0.12);
    moon.intensity = NIGHT_LOOK.moonIntensity * 0.28;
    this.flash = new DirectionalLight("taxi_storm_flash", new Vector3(0.4, -1, 0.5), scene);
    this.flash.diffuse.set(0.68, 0.78, 1);
    this.flash.intensity = 0;
    this.sky = new StormSky(scene);
    const roadReflection = new MirrorTexture("taxi_standing_water_reflection", 256, scene, false);
    roadReflection.mirrorPlane = new Plane(0, 1, 0, 0.058 - TAXI_GROUND_DROP);
    roadReflection.refreshRate = 3;
    roadReflection.level = 0.52;
    roadReflection.blurKernel = 6;
    roadReflection.renderParticles = false;
    // At night the ruts' water shows the storm sky and the dark line of the crowns
    // against it, not the trunks: the far cards stand in for the forest, at a fraction
    // of its cost (the full roadside here doubled the frame every third frame).
    roadReflection.renderList = [
      ...forest.filter((m) => m.name.startsWith("taxi_far_forest")),
      this.sky.dome,
    ];
    // The flood over the paddies holds the storm sky, the distant palms and stilt houses;
    // exclude tiny roadside shop props, posters, mud & puddles so draw calls stay low and FPS stays high!
    const paddyReflection = new MirrorTexture("taxi_paddy_flood_reflection", 256, scene, false);
    paddyReflection.mirrorPlane = new Plane(0, 1, 0, -TAXI_PADDY_WATER);
    paddyReflection.refreshRate = 5;
    paddyReflection.level = 0.72;
    paddyReflection.blurKernel = 10;
    paddyReflection.renderParticles = false;
    paddyReflection.renderList = [
      ...forest.filter((m) => {
        const mn = m.material?.name ?? "";
        // Allowlist ONLY tall silhouettes that read in the blurry flooded-paddy reflections
        // (soaring palms, stilt houses, far treeline) -> cuts ~350 mirror draw calls!
        if (
          !/^(M_palm_trunk|M_palm_fan|Wash_|Wahs_|M_flora_sugar_palm_|M_taxi_palm_card|M_wet_bark|M_forest_leaf)/.test(
            mn,
          ) &&
          !/stilt_house|far_forest/.test(m.name)
        )
          return false;
        return m.getBoundingInfo().boundingBox.minimumWorld.z < TAXI_FOREST_START + 30;
      }),
      this.sky.dome,
    ];
    this.paddyReflection = paddyReflection;
    this.waterRipples = makeRainRippleNormals(scene);
    const puddleMask = makePuddleEdgeMask(scene);
    const puddleRipples = this.waterRipples.clone();
    puddleRipples.uScale = puddleRipples.vScale = 4.2;
    puddleRipples.level = 0.52;
    this.puddleRipples = puddleRipples;
    for (const mesh of landscape) {
      if (!(mesh.material instanceof PBRMaterial)) continue;
      if (mesh.material.name === "M_puddle") {
        // Deep dark rainwater reflecting storm sky & headlamp glints with soft feathered mud edges!
        // Disable radiance/specular-over-alpha & depth write so shorelines blend seamlessly into wet mud!
        mesh.material.reflectionTexture = roadReflection;
        mesh.material.bumpTexture = puddleRipples;
        mesh.material.opacityTexture = puddleMask;
        mesh.material.transparencyMode = PBRMaterial.PBRMATERIAL_ALPHABLEND;
        mesh.material.useRadianceOverAlpha = false;
        mesh.material.useSpecularOverAlpha = false;
        mesh.material.forceDepthWrite = false;
        mesh.material.needDepthPrePass = false;
        mesh.material.albedoColor.set(0.006, 0.008, 0.01);
        mesh.material.roughness = 0.036;
        mesh.material.specularIntensity = 0.88;
        mesh.material.directIntensity = 0.42;
        mesh.material.alpha = 0.94;
      } else if (mesh.material.name === "M_ditch_water") {
        mesh.material.reflectionTexture = roadReflection;
        mesh.material.bumpTexture = this.waterRipples;
        mesh.material.albedoColor.set(0.008, 0.01, 0.011);
        mesh.material.roughness = 0.05;
        mesh.material.specularIntensity = 0.72;
        mesh.material.directIntensity = 0.42;
      } else if (mesh.material.name === "M_taxi_paddy_water") {
        mesh.material.reflectionTexture = paddyReflection;
        mesh.material.bumpTexture = this.waterRipples;
        mesh.material.albedoColor.set(0.012, 0.016, 0.02);
        mesh.material.roughness = 0.08;
        mesh.material.directIntensity = 0.55;
      }
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
    // Warm flickering practical bulbs under the roadside wooden shops and Khmer 90s poster boards
    // (calibrated so every hand-painted Khmer 90s shop sign stays rich, colourful and legible with zero white blowout!).
    for (const node of scene.transformNodes) {
      const shopMatch = /^taxi_road_anchor_(shop|poster|shop_int)_lamp_(\d+)$/.exec(node.name);
      if (!shopMatch) continue;
      const kind = shopMatch[1];
      const isShop = kind === "shop" || kind === "shop_int";
      const idx = Number(shopMatch[2]);
      node.computeWorldMatrix(true);
      const pos = node.getAbsolutePosition().clone();
      const lamp = new PointLight(`taxi_${kind}_lamp_${idx}`, pos, scene);
      lamp.parent = route;
      if (kind === "shop_int") {
        // Authentic 90s rural Cambodian contrast: cool-white 4ft fluorescent tube inside Barber/Dentist/Moto
        // shops (1, 2, 4) vs warm golden tungsten bulbs inside Noodle, TV, Grocery, Salon & Outpost shops!
        if (idx === 1 || idx === 2 || idx === 4) {
          lamp.diffuse.set(0.82, 0.94, 1);
          lamp.specular.set(0.24, 0.28, 0.32);
        } else {
          lamp.diffuse.set(1, 0.72, 0.34);
          lamp.specular.set(0.3, 0.22, 0.1);
        }
        lamp.range = 8.8;
      } else if (kind === "shop") {
        lamp.diffuse.set(1, 0.66, 0.28);
        lamp.specular.set(0.28, 0.18, 0.09);
        lamp.range = 11.8;
      } else {
        lamp.diffuse.set(1, 0.74, 0.38);
        lamp.specular.set(0.18, 0.14, 0.08);
        lamp.range = 6.5;
      }
      const base = kind === "shop" ? 10.6 : kind === "shop_int" ? 10.2 : 2.8;
      lamp.intensity = base;
      lamp.includedOnlyMeshes = within(forest, pos, lamp.range);
      lamp.setEnabled(false);
      this.roadsideLamps.push({
        light: lamp,
        base,
        z: pos.z,
        phase: idx * 2.17 + (kind === "shop" ? 0.5 : kind === "shop_int" ? 1.8 : 3.9),
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
    const domeLight = new PointLight("taxi_cabin_dome_light", new Vector3(0, 1.21, -0.54), scene);
    domeLight.diffuse.set(1, 0.78, 0.46);
    domeLight.specular.set(0.05, 0.04, 0.02);
    domeLight.intensity = 0.42;
    domeLight.range = 2.75;
    domeLight.includedOnlyMeshes = cabinSolid;
    this.domeLight = domeLight;

    // Soft natural interior bounce over Sora's cream blouse, hands on her thighs, satchel & shoes.
    const soraFill = new PointLight("taxi_sora_lap_fill", new Vector3(0.24, 0.94, 0.24), scene);
    soraFill.diffuse.set(0.9, 0.8, 0.64);
    soraFill.specular.set(0.025, 0.02, 0.015);
    soraFill.intensity = 0.11;
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
        // Only vertical roadside structures/trees in the beam cast shadows (skip flat ground, mud,
        // puddles, grass and pebbles to cut shadow-map triangle cost by >60%!).
        this.shadowCasters = landscape.filter((mesh) => {
          if ((mesh.metadata as { batchGroup?: string } | null)?.batchGroup === "distant")
            return false;
          const matName = mesh.material?.name ?? "";
          if (
            /^(M_wet_forest_floor|M_wet_mud|M_taxi_laterite|M_puddle|M_ditch_water|M_taxi_paddy_water|M_taxi_dike_earth|M_forest_grass|M_taxi_rice)$/.test(
              matName,
            )
          )
            return false;
          return !/pebble|median_grass|rut_water|ditch_water|muddy_track|laterite_track|road_ground/.test(
            mesh.name,
          );
        });
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

      const metalParts = [cap, collar, arm, saddle, spine];
      for (const cy of [-0.086, -0.226]) {
        const claw = CreateBox(
          `taxi_wiper_claw_${i}_${cy}`,
          { width: 0.0046, height: 0.007, depth: 0.0048 },
          scene,
        );
        claw.position.set(0, cy, 0.0042);
        part(claw, metal);
        metalParts.push(claw);
      }
      const mergedMetal = Mesh.MergeMeshes(metalParts, true, true);
      if (mergedMetal) {
        mergedMetal.name = `taxi_wiper_frame_${i}`;
        mergedMetal.parent = pivot;
        mergedMetal.material = metal;
        mergedMetal.isPickable = false;
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
    // The rear-view mirror, as the driver set it: angled cleanly across the tufted rear bench
    // and storm-lit rear window—and directly onto the ghost when she appears behind Sora.
    const glassAt = anchorAt(scene, "mirror", new Vector3(0, 1.102, 0.398));
    const mirrorEye = new FreeCamera(
      "taxi_rear_view_eye",
      glassAt.add(new Vector3(0, 0, -0.02)),
      scene,
    );
    mirrorEye.setTarget(new Vector3(0.05, 0.89, -1.15));
    // Vertical field: frames both the tufted rear seatback and the rear window clouds, plus the ghost.
    mirrorEye.fov = 0.42;
    mirrorEye.minZ = 0.05;
    mirrorEye.maxZ = 120;
    // Only the RTT renders through it; it must not take part in input or the main view.
    mirrorEye.inputs.clear();
    mirrorEye.layerMask = 0x0fffffff | MIRROR_ONLY;
    this.mirror = new RenderTargetTexture("taxi_rear_view", { width: 512, height: 212 }, scene);
    this.mirror.activeCamera = mirrorEye;
    // Through the rear and side glass: dark storm night (sky dome supplies the real clouds & flashes).
    this.mirror.clearColor = new Color4(...MIRROR_FOG, 1);
    // A plain colour pass: the SSAO pre-pass belongs to the player's camera only.
    this.mirror.noPrePassRenderer = true;
    scene.customRenderTargets.push(this.mirror);
    this.mirror.level = 2.85;
    this.mirror.refreshRate = 3;
    this.mirror.renderParticles = false;
    // Render ONLY rear-visible cabin interior meshes + storm sky dome (~85% fewer mirror tris!).
    const rearCabinMeshes = cabinMeshes.filter((m) => {
      const g = (m.metadata as { batchGroup?: string } | null)?.batchGroup;
      if (g) return g.startsWith("rear|");
      return isMirrorCabinMesh(m);
    });
    this.mirror.renderList = [...rearCabinMeshes, this.sky.dome];
    // Mirror-only rear-cabin fill light: turned ON exclusively during the rear-view mirror RTT pass
    // (and turned off right after) so forward headlamp auto-exposure never crushes the mirror glass
    // to black while keeping Sora's direct look-back rear cabin view 100% moody and natural!
    const mirrorCabinFill = new PointLight(
      "taxi_mirror_rear_bench_fill",
      new Vector3(0.05, 1.06, -0.78),
      scene,
    );
    mirrorCabinFill.diffuse.set(0.95, 0.84, 0.68);
    mirrorCabinFill.specular.set(0.08, 0.07, 0.05);
    mirrorCabinFill.intensity = 0;
    mirrorCabinFill.range = 2.8;
    mirrorCabinFill.renderPriority = 10;
    mirrorCabinFill.includedOnlyMeshes = rearCabinMeshes.filter(
      (m) => m.material?.name !== "M_taxi_window_glass",
    );
    this.mirrorCabinFill = mirrorCabinFill;
    let savedRiderIntensities: number[] = [];
    this.mirror.onBeforeRenderObservable.add(() => {
      this.mirrorCabinFill.intensity = this.mirrorFillTarget;
      if (this.mirrorRiderBoost > 0 && this.riderLights.length === 3) {
        // mirror.level is already 2.85x to keep the dark rear cabin legible, so tame the
        // mirror-pass face key to preserve eerie pale facial sculpting with zero white blowout!
        savedRiderIntensities = this.riderLights.map((l) => l.intensity);
        this.riderLights[0].intensity *= 0.42;
        this.riderLights[1].intensity *= 0.78;
        this.riderLights[2].intensity *= 0.45;
      } else {
        savedRiderIntensities = [];
      }
    });
    this.mirror.onAfterRenderObservable.add(() => {
      this.mirrorCabinFill.intensity = 0;
      if (savedRiderIntensities.length === this.riderLights.length) {
        for (let i = 0; i < this.riderLights.length; i++)
          this.riderLights[i].intensity = savedRiderIntensities[i];
        savedRiderIntensities = [];
      }
    });
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
    // Three dedicated cold-moonlight horror lights sculpting her pale gaunt face, staring eyes &
    // white dress while keeping her long wet black hair deeply jet-black (zero orange nose-glare!).
    for (const [name, at, colour, range] of [
      ["taxi_mirror_rider_face", new Vector3(0.06, 0.96, -0.18), new Color3(0.84, 0.9, 1), 2.8],
      ["taxi_mirror_rider_rim", new Vector3(0.55, 1.12, -0.92), new Color3(0.62, 0.76, 1), 2.8],
      ["taxi_mirror_rider_dash", new Vector3(-0.22, 0.9, -0.18), new Color3(0.76, 0.82, 0.92), 2.4],
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
    this.tallGrass = new TaxiTallGrass(scene, route, game.wind, game.preset.name === "low");
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
      if (material instanceof PBRMaterial) material.maxSimultaneousLights = 12;
    // Keep high simultaneous-light headroom and deeply matte hair/cloth shading on both ghost
    // figures AFTER the global cap so their face lights stay active and white cloth never blows out!
    for (const mesh of this.rider.meshes)
      if (mesh.material instanceof PBRMaterial) {
        mesh.material.maxSimultaneousLights = 16;
        mesh.material.roughness = 0.96;
        mesh.material.specularIntensity = 0.02;
        mesh.material.environmentIntensity = 0.22;
        mesh.material.directIntensity = 0.72;
      }
    for (const mesh of this.spirit.meshes)
      if (mesh.material instanceof PBRMaterial) {
        mesh.material.maxSimultaneousLights = 16;
        mesh.material.roughness = 0.96;
        mesh.material.specularIntensity = 0.02;
        mesh.material.environmentIntensity = 0.16;
        // Prevents close 2400-intensity twin headlamps & lightning from turning her white dress into HDR bloom.
        mesh.material.directIntensity = 0.28;
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
        /^M_taxi_(driver_skin|driver_hands_scan|sora_skin_scan|driver_head_scan|driver_neck_skin)$/.test(
          material.name,
        )
      ) {
        // Subtle natural subsurface warmth (restrained on driver head/neck & Sora hands so skin never glows orange).
        material.subSurface.isTranslucencyEnabled = true;
        material.subSurface.translucencyIntensity =
          material.name === "M_taxi_driver_head_scan" || material.name === "M_taxi_driver_neck_skin"
            ? 0.14
            : material.name === "M_taxi_sora_skin_scan"
              ? 0.2
              : 0.28;
        material.subSurface.tintColor =
          material.name === "M_taxi_sora_skin_scan"
            ? new Color3(0.84, 0.56, 0.44)
            : new Color3(0.9, 0.48, 0.34);
        // The scanned face carries its own roughness map (wet eyes, lips, oily nose, cotton cap);
        // match driver neck roughness & specular identically so the jaw-to-neck lighting is seamless!
        if (material.name === "M_taxi_driver_head_scan") {
          material.specularIntensity = 0.24;
        } else if (material.name === "M_taxi_driver_neck_skin") {
          material.roughness = 0.56;
          material.specularIntensity = 0.24;
        } else {
          material.roughness = 0.64;
          material.specularIntensity = 0.2;
        }

        material.metallic = 0;
      }
      if (
        /^M_taxi_(driver_clothes_scan|driver_shirt_scan|sora_trousers_scan|sora_blouse_scan)$/.test(
          material.name,
        ) ||
        /^M_cab_(driver_krama|driver_cuff_cotton|sora_cuff_linen)$/.test(material.name)
      ) {
        // Woven cotton and linen: deeply matte and silky-smooth so close cabin practicals never cause harsh creases.
        material.metallic = 0;
        material.roughness = 0.94;
        material.specularIntensity = 0.03;
      }
      if (material.name === "M_cab_gauge_crystal") {
        material.transparencyMode = PBRMaterial.PBRMATERIAL_ALPHABLEND;
        material.alpha = 0.12;
        material.metallic = 0;
        material.roughness = 0.04;
        material.specularIntensity = 0.9;
        material.forceDepthWrite = false;
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
      group: (mesh) =>
        `${isMirrorCabinMesh(mesh) ? "rear" : "front"}|${mesh.getVerticesDataKinds().sort().join(",")}`,
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
          // Real hand-painted Khmer 90s shop signs & posters: crisp saturation with damp night sheen (never white-clipped!).
          material.albedoColor.set(0.76, 0.74, 0.7);
          material.metallic = 0;
          material.roughness = 0.56;
          material.clearCoat.isEnabled = true;
          material.clearCoat.intensity = 0.22;
          material.clearCoat.roughness = 0.26;
        } else if (
          /^M_taxi_shop_(bulb|fluoro|crt|mirror|window_glow|noodle_glow|shrine_glow|foliage)$/.test(
            material.name,
          )
        ) {
          // Preserve authored emissive shop bulbs, fluorescent tubes, CRT glow, amber windows, shrines & deep wet planters.
          material.metallic = material.name === "M_taxi_shop_mirror" ? 0.96 : material.metallic;
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
    scene.clearColor = new Color4(0.007, 0.01, 0.014, 1);
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
      g.pipeline.fog.density = 0.034;
      g.pipeline.fog.heightFalloff = 0.22;
      // Cool blue-slate monsoon mist matching ep1-refine's VILLAGE_NIGHT farmstead renders!
      g.pipeline.fog.ambient.set(0.015, 0.02, 0.029);
    } else {
      g.scene.fogDensity = 0.034;
      g.scene.fogColor.set(0.015, 0.02, 0.029);
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
    // The car's electrics fail when something is close: compute early so shadows, rain & lights all sync.
    const power = taxiElectrics(t);
    // Disable paddy water mirror reflection once deep inside the dark jungle (> 165 m).
    const needPaddyMirror = distance < TAXI_PADDY_END + 25;
    if (needPaddyMirror !== this.paddyReflectionActive) {
      this.paddyReflectionActive = needPaddyMirror;
      this.paddyReflection.refreshRate = needPaddyMirror
        ? 4
        : RenderTargetTexture.REFRESHRATE_RENDER_ONCE;
    }
    // The lamps' shadows come from the 40 m of vertical roadside structures in front of the car.
    const stretch = Math.floor(distance / 6);
    if (this.headlampShadow) {
      const shadowMap = this.headlampShadow.getShadowMap();
      if (shadowMap) {
        shadowMap.refreshRate =
          power > 0.05
            ? RenderTargetTexture.REFRESHRATE_RENDER_ONEVERYFRAME
            : RenderTargetTexture.REFRESHRATE_RENDER_ONCE;
        if (stretch !== this.shadowStretch) {
          this.shadowStretch = stretch;
          const list = shadowMap.renderList!;
          list.length = 0;
          for (const chunk of this.routeChunks)
            if (
              chunk.maxZ > distance - 2 &&
              chunk.minZ < distance + 40 &&
              this.shadowCasters.includes(chunk.mesh)
            )
              list.push(chunk.mesh);
        }
      }
    }
    // A swerve turns the car, so the world turns about the passenger instead of the route origin.
    const pose = taxiRoadPose(distance),
      swerve = taxiSwerve(t),
      c = Math.cos(swerve),
      s = Math.sin(swerve);
    this.route.rotation.y = pose.yaw + swerve;
    this.route.position.set(pose.x * c + pose.z * s, 0, -pose.x * s + pose.z * c);
    // Storm lightning tuned for high-contrast moody silver-blue highlights (never washes foliage to flat pastel).
    this.flash.intensity = flash * 2.15;
    if (this.shrineCandle)
      this.shrineCandle.intensity =
        1.6 * (0.7 + 0.18 * Math.sin(t * 13.3) + 0.12 * Math.sin(t * 31.1 + 2)) * (1 - flash * 0.5);
    if (this.houseLamp)
      this.houseLamp.intensity =
        6 * (0.82 + 0.1 * Math.sin(t * 9.1) + 0.08 * Math.sin(t * 23.7 + 1.3));
    // Animate warm shop & Khmer poster practicals only near the car (<= 42 m), and sweep warm light
    // across the dark cabin as the taxi rolls past each detailed roadside shop!
    let bestSweep = 0;
    let sweepZ = 0;
    let sweepSide = -1;
    for (const lamp of this.roadsideLamps) {
      const dz = lamp.z - distance;
      const near = Math.abs(dz) < 42;
      if (lamp.light.isEnabled() !== near) lamp.light.setEnabled(near);
      if (!near) continue;
      const flutter =
        0.88 +
        0.07 * Math.sin(t * 11.3 + lamp.phase) +
        0.05 * Math.sin(t * 27.1 + lamp.phase * 1.7);
      lamp.light.intensity = lamp.base * flutter;
      const closeness = Math.exp(-((dz / 6.5) ** 2)) * (lamp.isShop ? 1 : 0.4);
      if (closeness > bestSweep) {
        bestSweep = closeness;
        sweepZ = dz * 0.14;
        sweepSide = lamp.light.position.x < taxiRoadX(lamp.z) ? -1 : 1;
      }
    }
    this.cabinShopSweep.intensity = bestSweep * 0.54;
    this.cabinShopSweep.position.set(sweepSide * 1.05, 1.05, Math.max(-0.8, Math.min(1.1, sweepZ)));
    this.sky.update(flash, g.pipeline.main.imageProcessing.exposure, dt);
    for (const wiper of this.wipers) wiper.rotation.z = angle;
    this.glass.update(dt, angle, flash, power);
    this.waterRipples.uOffset = t * 0.011;
    this.waterRipples.vOffset = t * 0.008;
    if (this.puddleRipples) {
      this.puddleRipples.uOffset = t * 0.032;
      this.puddleRipples.vOffset = -t * 0.024;
    }
    // Rain running back along the bonnet in the wind of the car's speed.
    if (this.bonnetBeads) this.bonnetBeads.vOffset = -t * 0.05 * (speed / 6.8);
    this.rain.update(t, speed, flash);
    this.updateSpirit(t, flash);
    this.updateMirrorRider(t, flash);
    this.glassMarks?.update(t, flash);
    for (const lamp of this.headlamps) lamp.light.intensity = lamp.power * power;
    this.dash.intensity = 0.18 * (0.12 + 0.88 * power);
    this.domeLight.intensity = 0.42 * (0.06 + 0.94 * power);
    this.mirrorFillTarget = 2.8 * (0.12 + 0.88 * power) + flash * 1.6;
    this.mirrorCabinFill.intensity = 0;
    this.soraFill.intensity = 0.11 * (0.14 + 0.86 * power) + flash * 0.12;
    this.footwellLight.intensity = 0.24 * (0.08 + 0.92 * power) + flash * 0.1;
    this.roadBounce.intensity = 0.16 * power + flash * 0.34;
    this.roadBounce.diffuse.set(
      0.84 * (1 - flash * 0.3) + 0.65 * flash * 0.3,
      0.72 * (1 - flash * 0.3) + 0.78 * flash * 0.3,
      0.48 * (1 - flash * 0.5) + 1.0 * flash * 0.5,
    );
    this.dials.emissiveColor.set(0.58, 0.46, 0.25).scaleInPlace(0.12 + 0.88 * power);
    if (this.radioDialMat) this.radioDialMat.emissiveIntensity = 0.15 + 1.55 * power;
    if (this.domeGlassMat) this.domeGlassMat.emissiveIntensity = 0.08 + 1.35 * power;
    if (this.footwellBulbMat) this.footwellBulbMat.emissiveIntensity = 0.1 + 2.1 * power;
    this.tallGrass.update(distance);
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
      // Cold lightning silhouette inches off the wet bonnet: hauntingly legible gaunt face & bloodied cloth, zero white bloom!
      this.spiritFill.position.set(0.18, 0.96, 2.15);
      this.spiritFill.range = 4.6;
      this.spiritFill.intensity = 0.48 + flash * 0.92;
    } else if (pose?.kind === "window") {
      // Positioned cleanly between Sora's passenger glass and the ghost's face outside so her
      // gaunt features & white dress read vividly while her black hair stays pitch-black!
      this.spiritFill.position.set(0.68, 1.06, -0.04);
      this.spiritFill.range = 2.6;
      this.spiritFill.intensity = 0.52 + flash * 1.45;
    } else if (atTheGlass) {
      this.spiritFill.position.set(0.58, 1.05, 0.12);
      this.spiritFill.range = 3.2;
      this.spiritFill.intensity = flash * 2.2;
    } else if (pose?.kind === "crossing") {
      this.spiritFill.position.set(0, 1.15, 4.8);
      this.spiritFill.range = 9.5;
      this.spiritFill.intensity = flash * 1.25;
    } else if (pose?.kind === "stander") {
      this.spiritFill.position.set(1.3, 1.1, 4.2);
      this.spiritFill.range = 9.5;
      this.spiritFill.intensity = flash * 1.8;
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
    // Moody storm blue-grey behind the rear window (real clouds come from sky.dome — never a harsh white bar!).
    const [fr, fg, fb] = MIRROR_FOG;
    this.mirror.clearColor.set(fr + flash * 0.1, fg + flash * 0.13, fb + flash * 0.17, 1);
    const [faceKey, rim, dash] = this.riderLights;
    if (pose) {
      const p = pose.presence;
      const lungeBoost = pose.kind === "lean" ? 1.4 : 0.95;
      this.mirrorRiderBoost = p;
      faceKey.intensity = p * (1.85 * lungeBoost + flash * 1.9);
      rim.intensity = p * (1.25 * lungeBoost + flash * 1.45);
      dash.intensity = p * (0.65 * taxiElectrics(t) + 0.35);
    } else {
      this.mirrorRiderBoost = 0;
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
    // Live steering wheel turn following road curvature & emergency swerves (bounded cleanly so the
    // driver's scanned hands stay seated naturally around the sculpted 1933 bakelite rim!).
    if (this.wheel?.rotationQuaternion && this.wheelBase) {
      const targetAngle = Math.max(
        -0.32,
        Math.min(
          0.32,
          turnRate * 0.85 + taxiSwerve(t) * 2.8 + Math.sin(t * 7.3) * 0.018 * (speed / 6.8),
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
