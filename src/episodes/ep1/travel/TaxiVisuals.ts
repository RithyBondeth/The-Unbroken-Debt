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
import { Color3, Color4 } from "@babylonjs/core/Maths/math.color";
import { Plane } from "@babylonjs/core/Maths/math.plane";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { CreateBox } from "@babylonjs/core/Meshes/Builders/boxBuilder";
import { CreateTube } from "@babylonjs/core/Meshes/Builders/tubeBuilder";
import { PointLight } from "@babylonjs/core/Lights/pointLight";
import { HemisphericLight } from "@babylonjs/core/Lights/hemisphericLight";
import { DirectionalLight } from "@babylonjs/core/Lights/directionalLight";
import { SpotLight } from "@babylonjs/core/Lights/spotLight";
import { ShadowGenerator } from "@babylonjs/core/Lights/Shadows/shadowGenerator";
import { realiseInstances } from "../../../core/AreaLoader";
import { addStaticBox } from "../../../core/Physics";
import { buildTaxiRoadside } from "./TaxiRoadside";
import { StormSky } from "../act1/StormSky";
import { ShadowFigure } from "../entities/ShadowFigure";
import { NIGHT_LOOK } from "../data/nightLook";
import { TaxiWeather } from "./TaxiWeather";
import { TaxiFoliageWind } from "./TaxiFoliageWind";
import { TaxiRain } from "./TaxiRain";
import {
  taxiDistance,
  taxiRoadX,
  taxiRoadPose,
  taxiRouteChunkVisible,
  taxiSpeed,
  taxiWiperAngle,
} from "./taxiMotion";

/** Authored cabin, Act I foliage/materials, physical headlights and the same storm grade. */
export class TaxiVisuals {
  private readonly route: TransformNode;
  private readonly wind: TaxiFoliageWind[] = [];
  private readonly routeChunks: { mesh: Mesh; minZ: number; maxZ: number; active: boolean }[] = [];
  private readonly wipers: TransformNode[] = [];
  private readonly sky: StormSky;
  private readonly flash: DirectionalLight;
  private readonly rain: TaxiWeather;
  private readonly glass: TaxiRain;
  private readonly watcher: ShadowFigure;
  private readonly dialTexture: DynamicTexture;
  private dialIn = 0;
  private readonly mirror: MirrorTexture;

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
    const leafMaterials = new Set(landscape.map((mesh) => mesh.material));
    for (const material of leafMaterials)
      if (material instanceof PBRMaterial && /leaf|leaves|palm_fan/.test(material.name))
        this.wind.push(new TaxiFoliageWind(material));
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
    roadReflection.mirrorPlane = new Plane(0, 1, 0, 0.111);
    roadReflection.refreshRate = 3;
    roadReflection.level = 0.4;
    roadReflection.blurKernel = 8;
    roadReflection.renderParticles = false;
    roadReflection.renderList = [
      ...landscape.filter((m) => m.material?.name !== "M_puddle"),
      this.sky.dome,
    ];
    for (const mesh of landscape)
      if (mesh.material instanceof PBRMaterial && mesh.material.name === "M_puddle") {
        mesh.material.reflectionTexture = roadReflection;
        mesh.material.roughness = 0.09;
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
    this.watcher = new ShadowFigure(scene, "taxi_roadside_watcher", 2.05);
    this.watcher.root.parent = route;
    const watcherZ = taxiDistance(35.8) + 14;
    this.watcher.root.position.set(taxiRoadX(watcherZ) + 3.7, 0, watcherZ);
    this.watcher.root.rotation.y = -Math.PI * 0.75;
    this.watcher.root.setEnabled(false);
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
    for (const material of cabin.materials)
      if (material instanceof PBRMaterial && material.name === "M_taxi_dashboard_walnut")
        material.albedoColor.scaleInPlace(3);
    for (const material of cabin.materials)
      if (material instanceof PBRMaterial && material.name === "M_taxi_window_glass")
        material.specularIntensity = 0.03;
    realiseInstances(cabin);
    const cabinMeshes = cabin.meshes.filter((m) => m.getTotalVertices() > 0);
    for (const material of roadside.materials)
      if (material instanceof PBRMaterial) {
        material.maxSimultaneousLights = 8;
        if (material.name.startsWith("M_wet_")) {
          material.albedoColor.scaleInPlace(0.86);
          material.roughness = 0.92;
        }
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
    g.camera.maxZ = 60;
    if (g.pipeline.fog) {
      g.pipeline.fog.density = NIGHT_LOOK.fogDensity;
      g.pipeline.fog.heightFalloff = 0.25;
      g.pipeline.fog.ambient.set(...NIGHT_LOOK.fogAmbient);
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
    const pose = taxiRoadPose(distance);
    this.route.rotation.y = pose.yaw;
    this.route.position.set(pose.x, 0, pose.z);
    this.flash.intensity = flash * 3;
    this.sky.update(flash, g.pipeline.main.imageProcessing.exposure, dt);
    for (const wiper of this.wipers) wiper.rotation.z = angle;
    this.glass.update(dt, angle, flash);
    this.rain.update(t, speed, flash);
    for (const wind of this.wind) wind.seconds = t;
    this.watcher.root.setEnabled(t > 35.8 && t < 39.0);
    this.watcher.animate(t, 0);
    // Small suspension movement, tied to speed, leaves mouse look independent of the car body.
    const bump = (Math.sin(t * 5.6) * 0.0028 + Math.sin(t * 9.9 + 0.7) * 0.0012) * (speed / 6.8);
    g.camera.position.y = g.player.feet.y + 1.31 + bump;
    g.camera.rotation.z = (Math.sin(t * 1.15) * 0.003 + Math.sin(t * 3.1) * 0.001) * (speed / 6.8);
    this.dialIn -= dt;
    if (this.dialIn <= 0) {
      this.dialIn = 0.1;
      this.paintDials(speed);
    }
    g.atmosphere.update(dt, 0.22 + flash * 0.3);
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
