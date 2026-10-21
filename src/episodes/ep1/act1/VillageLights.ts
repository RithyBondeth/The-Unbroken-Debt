import type { Scene } from "@babylonjs/core/scene";
import type { Camera } from "@babylonjs/core/Cameras/camera";
import { DirectionalLight } from "@babylonjs/core/Lights/directionalLight";
import { HemisphericLight } from "@babylonjs/core/Lights/hemisphericLight";
import { PointLight } from "@babylonjs/core/Lights/pointLight";
import { Color3, Color4 } from "@babylonjs/core/Maths/math.color";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import type { Area } from "../../../core/AreaLoader";
import type { QualityPreset } from "../../../render/QualityPresets";
import {
  createShadowedPointLight,
  FLAME_COLOR,
  limitLightToRange,
} from "../../../render/RenderSetup";
import { Lightning } from "../Lightning";

/** Materials whose meshes never cast the lamp's shadow. */
const NO_SHADOW =
  /^M_(flame|ember|puddle|flood_water|cobweb|jasmine|rice|incense|white_thread|rope|muddy_footprints|lotus_bud|stem_green|hearth_embers|lamp_window)/;

/**
 * The village at night (Art Bible, section 3): a dark, rain-heavy sky; the
 * funeral tent glowing from its hanging oil lamps and altar candles; lightning;
 * and Sora's hurricane lamp, the hero light, carried at her side.
 */
export class VillageLights {
  readonly flames: PointLight[] = [];
  readonly lamp: PointLight;
  readonly storm = new Lightning();
  private readonly sky: HemisphericLight;
  private readonly moon: DirectionalLight;
  private readonly flash: DirectionalLight;
  private time = 0;
  private readonly phases: number[] = [];

  constructor(scene: Scene, area: Area, preset: QualityPreset, camera: Camera) {
    // Rain-heavy sky with the moon somewhere behind the clouds: dark slate, light
    // enough that roofs, palms and the flag read as silhouettes (Art Bible 1, 3).
    scene.clearColor = new Color4(0.02, 0.024, 0.032, 1);
    this.sky = new HemisphericLight("night_sky", new Vector3(0.2, 1, -0.3), scene);
    this.sky.diffuse = new Color3(0.36, 0.42, 0.56);
    this.sky.groundColor = new Color3(0.03, 0.03, 0.025);
    this.sky.specular = new Color3(0.05, 0.06, 0.08);
    this.sky.intensity = 0.09;
    // The moon hides low in the south, over the flooded fields: their water catches it.
    this.moon = new DirectionalLight("moonlight", new Vector3(-0.25, -0.45, -0.85), scene);
    this.moon.diffuse = Color3.FromHexString("#8FA8D8");
    this.moon.specular = new Color3(0.25, 0.3, 0.4);
    this.moon.intensity = 0.1;

    this.flash = new DirectionalLight("lightning", new Vector3(0.4, -1, 0.5), scene);
    this.flash.diffuse = new Color3(0.75, 0.82, 1);
    this.flash.intensity = 0;

    for (const [id, marker] of area.level.flames) {
      const light = new PointLight(id, marker.position.clone(), scene);
      light.diffuse = FLAME_COLOR.clone();
      light.range = Number(marker.extras.radius) || 4;
      light.intensity = Number(marker.extras.intensity) || 2;
      light.metadata = { base: light.intensity };
      // Each flame lights only what it reaches, so a mesh's light slots go to the
      // flames near it rather than the first ones in the list.
      limitLightToRange(light, area.container.meshes);
      this.flames.push(light);
      this.phases.push(Math.random() * 10);
    }

    // Sora's hurricane lamp, lit (Phase 2 stand-in: the oil and matches come next).
    const lamp = createShadowedPointLight(
      scene,
      "hurricane_lamp",
      new Vector3(0.28, -0.35, 0.25),
      9,
      preset.lampShadowMapSize,
      // Not the sky, the ground or the flood (they only receive the lamp's shadows),
      // nor flames, threads, petals and decals too fine to cast one worth drawing.
      (m) =>
        m.isVisible &&
        m.renderingGroupId === 0 &&
        !m.infiniteDistance &&
        !NO_SHADOW.test(m.material?.name ?? "") &&
        m.getBoundingInfo().boundingSphere.radiusWorld > 0.12 &&
        m.getBoundingInfo().boundingSphere.radiusWorld < 30,
    );
    this.lamp = lamp.light;
    this.lamp.parent = camera;
    this.lamp.diffuse = FLAME_COLOR.clone();
    this.lamp.intensity = 6;

    // Materials take 4 lights by default. Sora's lamp always comes first, then the
    // lightning, the moon, the sky and night sight, leaving three for the flames
    // in reach of each mesh.
    this.lamp.renderPriority = 10;
    this.flash.renderPriority = 5;
    this.moon.renderPriority = 4;
    scene.requireLightSorting = true;
    for (const material of scene.materials)
      if (material instanceof PBRMaterial) {
        material.maxSimultaneousLights = 8;
        // Rain-soaked outdoor surfaces (named M_wet_ in Blender): darker and glossier
        // (Art Bible 6, wetness), so lamp light glints on mud, thatch and tiles.
        if (material.name.startsWith("M_wet_")) {
          material.albedoColor.scaleInPlace(0.72);
          material.roughness = 0.55;
        }
      }
  }

  get flashing(): boolean {
    return this.storm.flashing;
  }

  update(dt: number): void {
    this.time += dt;
    const t = this.time;
    // Flames are never steady (Art Bible); each one out of step with the others.
    this.flames.forEach((light, i) => {
      const p = this.phases[i];
      const base = (light.metadata as { base: number }).base;
      light.intensity =
        base * (0.88 + 0.07 * Math.sin(t * 8.3 + p) + 0.05 * Math.sin(t * 15.1 + p * 2));
    });
    this.lamp.intensity = 6 * (0.9 + 0.06 * Math.sin(t * 7.3) + 0.04 * Math.sin(t * 13.1));
    this.flash.intensity = this.storm.update(dt) * 3;
  }

  /** Light reaching Sora's eyes, for eye adaptation (1 = her lamp at arm's length). */
  lightAtEye(eye: Vector3): number {
    let light = this.lamp.intensity / 14;
    for (const l of this.flames) {
      const d = Math.max(0.5, Vector3.Distance(eye, l.position));
      light += l.intensity / (d * d) / 14;
    }
    return light + this.storm.level * 0.3;
  }
}
