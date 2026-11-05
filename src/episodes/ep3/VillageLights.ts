import { HemisphericLight } from "@babylonjs/core/Lights/hemisphericLight";
import { DirectionalLight } from "@babylonjs/core/Lights/directionalLight";
import { PointLight } from "@babylonjs/core/Lights/pointLight";
import { ShadowGenerator } from "@babylonjs/core/Lights/Shadows/shadowGenerator";
import { Color3, Color4 } from "@babylonjs/core/Maths/math.color";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { CreatePlane } from "@babylonjs/core/Meshes/Builders/planeBuilder";
import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { StandardMaterial } from "@babylonjs/core/Materials/standardMaterial";
import type { Game } from "../../core/Game";
import type { Area } from "../../core/AreaLoader";
import { useSoftFalloff, softFalloff } from "../../render/softLampFalloff";
import { limitLightToRange } from "../../render/RenderSetup";
import { NIGHT_LOOK } from "../ep1/data/nightLook";
import { StormSky } from "../ep1/act1/StormSky";
import { Lightning } from "../ep1/Lightning";
import { VillageRain } from "./VillageRain";
import type { VillageStage } from "./VillageProgress";
import { VillageEnvironment } from "./VillageEnvironment";
import { FoliageWind } from "../../render/FoliageWind";

/** The established Episode 1 exposure, falloff, clouds and storm, with an afternoon opening. */
export class VillageLights {
  readonly lamp: PointLight;
  readonly sky: HemisphericLight;
  readonly sun: DirectionalLight;
  readonly flames: PointLight[] = [];
  readonly lightning = new Lightning();
  private readonly clouds: StormSky;
  private readonly rain: VillageRain;
  private readonly flash: DirectionalLight;
  private stage: VillageStage = "market";
  private time = 0;
  private shade = 1;
  private readonly shadows: ShadowGenerator[] = [];
  private equipmentMeshes: AbstractMesh[] = [];
  private readonly environment: VillageEnvironment;
  private readonly heldFill: PointLight;
  private readonly ritualCandles: PointLight[] = [];
  private readonly foliage: FoliageWind[] = [];
  private readonly visibleFlames: Mesh[] = [];
  constructor(
    private readonly game: Game,
    area: Area,
  ) {
    const s = game.scene;
    this.environment = new VillageEnvironment(s, game.preset.name === "low" ? 128 : 256);
    this.sky = new HemisphericLight("lake_sky", new Vector3(0.2, 1, -0.4), s);
    this.sky.specular.set(0.025, 0.03, 0.035);
    this.sun = new DirectionalLight("lake_sun", new Vector3(0.45, -0.7, -0.35), s);
    this.sun.position.set(-30, 40, 20);
    this.sun.specular.set(0.12, 0.14, 0.16);
    this.sun.renderPriority = 4;
    this.sky.renderPriority = 3;
    this.lamp = new PointLight("player_lamp", new Vector3(-0.06, -0.14, 0.1), s);
    this.lamp.parent = game.camera;
    this.lamp.diffuse = Color3.FromHexString("#FFD4A0");
    this.lamp.range = 11.5;
    this.lamp.renderPriority = 10;
    useSoftFalloff(this.lamp);
    this.heldFill = new PointLight("ep3_flame_on_equipment", new Vector3(-0.25, -0.25, 0.68), s);
    this.heldFill.parent = game.camera;
    this.heldFill.diffuse = Color3.FromHexString("#FFD4A0");
    this.heldFill.range = 0.85;
    this.heldFill.intensity = 0.045;
    this.heldFill.renderPriority = 12;
    this.heldFill.shadowEnabled = false;
    const actors = s.meshes.filter((mesh) => {
      for (let n = mesh.parent; n; n = n.parent)
        if (/^(kanha|pich|npc_|market_resident_)/.test(n.name)) return true;
      return false;
    });
    for (const [id, p] of area.level.flames) {
      const l = new PointLight("ep3_" + id, p.position.clone(), s);
      l.diffuse = Color3.FromHexString("#FFD4A0");
      l.range = 5;
      l.intensity = 4;
      limitLightToRange(l, s.meshes, actors);
      this.flames.push(l);
    }
    const paintedFlame = area.container.meshes.find(
      (m) => m.name.startsWith("ritual_flame_0") && m.material instanceof PBRMaterial,
    )?.material as PBRMaterial | undefined;
    const flameSurface = paintedFlame ? new StandardMaterial("M_ep3_visible_flame", s) : null;
    if (flameSurface && paintedFlame) {
      const painted = paintedFlame.albedoTexture ?? paintedFlame.emissiveTexture;
      flameSurface.diffuseTexture = painted;
      flameSurface.emissiveTexture = painted;
      flameSurface.emissiveColor.set(1.25, 1.25, 1.25);
      flameSurface.diffuseColor.set(0, 0, 0);
      flameSurface.disableLighting = true;
      flameSurface.useAlphaFromDiffuseTexture = true;
      flameSurface.backFaceCulling = false;
      flameSurface.transparencyMode = StandardMaterial.MATERIAL_ALPHABLEND;
      for (const mesh of area.container.meshes)
        if (mesh.name.startsWith("ritual_flame_") && mesh.getTotalVertices()) {
          mesh.material = flameSurface;
          mesh.isPickable = false;
        }
    }
    for (const mesh of area.container.meshes) {
      let practical = false;
      for (let parent = mesh.parent; parent; parent = parent.parent)
        if (/real_practical_lantern|ep3_finish_ritual_hanging_lamp/.test(parent.name))
          practical = true;
      const mat = mesh.material;
      if (practical && mat instanceof PBRMaterial && /glass/i.test(mesh.name + mat.name)) {
        mat.alpha = 0.2;
        mat.metallic = 0;
        mat.roughness = 0.16;
        mat.transparencyMode = PBRMaterial.PBRMATERIAL_ALPHABLEND;
      }
    }
    if (flameSurface) {
      for (const light of this.flames) {
        const flame = CreatePlane("ep3_visible_oil_flame", { width: 0.026, height: 0.065 }, s);
        flame.position.copyFrom(light.position);
        flame.billboardMode = Mesh.BILLBOARDMODE_ALL;
        flame.material = flameSurface;
        flame.isPickable = false;
        this.visibleFlames.push(flame);
      }
    }
    this.flash = new DirectionalLight("lake_lightning", new Vector3(0.4, -1, 0.5), s);
    this.flash.diffuse.set(0.65, 0.75, 1);
    this.flash.intensity = 0;
    this.flash.specular.set(0.03, 0.04, 0.06);
    this.flash.renderPriority = 5;
    for (const [i, x, z] of [
      [0, -12.45, 4.5],
      [1, -11.6, 4.5],
      [2, -12, 5.3],
    ]) {
      const light = new PointLight("ep3_ritual_candle_" + i, new Vector3(x, 3.59, z), s);
      light.diffuse = Color3.FromHexString("#FFD09A");
      light.range = 2.6;
      light.intensity = 0;
      light.shadowEnabled = false;
      light.renderPriority = 2;
      this.ritualCandles.push(light);
    }
    this.clouds = new StormSky(s);
    this.clouds.dome.scaling.setAll(40);
    this.rain = new VillageRain(game);
    for (const light of [this.lamp, this.sun, this.sky, this.flash, ...this.flames])
      light.shadowEnabled = false;
    if (game.preset.name !== "low") {
      this.sun.shadowEnabled = true;
      this.sun.orthoLeft = -34;
      this.sun.orthoRight = 34;
      this.sun.orthoTop = 34;
      this.sun.orthoBottom = -34;
      this.sun.shadowMinZ = 1;
      this.sun.shadowMaxZ = 160;
      const shadows = new ShadowGenerator(game.preset.name === "medium" ? 1024 : 2048, this.sun);
      this.shadows.push(shadows);
      shadows.usePercentageCloserFiltering = true;
      shadows.bias = 0.0005;
      shadows.normalBias = 0.02;
      const moving = (mesh: Mesh) => {
        for (let n: typeof mesh.parent = mesh; n; n = n.parent)
          if (/^(kanha|pich|npc_|market_resident|curtain_motion_|collapse_beam)/.test(n.name))
            return true;
        return false;
      };
      for (const mesh of area.container.meshes) {
        mesh.receiveShadows = true;
        if (
          mesh instanceof Mesh &&
          mesh.isVisible &&
          mesh.getTotalVertices() &&
          mesh.renderingGroupId === 0
        )
          shadows.addShadowCaster(mesh);
      }
      const map = shadows.getShadowMap();
      // People and wet foliage must cast shadows where they are now. Updating
      // this pass periodically keeps contact without a stale actor silhouette.
      if (map) map.refreshRate = game.preset.name === "medium" ? 12 : 6;
      const ward = this.flames.find((light) => light.name.includes("ward"));
      if (ward && game.preset.name !== "medium") {
        ward.shadowEnabled = true;
        const contact = new ShadowGenerator(512, ward);
        contact.usePoissonSampling = true;
        contact.bias = 0.003;
        contact.normalBias = 0.012;
        this.shadows.push(contact);
        for (const mesh of area.container.meshes)
          if (
            mesh instanceof Mesh &&
            mesh.isVisible &&
            mesh.getTotalVertices() &&
            !moving(mesh) &&
            Vector3.Distance(mesh.getBoundingInfo().boundingSphere.centerWorld, ward.position) < 8
          )
            contact.addShadowCaster(mesh);
        const shadow = contact.getShadowMap();
        let frames = 0;
        const freezeContact = s.onAfterRenderObservable.add(() => {
          if (++frames < 12) return;
          if (shadow) {
            shadow.refreshRate = 0;
            shadow.resetRefreshCounter();
          }
          freezeContact?.remove();
        });
        s.onDisposeObservable.addOnce(() => contact.dispose());
      }
      s.onDisposeObservable.addOnce(() => shadows.dispose());
    }
    // Match main's material/light budget, including glTF materials imported late.
    s.requireLightSorting = true;
    for (const mat of area.container.materials)
      if (mat instanceof PBRMaterial) {
        mat.maxSimultaneousLights = 8;
        if (/^M_ep3_(wood|dark)$/.test(mat.name)) {
          mat.albedoColor.scaleInPlace(0.82);
          mat.clearCoat.isEnabled = true;
          mat.clearCoat.intensity = 0.16;
          mat.clearCoat.roughness = 0.46;
        }
        if (mat.name.startsWith("M_ep3_real_drowned_skin")) mat.albedoColor.set(0.42, 0.5, 0.47);
        if (/leaf|leaves/.test(mat.name)) this.foliage.push(new FoliageWind(mat));
        if (mat.name.startsWith("M_ep3_real_corroded_steel")) {
          mat.backFaceCulling = false;
          mat.twoSidedLighting = true;
        }
      }
  }
  begin(): void {
    this.game.addFlameLights(this.lamp, ...this.flames.slice(0, 3));
    this.setStage(this.stage);
  }
  lightEquipment(meshes: AbstractMesh[]): void {
    this.equipmentMeshes = meshes;
    this.heldFill.includedOnlyMeshes = meshes;
    for (const light of this.flames) light.excludedMeshes.push(...meshes);
    for (const light of this.ritualCandles) light.excludedMeshes.push(...meshes);
    this.setStage(this.stage);
  }
  setStage(stage: VillageStage): void {
    this.stage = stage;
    const day = stage === "market",
      dawn = stage === "dawn" || stage === "complete",
      memory = stage === "memory",
      g = this.game;
    const bright = day || dawn || memory;
    this.environment.setStage(day, dawn, memory);
    for (const light of [this.sky, this.sun])
      light.excludedMeshes = bright ? [] : this.equipmentMeshes;
    this.sun.position.set(day ? -64 : 8, day ? 32 : 26, day ? 10 : 14);
    this.sun.direction.set(day ? 0.45 : -0.25, day ? -0.7 : -0.45, day ? -0.35 : -0.85);
    for (const shadow of this.shadows) shadow.getShadowMap()?.resetRefreshCounter();
    this.clouds.dome.setEnabled(!bright);
    g.scene.clearColor = bright
      ? new Color4(day ? 0.22 : 0.18, day ? 0.25 : 0.21, 0.23, 1)
      : new Color4(...NIGHT_LOOK.clearColor, 1);
    this.sky.intensity = day ? 0.16 : dawn ? 0.3 : memory ? 0.3 : NIGHT_LOOK.skyIntensity * 0.45;
    this.sky.diffuse.set(day ? 0.61 : 0.48, day ? 0.7 : 0.57, day ? 0.73 : 0.65);
    this.sky.groundColor.set(0.1, 0.12, 0.11);
    this.sun.diffuse.set(bright ? 1 : 0.54, bright ? 0.77 : 0.65, bright ? 0.5 : 0.8);
    this.sun.intensity = day ? 0.24 : dawn ? 0.35 : memory ? 0.25 : 0.16;
    if (g.atmosphere) {
      g.atmosphere.baseExposure = day ? 0.95 : bright ? 1.1 : NIGHT_LOOK.baseExposure;
      g.atmosphere.maxExposure = day ? 1.35 : bright ? 1.8 : NIGHT_LOOK.maxExposure;
      g.atmosphere.nightSightIntensity = bright ? 0 : NIGHT_LOOK.nightSightIntensity;
      g.atmosphere.nightSight.range = NIGHT_LOOK.nightSightRange;
      g.atmosphere.mood.memory = memory;
    }
    const density = day ? 0.018 : dawn ? 0.012 : 0.02;
    const ambient = day
      ? [0.045, 0.057, 0.06]
      : bright
        ? [0.09, 0.11, 0.12]
        : [0.007, 0.012, 0.015];
    if (g.pipeline?.fog) {
      const near = this.flames.filter((light) =>
        day
          ? /lok_lamp|market_/.test(light.name)
          : stage === "purification"
            ? /ritual_key|deck/.test(light.name)
            : /entry|ward|attic|vault/.test(light.name),
      );
      g.pipeline.fog.lights.splice(0, g.pipeline.fog.lights.length, this.lamp, ...near.slice(0, 4));
      g.pipeline.fog.density = density;
      g.pipeline.fog.maxDistance = day ? 90 : dawn ? 160 : 55;
      g.pipeline.fog.ambient.set(ambient[0], ambient[1], ambient[2]);
      g.pipeline.fog.setMistPockets([
        { x: 0, z: -4, radiusX: 20, radiusZ: 25, baseY: 0.05, height: 0.7, density: 0.3 },
        { x: -64, z: -4, radiusX: 36, radiusZ: 36, baseY: -0.1, height: 0.5, density: 0.055 },
      ]);
    } else {
      g.scene.fogDensity = density;
      g.scene.fogColor.set(ambient[0], ambient[1], ambient[2]);
    }
  }
  update(dt: number, flame: number): void {
    this.time += dt;
    for (const wind of this.foliage) wind.seconds = this.time;
    this.visibleFlames.forEach((flame, i) => {
      flame.scaling.y = 0.9 + 0.1 * Math.sin(this.time * 17 + i * 2.7);
    });
    const g = this.game,
      storm = !["market", "memory", "dawn", "complete"].includes(this.stage);
    const flash = storm ? this.lightning.update(dt) : 0;
    this.flash.intensity = flash * 2;
    this.clouds.update(flash, g.atmosphere?.eye.exposure ?? 1.45, dt);
    this.rain.update(storm || this.stage === "market", this.stage === "market", flash, flame);
    this.shade +=
      (Math.max(0.5, Math.min(1, (g.interaction.distance / 1.3) ** 2)) - this.shade) *
      Math.min(1, dt * 5);
    this.lamp.intensity = (22 / (16 * softFalloff(4, 11.5))) * flame * this.shade;
    this.heldFill.intensity = flame * 0.045;
    for (const [i, l] of this.flames.entries())
      l.intensity = 4 * (0.94 + 0.06 * Math.sin(this.time * 8 + i));
    this.ritualCandles.forEach((light, i) => {
      light.intensity = g.flags.get(`ep3.candle.${i}`, false)
        ? 0.24 * (0.9 + 0.1 * Math.sin(this.time * 9.7 + i * 3))
        : 0;
    });
    g.atmosphere?.update(
      dt,
      this.stage === "market" || this.stage === "dawn" || this.stage === "complete"
        ? 1
        : flame * 0.43 + 0.05,
    );
  }
}
