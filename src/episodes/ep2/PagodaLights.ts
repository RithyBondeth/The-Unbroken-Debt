import { ShadowGenerator } from "@babylonjs/core/Lights/Shadows/shadowGenerator";
import { CreateSphere } from "@babylonjs/core/Meshes/Builders/sphereBuilder";
import { StandardMaterial } from "@babylonjs/core/Materials/standardMaterial";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { HemisphericLight } from "@babylonjs/core/Lights/hemisphericLight";
import { DirectionalLight } from "@babylonjs/core/Lights/directionalLight";
import { PointLight } from "@babylonjs/core/Lights/pointLight";
import { Color3, Color4 } from "@babylonjs/core/Maths/math.color";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import type { Game } from "../../core/Game";
import type { Area } from "../../core/AreaLoader";
import { FLAME_COLOR, limitLightToRange } from "../../render/RenderSetup";
import { softFalloff, useSoftFalloff } from "../../render/softLampFalloff";
import { applyFoliageWind, type FoliageWind } from "../../render/FoliageWind";
import { NIGHT_LOOK, DAWN_LOOK } from "../ep1/data/nightLook";
import { LowGroundMist } from "../../render/LowGroundMist";
import type { MistPocket } from "../../render/mist";

const POND_MIST: MistPocket[] = [
  { x: -8, z: -25, radiusX: 9, radiusZ: 12, baseY: 0.04, height: 1, density: 0.5 },
  { x: 8, z: -25, radiusX: 9, radiusZ: 12, baseY: 0.04, height: 1, density: 0.5 },
  { x: -8, z: 0, radiusX: 6, radiusZ: 10, baseY: 0.02, height: 0.55, density: 0.2 },
];
/** Episode 1's calibrated lamp, surfaces, grade and fog, under a clearer moon. */
export class PagodaLights {
  readonly lamp: PointLight;
  readonly flames: PointLight[] = [];
  readonly sky: HemisphericLight;
  readonly moon: DirectionalLight;
  private readonly wind: FoliageWind[] = [];
  /** 0–1 while an apparition is close: the lamp gutters. */
  scare = 0;
  private mist: LowGroundMist | null = null;
  private time = 0;
  private shade = 1;
  private daytime = false;
  constructor(
    private readonly game: Game,
    area: Area,
  ) {
    const scene = game.scene;
    scene.clearColor = new Color4(...NIGHT_LOOK.clearColor, 1);
    this.sky = new HemisphericLight("pagoda_sky", new Vector3(0.2, 1, -0.3), scene);
    this.sky.diffuse = new Color3(0.48, 0.56, 0.72);
    this.sky.groundColor = new Color3(0.13, 0.16, 0.2);
    this.sky.specular = new Color3(0.03, 0.04, 0.06);
    this.sky.intensity = NIGHT_LOOK.skyIntensity;
    this.moon = new DirectionalLight("pagoda_moon", new Vector3(-0.3, -0.7, 0.5), scene);
    this.moon.diffuse = Color3.FromHexString("#7F9FD6");
    this.moon.intensity = 0.28;
    this.lamp = new PointLight("player_lamp", new Vector3(-0.06, -0.14, 0.1), scene);
    this.lamp.parent = game.camera;
    this.lamp.diffuse = Color3.FromHexString("#FFD4A0");
    this.lamp.range = 11.5;
    useSoftFalloff(this.lamp);
    this.lamp.intensity = 0;
    for (const mesh of scene.meshes) mesh.computeWorldMatrix(true);
    for (const [id, marker] of area.level.flames) {
      const light = new PointLight("pagoda_" + id, marker.position.clone(), scene);
      light.diffuse = FLAME_COLOR.clone();
      light.range = Number(marker.extras.radius) || 5;
      light.intensity = Number(marker.extras.intensity) || 2.6;
      light.metadata = { base: light.intensity };
      limitLightToRange(light, scene.meshes);
      this.flames.push(light);
    }
    this.lamp.renderPriority = 10;
    this.moon.renderPriority = 4;
    this.sky.renderPriority = 3;
    scene.requireLightSorting = true;
    for (const light of [this.lamp, this.moon, this.sky, ...this.flames])
      light.shadowEnabled = false;
    const moonDisc = CreateSphere("pagoda_moon_disc", { diameter: 2.4, segments: 20 }, scene);
    moonDisc.position.set(-24, 38, -40);
    moonDisc.isPickable = false;
    moonDisc.applyFog = false;
    const moonSurface = new StandardMaterial("pagoda_moon_surface", scene);
    moonSurface.disableLighting = true;
    moonSurface.emissiveColor.set(0.5, 0.56, 0.64);
    moonDisc.material = moonSurface;
    if (game.preset.name !== "low") {
      this.moon.position.set(15, 32, -20);
      this.moon.orthoLeft = -42;
      this.moon.orthoRight = 42;
      this.moon.orthoTop = 44;
      this.moon.orthoBottom = -44;
      this.moon.shadowMinZ = 1;
      this.moon.shadowMaxZ = 110;
      this.moon.shadowEnabled = true;
      const shadows = new ShadowGenerator(game.preset.name === "medium" ? 1024 : 2048, this.moon);
      shadows.usePercentageCloserFiltering = true;
      shadows.bias = 0.0005;
      shadows.normalBias = 0.025;
      for (const mesh of area.container.meshes) {
        mesh.receiveShadows = true;
        if (
          mesh instanceof Mesh &&
          /M_ep2_(stone|moss|teak|boards|plaster|chalk|soot|ochre|red|carved|column|tiles|bark|gate_)|M_forest_leaf/.test(
            mesh.material?.name ?? "",
          )
        )
          shadows.addShadowCaster(mesh);
      }
      // The moon and architecture are static; render their shadows once after textures compile.
      let readyFrames = 0;
      const freeze = scene.onAfterRenderObservable.add(() => {
        if (!scene.isReady()) return;
        if (++readyFrames < 3) return;
        const map = shadows.getShadowMap();
        if (map) {
          map.refreshRate = 0;
          map.resetRefreshCounter();
        }
        freeze.remove();
      });
      scene.onDisposeObservable.addOnce(() => shadows.dispose());
    }
    for (const mat of area.container.materials)
      if (mat instanceof PBRMaterial) mat.maxSimultaneousLights = 8;
    // Foliage bends to the game's shared wind, as in Episode 1's forest.
    this.wind.push(...applyFoliageWind(area.container.materials, game.wind));
  }
  begin(): void {
    const g = this.game;
    g.addFlameLights(this.lamp, ...this.flames.slice(0, 4));
    // A still, close night under the canopy: a light breeze in the crowns.
    g.wind.base = 0.3;
    g.wind.calm = 0;
    g.atmosphere.baseExposure = NIGHT_LOOK.baseExposure;
    g.atmosphere.maxExposure = NIGHT_LOOK.maxExposure;
    g.atmosphere.nightSightIntensity = NIGHT_LOOK.nightSightIntensity;
    g.atmosphere.nightSight.range = NIGHT_LOOK.nightSightRange;
    if (g.pipeline.fog) {
      g.pipeline.fog.density = 0.015;
      g.pipeline.fog.ambient.set(...NIGHT_LOOK.fogAmbient);
      g.pipeline.fog.setMistPockets(POND_MIST);
    } else {
      g.scene.fogDensity = 0.015;
      g.scene.fogColor.set(...NIGHT_LOOK.fogAmbient);
      this.mist = new LowGroundMist(g.scene, POND_MIST);
    }
  }
  update(dt: number, flame: number): void {
    this.time += dt;
    const shade = Math.max(0.5, Math.min(1, (this.game.interaction.distance / 1.3) ** 2));
    this.shade += (shade - this.shade) * Math.min(1, dt * 5);
    // An apparition makes the flame gutter and nearly die.
    const gutter = this.scare > 0 ? 1 - this.scare * (0.55 + 0.45 * Math.random()) : 1;
    this.lamp.intensity =
      (22 / (16 * softFalloff(4, 11.5))) *
      flame *
      gutter *
      this.shade *
      (0.9 + 0.06 * Math.sin(this.time * 7.3) + 0.04 * Math.sin(this.time * 13.1));
    for (const [i, l] of this.flames.entries())
      l.intensity =
        (l.metadata as { base: number }).base *
        (0.9 + 0.07 * Math.sin(this.time * 8.3 + i) + 0.03 * Math.sin(this.time * 15.1 + i * 2));
    this.game.atmosphere.update(dt, this.daytime ? 1 : flame * (6 / 14) + 0.05);
  }
  dawn(): void {
    this.daytime = true;
    this.sky.intensity = DAWN_LOOK.skyIntensity;
    this.sky.diffuse.set(0.78, 0.77, 0.69);
    this.moon.intensity = 0.35;
    this.moon.diffuse.set(1, 0.8, 0.58);
    const g = this.game;
    g.scene.clearColor.set(...DAWN_LOOK.clearColor, 1);
    g.atmosphere.baseExposure = DAWN_LOOK.baseExposure;
    g.atmosphere.maxExposure = DAWN_LOOK.maxExposure;
    g.atmosphere.nightSightIntensity = 0;
    if (g.pipeline.fog) {
      g.pipeline.fog.density = 0.01;
      g.pipeline.fog.ambient.set(...DAWN_LOOK.fogAmbient);
      g.pipeline.fog.mistStrength = 0.3;
    } else {
      g.scene.fogDensity = 0.01;
      g.scene.fogColor.set(...DAWN_LOOK.fogAmbient);
    }
    this.mist?.stop();
  }
}
