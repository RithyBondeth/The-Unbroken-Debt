import type { Scene } from "@babylonjs/core/scene";
import type { Camera } from "@babylonjs/core/Cameras/camera";
import { DirectionalLight } from "@babylonjs/core/Lights/directionalLight";
import { HemisphericLight } from "@babylonjs/core/Lights/hemisphericLight";
import { PointLight } from "@babylonjs/core/Lights/pointLight";
import { Color3, Color4 } from "@babylonjs/core/Maths/math.color";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import type { Area } from "../../../core/AreaLoader";
import { FLAME_COLOR, limitLightToRange } from "../../../render/RenderSetup";
import { softFalloff, useSoftFalloff } from "../../../render/softLampFalloff";
import { Lightning } from "../Lightning";

/**
 * The village at night (Art Bible, section 3): a dark, rain-heavy sky; the
 * funeral tent glowing from its hanging oil lamps and altar candles; lightning;
 * and Sora's hurricane lamp, the hero light, carried at her side.
 */
/** Sora's lamp at full flame, as it was with plain physical falloff (this much at 1 m). */
const PHYSICAL_INTENSITY = 10;
const LAMP_RANGE = 9;
/**
 * With the soft falloff (render/softLampFalloff.ts), the same light at Sora's
 * working distance, 4 m: everything from about 3 m out is lit as before, and
 * what she holds up close no longer burns to white.
 */
const LAMP_INTENSITY = PHYSICAL_INTENSITY / (16 * softFalloff(4, LAMP_RANGE));
/**
 * Close to what she looks at, Sora's lamp is shaded down a little more, as she
 * would lower it: full beyond this distance (m), and never below the floor. The
 * soft falloff already keeps what she holds from burning out; this keeps an object
 * she inspects at 1 m as bright as it was, and one at 0.5 m from glaring.
 */
const SHADE_FROM = 1.3;
const SHADE_FLOOR = 0.5;

export class VillageLights {
  /** A2-01 snuffs the hanging lamps independently of incense dimming. */
  hangingLevel = 1;
  /** Story-authored practical lamp levels, independent of wick flicker and incense. */
  readonly practicalLevels = new Map<string, number>();
  readonly flames: PointLight[] = [];
  readonly lamp: PointLight;
  readonly storm = new Lightning();
  /** Sora's lamp flame, 0 (out) to 1 (full), from the vigil's Lamp. */
  lampFlame = 0;
  /** The pavilion's lamps and candles, dimmed as the incense dies (A1-10). */
  tentLevel = 1;
  /** Distance to what Sora is looking at (m), for shading the lamp up close. */
  lookingAt = Infinity;
  private shade = 1;
  private readonly sky: HemisphericLight;
  private readonly moon: DirectionalLight;
  private readonly flash: DirectionalLight;
  private time = 0;
  private readonly phases: number[] = [];

  constructor(scene: Scene, area: Area, camera: Camera) {
    // Rain-heavy sky with the moon somewhere behind the clouds: dark slate, light
    // enough that roofs, palms and the flag read as silhouettes (Art Bible 1, 3).
    scene.clearColor = new Color4(0.02, 0.024, 0.032, 1);
    this.sky = new HemisphericLight("night_sky", new Vector3(0.2, 1, -0.3), scene);
    this.sky.diffuse = new Color3(0.48, 0.56, 0.72);
    this.sky.groundColor = new Color3(0.13, 0.16, 0.2);
    this.sky.specular = new Color3(0.03, 0.04, 0.06);
    // Soft cloud bounce exposes leaf veins and bark between pools of lamplight.
    this.sky.intensity = 0.38;
    // The moon hides low in the south, over the flooded fields: their water catches it.
    this.moon = new DirectionalLight("moonlight", new Vector3(-0.25, -0.45, -0.85), scene);
    // Cool and weak through the cloud: enough for the forest to read as shapes in blue.
    this.moon.diffuse = Color3.FromHexString("#7F9FD6");
    this.moon.specular = new Color3(0.1, 0.13, 0.18);
    this.moon.intensity = 0.38;

    this.flash = new DirectionalLight("lightning", new Vector3(0.4, -1, 0.5), scene);
    this.flash.diffuse = new Color3(0.75, 0.82, 1);
    this.flash.intensity = 0;

    // Include authored runtime props at their actual world positions.
    for (const mesh of scene.meshes) mesh.computeWorldMatrix(true);
    for (const [id, marker] of area.level.flames) {
      const light = new PointLight(id, marker.position.clone(), scene);
      light.diffuse = FLAME_COLOR.clone();
      light.range = Number(marker.extras.radius) || 4;
      light.intensity = Number(marker.extras.intensity) || 2;
      light.metadata = { base: light.intensity };
      // Each flame lights only what it reaches, so a mesh's light slots go to the
      // flames near it rather than the first ones in the list.
      limitLightToRange(light, scene.meshes);
      this.flames.push(light);
      this.phases.push(Math.random() * 10);
    }

    // Sora's hurricane lamp; the vigil places it just below her eyes. It casts no
    // shadows: from (nearly) the eye, what she can see the lamp lights, and a shadow
    // map turning with her head only made shadows swim over bark and leaves.
    this.lamp = new PointLight("hurricane_lamp", new Vector3(-0.06, -0.14, 0.1), scene);
    this.lamp.range = LAMP_RANGE;
    useSoftFalloff(this.lamp);
    this.lamp.parent = camera;
    this.lamp.diffuse = FLAME_COLOR.clone();
    this.lamp.intensity = 6;

    // Materials take 4 lights by default. Sora's lamp always comes first, then the
    // lightning, the moon, the sky and night sight, leaving three for the flames
    // in reach of each mesh.
    this.lamp.renderPriority = 10;
    this.flash.renderPriority = 5;
    this.moon.renderPriority = 4;
    this.sky.renderPriority = 3;
    // Babylon sorts lights that may cast shadows ahead of the others whatever their
    // priority; none of these has a shadow map, so none claims to.
    for (const light of [this.lamp, this.flash, this.moon, this.sky, ...this.flames])
      light.shadowEnabled = false;
    scene.requireLightSorting = true;
    for (const material of scene.materials)
      if (material instanceof PBRMaterial) {
        material.maxSimultaneousLights = 8;
        // Rain-soaked outdoor surfaces (named M_wet_ in Blender): darker and a little
        // glossier (Art Bible 6, wetness). The factor scales each texture's own
        // roughness: much lower and the moon, low behind the clouds, turns mud and
        // bark to crumpled foil.
        if (material.name.startsWith("M_wet_")) {
          material.albedoColor.scaleInPlace(0.86);
          material.roughness = 0.92;
        }
      }
  }

  dawn(): void {
    this.sky.intensity = 0.65;
    this.sky.diffuse.set(0.65, 0.72, 0.8);
    this.moon.intensity = 0.4;
    this.moon.diffuse.set(0.7, 0.76, 0.84);
    this.flash.intensity = 0;
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
      const tent = /^(tent|altar|coffin)/.test(light.name) ? this.tentLevel : 1;
      light.intensity =
        base *
        (this.practicalLevels.get(light.name) ?? 1) *
        tent *
        (/^(tent|altar|coffin)/.test(light.name) ? this.hangingLevel : 1) *
        (0.88 + 0.07 * Math.sin(t * 8.3 + p) + 0.05 * Math.sin(t * 15.1 + p * 2));
    });
    // Strong enough for a warm pool round Sora that the dark eats a few metres out.
    const shade = Math.max(SHADE_FLOOR, Math.min(1, (this.lookingAt / SHADE_FROM) ** 2));
    this.shade += (shade - this.shade) * Math.min(1, dt * 5);
    this.lamp.intensity =
      LAMP_INTENSITY *
      this.lampFlame *
      this.shade *
      (0.9 + 0.06 * Math.sin(t * 7.3) + 0.04 * Math.sin(t * 13.1));
    this.flash.intensity = this.storm.update(dt) * 3;
  }

  /** Light reaching Sora's eyes, for eye adaptation (1 = her lamp at arm's length). */
  lightAtEye(eye: Vector3): number {
    // Calibrated when the lamp was 6: the eye's response to it stays the same. The
    // flame, not the shaded light: shading the lamp must not open the eyes wider.
    let light = this.lampFlame * (6 / 14);
    for (const l of this.flames) {
      const d = Math.max(0.5, Vector3.Distance(eye, l.position));
      light += l.intensity / (d * d) / 14;
    }
    return light + this.storm.level * 0.3;
  }
}
