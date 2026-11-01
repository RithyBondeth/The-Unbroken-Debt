import type { Game } from "../../../core/Game";
import { LoadAssetContainerAsync } from "@babylonjs/core/Loading/sceneLoader";
import { registerBuiltInLoaders } from "@babylonjs/loaders/dynamic";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { VertexData } from "@babylonjs/core/Meshes/mesh.vertexData";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { StandardMaterial } from "@babylonjs/core/Materials/standardMaterial";
import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import { MirrorTexture } from "@babylonjs/core/Materials/Textures/mirrorTexture";
import { Texture } from "@babylonjs/core/Materials/Textures/texture";
import { RawTexture } from "@babylonjs/core/Materials/Textures/rawTexture";
import { Color3, Color4 } from "@babylonjs/core/Maths/math.color";
import { Plane } from "@babylonjs/core/Maths/math.plane";
import { Quaternion, Vector3 } from "@babylonjs/core/Maths/math.vector";
import { CreateBox } from "@babylonjs/core/Meshes/Builders/boxBuilder";
import { CreateTube } from "@babylonjs/core/Meshes/Builders/tubeBuilder";
import { PointLight } from "@babylonjs/core/Lights/pointLight";
import type { MorphTarget } from "@babylonjs/core/Morph/morphTarget";
import { taxiDriverFace, type DriverFace } from "./taxiDriver";
import { HemisphericLight } from "@babylonjs/core/Lights/hemisphericLight";
import { DirectionalLight } from "@babylonjs/core/Lights/directionalLight";
import { SpotLight } from "@babylonjs/core/Lights/spotLight";
import { ShadowGenerator } from "@babylonjs/core/Lights/Shadows/shadowGenerator";
import { realiseInstances } from "../../../core/AreaLoader";
import { mergeStaticMeshes } from "../../../render/StaticBatcher";
import { addStaticBox } from "../../../core/Physics";
import { buildTaxiRoadside } from "./TaxiRoadside";
import { StormSky } from "../act1/StormSky";
import { ShadowFigure } from "../entities/ShadowFigure";
import { NIGHT_LOOK } from "../data/nightLook";
import { applyRainWetness } from "../../../render/SurfaceDetail";
import { TaxiWeather } from "./TaxiWeather";
import { applyFoliageWind } from "../../../render/FoliageWind";
import { gradeJungle } from "../act1/jungleGrade";
import { TaxiRain } from "./TaxiRain";
import {
  taxiDistance,
  taxiRoadPose,
  taxiRouteChunkVisible,
  taxiSpeed,
  taxiRoadPoint,
  taxiWiperAngle,
} from "./taxiMotion";
import {
  TAXI_RITUAL_ALONG,
  TAXI_RITUAL_LATERAL,
  taxiFlinch,
  taxiRunnerAt,
  taxiSwerve,
} from "./taxiApparitions";

/** The running form and its smear: lag behind the lead (s) and how solid each is. */
const RUNNER_TRAIL = [
  [0, 1],
  [0.022, 0.42],
  [0.045, 0.18],
] as const;
/** Not the shrine's lacquer: something closer to a hole in the headlights. */
const RUNNER_BLACK = new Color3(0.004, 0.004, 0.005);

/** Authored cabin, Act I foliage/materials, physical headlights and the same storm grade. */
export class TaxiVisuals {
  readonly route: TransformNode;
  private readonly routeChunks: { mesh: Mesh; minZ: number; maxZ: number; active: boolean }[] = [];
  private readonly wipers: TransformNode[] = [];
  private readonly sky: StormSky;
  private readonly flash: DirectionalLight;
  private readonly rain: TaxiWeather;
  private readonly glass: TaxiRain;
  private readonly dialTexture: DynamicTexture;
  private dialIn = 0;
  private readonly mirror: MirrorTexture;
  private readonly waterRipples: Texture;
  private readonly runners: ShadowFigure[] = [];
  private readonly candlelight: PointLight;
  private readonly flames: PBRMaterial[] = [];
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

  private constructor(
    private readonly game: Game,
    cabinMeshes: AbstractMesh[],
    route: TransformNode,
    landscape: Mesh[],
  ) {
    const scene = game.scene;
    this.route = route;
    for (const mesh of landscape) {
      mesh.computeWorldMatrix(true);
      const box = mesh.getBoundingInfo().boundingBox;
      this.routeChunks.push({
        mesh,
        minZ: box.minimumWorld.z,
        maxZ: box.maximumWorld.z,
        active: true,
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
    roadReflection.mirrorPlane = new Plane(0, 1, 0, 0.058);
    roadReflection.refreshRate = 3;
    roadReflection.level = 0.6;
    roadReflection.blurKernel = 8;
    roadReflection.renderParticles = false;
    roadReflection.renderList = [
      ...landscape.filter((m) => m.material?.name !== "M_puddle"),
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
        mesh.material.roughness = 0.16;
      }
    this.glass = new TaxiRain(scene);
    const sideGlass = scene.materials.find((m) => m.name === "M_taxi_window_glass");
    if (sideGlass instanceof PBRMaterial) {
      sideGlass.albedoTexture = this.glass.sideTexture;
      sideGlass.emissiveTexture = this.glass.sideTexture;
      sideGlass.useAlphaFromAlbedoTexture = true;
      sideGlass.alpha = 0.65;
      sideGlass.emissiveColor.set(0.13, 0.17, 0.21);
    }

    // A warm practical from the instrument binnacle leaves the rest of the cabin in cool bounce.
    const dash = new PointLight("taxi_dashboard_glow", new Vector3(-0.34, 1.07, 0.85), scene);
    dash.diffuse.set(0.78, 0.65, 0.37);
    dash.intensity = 0.6;
    dash.range = 1.6;
    dash.includedOnlyMeshes = cabinMeshes;
    for (const x of [-0.6, 0.6]) {
      const headlamp = new SpotLight(
        `taxi_headlight_${x}`,
        new Vector3(x, 0.76, 2.52),
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
      if (x < 0) {
        const shadow = new ShadowGenerator(game.preset.name === "low" ? 512 : 1024, headlamp);
        shadow.usePercentageCloserFiltering = true;
        shadow.bias = 0.001;
        shadow.normalBias = 0.025;
        for (const mesh of landscape)
          if ((mesh.metadata as { batchGroup?: string } | null)?.batchGroup !== "distant")
            shadow.addShadowCaster(mesh, false);
      }
    }
    const metal =
      scene.materials.find((m) => m.name === "M_taxi_aged_nickel") ??
      new PBRMaterial("taxi_wiper_nickel", scene);
    const rubber = scene.materials.find((m) => m.name === "M_taxi_rubber") ?? metal;
    for (const x of [-0.43, 0.43]) {
      const pivot = new TransformNode(`taxi_wiper_pivot_${x}`, scene);
      pivot.position.set(x, 1.06, 1.268);
      pivot.rotation.x = -0.528;
      const arm = CreateTube(
        "taxi_wiper_sprung_arm",
        {
          path: [
            new Vector3(0, 0, 0),
            new Vector3(0.014, 0.16, -0.014),
            new Vector3(0, 0.42, -0.01),
          ],
          radius: 0.0055,
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
            new Vector3(0, 0.28, -0.012),
            new Vector3(0, 0.46, -0.018),
            new Vector3(0, 0.65, -0.012),
          ],
          radius: 0.009,
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
      { width: 1024, height: 512 },
      scene,
      false,
    );
    const dials = new StandardMaterial("taxi_instrument_glass_and_print", scene);
    dials.diffuseTexture = this.dialTexture;
    dials.emissiveTexture = this.dialTexture;
    dials.emissiveColor.set(0.45, 0.38, 0.22);
    dials.disableLighting = true;
    dials.specularColor = Color3.Black();
    for (const [x, r, u0, u1] of [
      [-0.49, 0.071, 0, 0.66],
      [-0.29, 0.043, 0.66, 1],
    ]) {
      const disc = new Mesh("taxi_instrument_face", scene),
        positions = [x, 0.975, 0.981],
        uv = [(u0 + u1) / 2, 0.5],
        indices: number[] = [];
      for (let i = 0; i <= 64; i++) {
        const a = (i / 64) * Math.PI * 2;
        positions.push(x + Math.cos(a) * r, 0.975 + Math.sin(a) * r, 0.981);
        uv.push(u0 + (Math.cos(a) * 0.5 + 0.5) * (u1 - u0), 0.5 + Math.sin(a) * 0.5);
        if (i < 64) indices.push(0, i + 2, i + 1);
      }
      const normals: number[] = [];
      VertexData.ComputeNormals(positions, indices, normals);
      const data = new VertexData();
      data.positions = positions;
      data.normals = normals;
      data.indices = indices;
      data.uvs = uv;
      data.applyToMesh(disc);
      disc.material = dials;
      dials.backFaceCulling = false;
      disc.isPickable = false;
    }
    this.paintDials(6.8);
    this.mirror = new MirrorTexture("taxi_rear_view", { width: 256, height: 96 }, scene, false);
    this.mirror.mirrorPlane = new Plane(0, 0, -1, 0.731);
    this.mirror.level = 0.6;
    this.mirror.refreshRate = 3;
    this.mirror.renderParticles = false;
    this.mirror.renderList = cabinMeshes.filter((m) => !/mirror|sunvisor|bonnet/.test(m.name));
    const mirrorMaterial = new StandardMaterial("taxi_mirror_silver", scene);
    mirrorMaterial.diffuseColor.set(0.035, 0.045, 0.04);
    mirrorMaterial.specularColor.set(0.3, 0.3, 0.3);
    mirrorMaterial.reflectionTexture = this.mirror;
    this.mirror.coordinatesMode = Texture.PLANAR_MODE;
    const face = cabinMeshes.find((m) => m.name.includes("taxi_mirror_surface"));
    if (face) face.material = mirrorMaterial;
    this.rain = new TaxiWeather(scene, game.preset.name === "low");
    for (const [index] of RUNNER_TRAIL.entries()) {
      const form = new ShadowFigure(scene, `taxi_road_runner_${index}`, 2.1);
      form.root.parent = route;
      form.root.setEnabled(false);
      form.darken(RUNNER_BLACK, true);
      this.runners.push(form);
    }
    // Candles still burning at the rite: one warm, guttering light for the whole ring.
    const rite = taxiRoadPoint(TAXI_RITUAL_LATERAL, TAXI_RITUAL_ALONG);
    this.candlelight = new PointLight(
      "taxi_rite_candlelight",
      new Vector3(rite.x, 0.35, rite.z),
      scene,
    );
    this.candlelight.parent = route;
    this.candlelight.diffuse.set(1, 0.58, 0.26);
    this.candlelight.specular.set(0.4, 0.25, 0.1);
    this.candlelight.range = 9;
    this.candlelight.intensity = 0;
    for (const material of scene.materials)
      if (material instanceof PBRMaterial && material.name === "M_taxi_ritual_flame")
        this.flames.push(material);
    this.charm = scene.getTransformNodeByName("taxi_mirror_charm_pivot");
    if (this.charm) this.charm.rotationQuaternion ??= Quaternion.Identity();
    // The driver's body as one piece, pivoting at his hips on the seat.
    const anatomy = cabinMeshes.find((m) => m.name.includes("taxi_driver_anatomy"));
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
    const [cabin, roadside] = await Promise.all([
      LoadAssetContainerAsync(`${base}ep1_taxi_cabin.glb`, scene),
      LoadAssetContainerAsync(`${base}ep1_taxi_roadside.glb`, scene),
      ShadowFigure.prepare(scene),
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
      if (material.name === "M_taxi_driver_skin") {
        // Light through the ears and fingers; a soft sheen of sweat rather than plastic.
        material.subSurface.isTranslucencyEnabled = true;
        material.subSurface.translucencyIntensity = 0.35;
        material.subSurface.tintColor = new Color3(0.95, 0.45, 0.32);
        material.roughness = 0.52;
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
    const apart = /taxi_driver|taxi_charm|taxi_mirror_surface|taxi_instrument_face/;
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
    game.spawnPlayer(new Vector3(0.39, 0, -0.24));
    game.player.config.standEyeHeight = 1.31;
    game.player.config.crouchEyeHeight = 1.31;
    game.player.headBobEnabled = false;
    game.player.pitch = 0.025;
    game.player.yaw = -0.12;
    scene.clearColor = new Color4(...NIGHT_LOOK.clearColor, 1);
    return new TaxiVisuals(game, cabinMeshes, route, landscape);
  }
  configure(): void {
    const g = this.game;
    g.atmosphere.baseExposure = NIGHT_LOOK.baseExposure;
    g.atmosphere.maxExposure = NIGHT_LOOK.maxExposure;
    g.atmosphere.nightSightIntensity = NIGHT_LOOK.nightSightIntensity;
    g.atmosphere.nightSight.range = 2.8;
    g.atmosphere.nightSight.excludedMeshes.push(this.glass.glass);
    // Far enough for the painted forest walls on both sides; fog closes beyond.
    g.camera.maxZ = 85;
    if (g.pipeline.fog) {
      g.pipeline.fog.density = NIGHT_LOOK.fogDensity;
      g.pipeline.fog.heightFalloff = 0.25;
      g.pipeline.fog.ambient.set(...NIGHT_LOOK.fogAmbient);
    } else {
      g.scene.fogDensity = NIGHT_LOOK.fogDensity;
      g.scene.fogColor.set(...NIGHT_LOOK.fogAmbient);
    }
  }
  update(dt: number, t: number, flash: number): void {
    const g = this.game,
      angle = taxiWiperAngle(t),
      distance = taxiDistance(t),
      speed = taxiSpeed(t);
    for (const chunk of this.routeChunks) {
      const active = taxiRouteChunkVisible(chunk.minZ, chunk.maxZ, distance);
      if (active !== chunk.active) {
        chunk.mesh.setEnabled(active);
        chunk.active = active;
      }
    }
    // A swerve turns the car, so the world turns about the passenger instead of the route origin.
    const pose = taxiRoadPose(distance),
      swerve = taxiSwerve(t),
      c = Math.cos(swerve),
      s = Math.sin(swerve);
    this.route.rotation.y = pose.yaw + swerve;
    this.route.position.set(pose.x * c + pose.z * s, 0, -pose.x * s + pose.z * c);
    this.flash.intensity = flash * 3;
    this.sky.update(flash, g.pipeline.main.imageProcessing.exposure, dt);
    for (const wiper of this.wipers) wiper.rotation.z = angle;
    this.glass.update(dt, angle, flash);
    this.waterRipples.uOffset = t * 0.009;
    this.waterRipples.vOffset = t * 0.006;
    this.rain.update(t, speed, flash);
    this.updateRunners(t);
    this.updateRite(t, distance);
    this.updateCabinLife(dt, t, speed, flash);
    // Small suspension movement, tied to speed, leaves mouse look independent of the car body.
    const bump = (Math.sin(t * 5.6) * 0.0028 + Math.sin(t * 9.9 + 0.7) * 0.0012) * (speed / 6.8);
    const flinch = taxiFlinch(t);
    g.camera.position.y = g.player.feet.y + 1.31 + bump - flinch * 0.014;
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

  /** Each pass: the lead form and two fainter copies a beat behind it, smeared by speed. */
  private updateRunners(t: number): void {
    RUNNER_TRAIL.forEach(([lag, solid], i) => {
      const form = this.runners[i],
        pose = taxiRunnerAt(t, lag);
      form.root.setEnabled(pose !== null);
      if (!pose) return;
      const edge = Math.min(1, pose.progress / 0.1, (1 - pose.progress) / 0.12);
      form.setPresence(solid * edge);
      form.root.position.set(pose.x, -0.12, pose.z);
      form.root.rotation.set(0.32, pose.heading, 0);
      form.animate(t * 4.4, 1, 0);
    });
  }

  /** Candle flames gutter in the rain; their light reaches only while the rite is near. */
  private updateRite(t: number, distance: number): void {
    const near = Math.max(0, 1 - Math.abs(distance - TAXI_RITUAL_ALONG) / 70),
      gutter =
        0.78 +
        0.12 * Math.sin(t * 13.1) +
        0.07 * Math.sin(t * 23.7 + 1.3) +
        0.05 * Math.sin(t * 41.9);
    this.candlelight.intensity = near * 3.4 * gutter;
    for (const flame of this.flames) flame.emissiveIntensity = 0.7 + 0.3 * gutter;
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

  private paintDials(speed: number): void {
    const c = this.dialTexture.getContext() as CanvasRenderingContext2D;
    c.fillStyle = "#111712";
    c.fillRect(0, 0, 1024, 512);
    for (const [cx, r, max, label] of [
      [338, 218, 100, "km/h"],
      [850, 146, 1, "FUEL"],
    ] as const) {
      c.strokeStyle = "#c3c2a0";
      c.fillStyle = "#c3c2a0";
      c.lineWidth = 3;
      for (let i = 0; i <= 20; i++) {
        const a = Math.PI * 0.78 + (i / 20) * Math.PI * 1.44,
          x = cx + Math.cos(a) * r,
          y = 256 + Math.sin(a) * r,
          rr = r - (i % 4 === 0 ? 24 : 12);
        c.beginPath();
        c.moveTo(x, y);
        c.lineTo(cx + Math.cos(a) * rr, 256 + Math.sin(a) * rr);
        c.stroke();
        if (i % 4 === 0) {
          c.font = cx === 338 ? "27px Georgia" : "25px Georgia";
          c.textAlign = "center";
          c.textBaseline = "middle";
          c.fillText(
            cx === 338 ? String((i / 20) * max) : i === 0 ? "E" : i === 20 ? "F" : "",
            cx + Math.cos(a) * (r - 47),
            256 + Math.sin(a) * (r - 47),
          );
        }
      }
      c.font = "25px Georgia";
      c.textAlign = "center";
      c.fillText(label, cx, 354);
      const value = cx === 338 ? (speed * 3.6) / 100 : 0.73,
        a = Math.PI * 0.78 + value * Math.PI * 1.44;
      c.strokeStyle = "#c8a36b";
      c.lineWidth = 5;
      c.beginPath();
      c.moveTo(cx - Math.cos(a) * 24, 256 - Math.sin(a) * 24);
      c.lineTo(cx + Math.cos(a) * (r - 38), 256 + Math.sin(a) * (r - 38));
      c.stroke();
      c.beginPath();
      c.arc(cx, 256, 11, 0, Math.PI * 2);
      c.fill();
    }
    c.fillStyle = "#30382e";
    c.fillRect(237, 290, 202, 38);
    c.fillStyle = "#c0b99b";
    c.font = "27px monospace";
    c.textAlign = "center";
    c.fillText("0 2 4 8 1", 338, 311);
    this.dialTexture.update();
  }
}
