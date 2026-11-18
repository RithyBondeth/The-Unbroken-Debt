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
import { CreateTube } from "@babylonjs/core/Meshes/Builders/tubeBuilder";
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
const MIRROR_FOG = [0.035, 0.04, 0.05] as const;

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
  /** The left lamp's shadows, and the roadside that may cast into them. */
  private headlampShadow: ShadowGenerator | null = null;
  private shadowCasters: AbstractMesh[] = [];
  private shadowStretch = Number.NaN;
  /** The candle at the Neak Ta's shrine. */
  private readonly shrineCandle: PointLight | null = null;
  private readonly mist: TaxiMist;
  private readonly headlamps: { light: SpotLight; power: number }[] = [];
  private readonly dash: PointLight;
  private readonly dials: StandardMaterial;
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
    // Young rice is a deep wet green, darker than the forest's grass it borrows.
    const rice = scene.getMaterialByName("M_taxi_rice");
    if (rice instanceof PBRMaterial) rice.albedoColor.multiplyInPlace(new Color3(0.42, 0.55, 0.36));
    const hemi = new HemisphericLight("taxi_storm_bounce", new Vector3(0.2, 1, -0.3), scene);
    hemi.diffuse.set(0.48, 0.56, 0.72);
    hemi.groundColor.set(0.13, 0.16, 0.2);
    hemi.specular.set(0.03, 0.04, 0.06);
    hemi.intensity = NIGHT_LOOK.skyIntensity;
    const moon = new DirectionalLight("taxi_moonlight", new Vector3(-0.25, -0.45, -0.85), scene);
    moon.diffuse = Color3.FromHexString("#7F9FD6");
    moon.specular.set(0.1, 0.13, 0.18);
    moon.intensity = NIGHT_LOOK.moonIntensity;
    this.flash = new DirectionalLight("taxi_storm_flash", new Vector3(0.4, -1, 0.5), scene);
    this.flash.diffuse.set(0.75, 0.82, 1);
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
    // The oil lamp behind the stilt house's shutters, the only light out on the paddies.
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
      anchorAt(scene, `wiper_${side}`, new Vector3(side === "l" ? -0.23 : 0.23, 1.112, 0.455)),
    );
    this.glass = new TaxiRain(scene, {
      min: anchorAt(scene, "windscreen_min", new Vector3(-0.485, 0.875, 0.49)),
      max: anchorAt(scene, "windscreen_max", new Vector3(0.485, 1.115, 0.45)),
      wipers: wiperPivots,
      blade: 0.205,
    });
    const sideGlass = scene.materials.find((m) => m.name === "M_taxi_window_glass");
    if (sideGlass instanceof PBRMaterial) {
      sideGlass.albedoTexture = this.glass.sideTexture;
      sideGlass.emissiveTexture = this.glass.sideTexture;
      sideGlass.useAlphaFromAlbedoTexture = true;
      sideGlass.alpha = 0.65;
      sideGlass.emissiveColor.set(0.13, 0.17, 0.21);
    }

    // A warm practical from the instrument cluster leaves the rest of the cabin in cool bounce.
    const cluster = anchorAt(scene, "dials", new Vector3(0, 0.72, 0.508));
    const dash = new PointLight(
      "taxi_dashboard_glow",
      cluster.add(new Vector3(0, 0.1, -0.26)),
      scene,
    );
    dash.diffuse.set(0.78, 0.65, 0.37);
    dash.intensity = 0.35;
    dash.range = 1.6;
    // Not the window glass: a lamp's point reflected in it reads as a white star.
    dash.includedOnlyMeshes = cabinMeshes.filter((m) => m.material?.name !== "M_taxi_window_glass");
    this.dash = dash;
    for (const side of ["l", "r"]) {
      const x = side === "l" ? -0.6 : 0.6;
      const headlamp = new SpotLight(
        `taxi_headlight_${side}`,
        // In the Rosalie's own lamp bowls, either side of the radiator shell.
        anchorAt(scene, `headlamp_${side}`, new Vector3(x * 0.72, 0.485, 1.74)),
        new Vector3(x < 0 ? -0.09 : 0.09, -0.08, 1).normalize(),
        1.25,
        1.5,
        scene,
      );
      headlamp.diffuse.set(1, 0.87, 0.63);
      headlamp.intensity = x < 0 ? 1500 : 2200;
      headlamp.range = 42;
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
      scene.materials.find((m) => m.name === "M_taxi_aged_nickel") ??
      new PBRMaterial("taxi_wiper_nickel", scene);
    const rubber = scene.materials.find((m) => m.name === "M_taxi_rubber") ?? metal;
    // Vacuum wipers hung from the head of the glass, as the period cars had them: each
    // sprung arm and rubber blade lies on the outside of the leaning windscreen.
    for (const [i, at] of wiperPivots.entries()) {
      const pivot = new TransformNode(`taxi_wiper_pivot_${i}`, scene);
      pivot.position.set(at.x, at.y, at.z + 0.012);
      pivot.rotation.x = -0.166;
      const arm = CreateTube(
        "taxi_wiper_sprung_arm",
        {
          path: [
            new Vector3(0, 0, 0),
            new Vector3(0.006, -0.08, 0.006),
            new Vector3(0, -0.2, 0.008),
          ],
          radius: 0.004,
          tessellation: 8,
        },
        scene,
      );
      arm.parent = pivot;
      arm.material = metal;
      arm.isPickable = false;
      const blade = CreateTube(
        "taxi_wiper_rubber_blade",
        {
          path: [
            new Vector3(0, -0.06, 0.011),
            new Vector3(0, -0.13, 0.012),
            new Vector3(0, -0.205, 0.011),
          ],
          radius: 0.0065,
          tessellation: 8,
        },
        scene,
      );
      blade.parent = pivot;
      blade.material = rubber;
      blade.isPickable = false;
      this.wipers.push(pivot);
    }
    this.dialTexture = new DynamicTexture(
      "taxi_analogue_gauges",
      { width: 1024, height: 256 },
      scene,
      false,
    );
    const dials = new StandardMaterial("taxi_instrument_glass_and_print", scene);
    dials.diffuseTexture = this.dialTexture;
    dials.emissiveTexture = this.dialTexture;
    dials.emissiveColor.set(0.3, 0.25, 0.15);
    dials.disableLighting = true;
    dials.specularColor = Color3.Black();
    this.dials = dials;
    // Over the car's own cluster: five small instruments behind one strip of glass.
    const instruments = CreatePlane("taxi_instrument_face", { width: 0.33, height: 0.082 }, scene);
    instruments.position.set(cluster.x, cluster.y, cluster.z - 0.004);
    instruments.material = dials;
    instruments.isPickable = false;
    this.paintDials(6.8);
    // The rear-view mirror, as the driver set it: angled down and across so that
    // from Sora's seat it frames the back seat behind her. A fixed camera at the
    // glass, drawn flipped, keeps that view steady however she turns her head.
    const glassAt = anchorAt(scene, "mirror", new Vector3(0, 1.102, 0.398)),
      rearSeat = anchorAt(scene, "rear_seat", new Vector3(0.25, 0.4, -1.05));
    const mirrorEye = new FreeCamera(
      "taxi_rear_view_eye",
      glassAt.add(new Vector3(0, 0, -0.02)),
      scene,
    );
    mirrorEye.setTarget(rearSeat.add(new Vector3(-0.1, 0.32, -0.3)));
    // Vertical field: a band from the seat cushion to the rear window's top.
    mirrorEye.fov = 0.4;
    mirrorEye.minZ = 0.05;
    mirrorEye.maxZ = 8;
    // Only the RTT renders through it; it must not take part in input or the main view.
    mirrorEye.inputs.clear();
    mirrorEye.layerMask = 0x0fffffff | MIRROR_ONLY;
    this.mirror = new RenderTargetTexture("taxi_rear_view", { width: 384, height: 160 }, scene);
    this.mirror.activeCamera = mirrorEye;
    // Through the rear and side glass: the night fog behind the car.
    this.mirror.clearColor = new Color4(...MIRROR_FOG, 1);
    // A plain colour pass: the SSAO pre-pass belongs to the player's camera only.
    this.mirror.noPrePassRenderer = true;
    scene.customRenderTargets.push(this.mirror);
    // A touch brighter than the cabin seen directly: eyes adjust to the small bright glass.
    this.mirror.level = 1.6;
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
    mirrorMaterial.emissiveColor.set(0.92, 0.95, 0.93);
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
    this.spiritFill.diffuse.set(0.68, 0.76, 0.95);
    this.spiritFill.specular.set(0.15, 0.17, 0.22);
    this.spiritFill.range = 3.2;
    this.spiritFill.intensity = 0;
    this.spiritFill.includedOnlyMeshes = this.spirit.meshes.filter((m) => m.getTotalVertices() > 0);
    // Shown once, behind the black of the opening, so its shaders are compiled before it is needed.
    this.spirit.pose("stand", 0);
    this.spirit.root.position.set(0, -50, 0);
    this.rider = new MocapFigure(spiritAsset, "taxi_mirror_rider");
    this.rider.setEnabled(false);
    this.mirror.renderList.push(...this.rider.meshes);
    // Two lights that touch only the rider: the cold night through Sora's side
    // glass across its face, and the dash's warm glow from below.
    for (const [name, at, colour, range] of [
      ["taxi_mirror_rider_rim", new Vector3(0.7, 1.05, -0.75), new Color3(0.55, 0.64, 0.85), 2.4],
      ["taxi_mirror_rider_dash", new Vector3(0.1, 0.65, 0.3), new Color3(0.85, 0.62, 0.36), 2.2],
    ] as const) {
      const light = new PointLight(name, at, scene);
      light.diffuse = colour;
      light.range = range;
      light.intensity = 0;
      light.includedOnlyMeshes = this.rider.meshes;
      this.riderLights.push(light);
    }
    // In the dark of the back seat the mirror shows little but its eyes: the chalk
    // whites catch what light there is, pale and fixed on the back of Sora's head.
    this.riderEyes = new StandardMaterial("M_taxi_mirror_rider_eyes", scene);
    this.riderEyes.disableLighting = true;
    this.riderEyes.diffuseColor.set(0, 0, 0);
    for (const mesh of this.rider.meshes) {
      if (/_eye_\d/.test(mesh.name)) mesh.material = this.riderEyes;
      // Its own two lights come last in the scene: room for them past the storm's.
      else if (mesh.material instanceof PBRMaterial) mesh.material.maxSimultaneousLights = 16;
    }
    // It is on a layer only the mirror's camera draws: turning round finds the seat empty.
    for (const mesh of this.rider.meshes) mesh.layerMask = MIRROR_ONLY;
    const soraGlass = cabinMeshes.find(
      (m): m is Mesh => m instanceof Mesh && m.name.startsWith("taxi_side_glass_sora"),
    );
    if (soraGlass) this.glassMarks = new TaxiGlassMarks(scene, soraGlass);
    this.mist = new TaxiMist(game, route);
    ageTaxiCabin(scene);
    this.charm = scene.getTransformNodeByName("taxi_mirror_charm_pivot");
    if (this.charm) this.charm.rotationQuaternion ??= Quaternion.Identity();
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
      if (material instanceof PBRMaterial) material.maxSimultaneousLights = 8;
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
        if (material.name !== "M_taxi_driver_head_scan") material.roughness = 0.52;

        material.metallic = 0;
      }
      if (
        /^M_taxi_(driver_clothes_scan|driver_shirt_scan|sora_trousers_scan|sora_blouse_scan)$/.test(
          material.name,
        )
      ) {
        // Woven cotton and wool: matte. (Babylon's sheen lifts dark cloth to grey here.)
        material.metallic = 0;
        material.roughness = 0.88;
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
      /taxi_driver|taxi_charm|taxi_mirror_surface|taxi_instrument_face|taxi_side_glass_sora/;
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
        applyRainWetness(material);
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
    scene.clearColor = new Color4(...NIGHT_LOOK.clearColor, 1);
    return new TaxiVisuals(game, cabinMeshes, route, landscape, spiritAsset);
  }
  configure(): void {
    const g = this.game;
    g.atmosphere.baseExposure = NIGHT_LOOK.baseExposure;
    g.atmosphere.maxExposure = NIGHT_LOOK.maxExposure;
    g.atmosphere.nightSightIntensity = NIGHT_LOOK.nightSightIntensity;
    g.atmosphere.nightSight.range = 2.8;
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
    this.flash.intensity = flash * 3;
    if (this.shrineCandle)
      this.shrineCandle.intensity =
        1.6 * (0.7 + 0.18 * Math.sin(t * 13.3) + 0.12 * Math.sin(t * 31.1 + 2)) * (1 - flash * 0.5);
    if (this.houseLamp)
      this.houseLamp.intensity =
        6 * (0.82 + 0.1 * Math.sin(t * 9.1) + 0.08 * Math.sin(t * 23.7 + 1.3));
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
    // The car's electrics fail when something is close: lamps, dash and dials together.
    const power = taxiElectrics(t);
    for (const lamp of this.headlamps) lamp.light.intensity = lamp.power * power;
    this.dash.intensity = 0.35 * (0.15 + 0.85 * power);
    this.dials.emissiveColor.set(0.45, 0.38, 0.22).scaleInPlace(0.12 + 0.88 * power);
    this.mist.update(dt, t, distance, power, flash);
    this.updateCabinLife(dt, t, speed, flash);
    // Small suspension movement, tied to speed, leaves mouse look independent of the car body.
    const bump = (Math.sin(t * 5.6) * 0.0028 + Math.sin(t * 9.9 + 0.7) * 0.0012) * (speed / 6.8);
    const flinch = taxiFlinch(t);
    g.camera.position.y = g.player.feet.y + this.eyeHeight + bump - flinch * 0.014;
    g.camera.rotation.z =
      (Math.sin(t * 1.15) * 0.003 + Math.sin(t * 3.1) * 0.001) * (speed / 6.8) + swerve * 0.25;
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
    this.spiritFill.intensity = atTheGlass ? flash * 9 : 0;
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

  /** The back-seat rider, posed for the mirror; the mirror refreshes every frame while it is there. */
  private updateMirrorRider(t: number, flash: number): void {
    const pose = taxiMirrorRiderAt(t),
      form = this.rider;
    form.setEnabled(pose !== null);
    this.mirror.refreshRate = pose ? 1 : 3;
    // The fog behind the car; the lightning turns it white.
    const [fr, fg, fb] = MIRROR_FOG;
    this.mirror.clearColor.set(fr + flash * 0.5, fg + flash * 0.55, fb + flash * 0.62, 1);
    const [rim, dash] = this.riderLights;
    rim.intensity = pose ? 1.6 + flash * 8 : 0;
    dash.intensity = pose ? 1.8 * taxiElectrics(t) : 0;
    if (!pose) return;
    for (const mesh of form.meshes) mesh.visibility = pose.presence;
    this.riderEyes.emissiveColor
      .set(0.62, 0.6, 0.55)
      .scaleInPlace(pose.presence * (0.75 + 0.25 * Math.sin(t * 2.3)) + flash);
    form.root.position.set(pose.x, pose.y, pose.z);
    form.root.rotation.set(pose.lean, pose.kind === "lean" ? -0.3 : 0.06, 0);
    // Sitting far too tall, then the arms coming up as it leans in between the seats.
    if (pose.kind === "lean") form.pose("reach", 0.5 + (t - TAXI_MIRROR.lean.from) * 1.4, false);
    else form.pose("stand", t - TAXI_MIRROR.seated.from + 1.5);
    form.root.computeWorldMatrix(true);
    form.lookAt(this.game.camera.globalPosition, pose.attention);
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
    c.fillStyle = "#14110c";
    c.fillRect(0, 0, 1024, 256);
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
