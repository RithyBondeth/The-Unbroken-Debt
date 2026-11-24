import type { Scene } from "@babylonjs/core/scene";
import type { Camera } from "@babylonjs/core/Cameras/camera";
import { DirectionalLight } from "@babylonjs/core/Lights/directionalLight";
import { HemisphericLight } from "@babylonjs/core/Lights/hemisphericLight";
import { PointLight } from "@babylonjs/core/Lights/pointLight";
import { ClusteredLightContainer } from "@babylonjs/core/Lights/Clustered/clusteredLightContainer";
import type { Draught } from "../data/draught";
import { Color3, Color4 } from "@babylonjs/core/Maths/math.color";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import type { Area } from "@/core/areaLoader";
import { FLAME_COLOR, limitLightToRange } from "@/render/renderSetup";
import { softFalloff, useSoftFalloff } from "@/render/softLampFalloff";
import { applyRainWetness } from "@/render/surfaceDetail";
import { FARM_STORM_GAP, Lightning } from "@/render/weather/Lightning";
import { DAWN_LOOK } from "@/render/nightLook";
import { VILLAGE_NIGHT } from "../data/villageLook";

/**
 * The village at night (Art Bible, section 3): a dark, rain-heavy sky; the
 * funeral tent glowing from its hanging oil lamps and altar candles; lightning;
 * and Sora's hurricane lamp, the hero light, carried at her side.
 */
/** Working light calibrated at 4 m, with a soft core to protect nearby skin and paper. */
const PHYSICAL_INTENSITY = 22;
const LAMP_RANGE = 11.5;
/**
 * With the soft falloff (render/softLampFalloff.ts), the same light at Sora's
 * working distance, 4 m. The extended pool exposes the trail ahead while the
 * soft core and inspection shade protect what she holds up close.
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

/**
 * The game's light intensity for one watt of a preview's Cycles point light, calibrated
 * by eye adaptation against the approved funeral_wide preview (Nov 22, 2026): at this
 * strength its candle pools, mats and ceiling measure within a few levels of the
 * preview's. Sora's lamp is the game's own hero light and stays as tuned.
 */
export const WATT = 0.4;
/** The funeral's lights: the old tent's and altar's, and those under the house (fu_). */
export const FUNERAL_LIGHT = /^(tent|altar|coffin|fu_)/;
/** Of a practical light's strength, the share the rain mist scatters back as its halo. */
export const FOG_SCATTER = 0.3;
/** Flames given a halo in the fog besides Sora's lamp (VolumetricFog's five lights). */
const FOG_FLAMES = 4;
/** Lights of a kind (candle by candle) are merged no further apart than this (m): never through a wall. */
const MERGE_REACH = 2.0;

function flameColour(extra: unknown): Color3 {
  if (Array.isArray(extra) && extra.length === 3 && extra.every((c) => Number.isFinite(Number(c))))
    return new Color3(Number(extra[0]), Number(extra[1]), Number(extra[2]));
  return FLAME_COLOR.clone();
}

/**
 * Merges the nearest lights of a kind (fu_candle_012 into fu_candle_013, never a candle
 * into the bulb) until `budget` remain or none of a kind stand within MERGE_REACH: the
 * merged light sits at their strength-weighted middle with their summed strength.
 */
export function mergeLights(lights: readonly PointLight[], budget: number): PointLight[] {
  const live = [...lights];
  const kind = (light: PointLight) => light.name.replace(/_\d+$/, "");
  const strength = (light: PointLight) => (light.metadata as { base: number }).base;
  while (live.length > budget) {
    let bi = -1,
      bj = -1,
      best = MERGE_REACH;
    for (let i = 0; i < live.length; i++)
      for (let j = i + 1; j < live.length; j++) {
        if (kind(live[i]) !== kind(live[j])) continue;
        const d = Vector3.Distance(live[i].position, live[j].position);
        if (d < best) [bi, bj, best] = [i, j, d];
      }
    if (bi < 0) break;
    const a = live[bi],
      b = live[bj];
    const wa = strength(a),
      wb = strength(b),
      w = wa + wb;
    a.position = a.position.scale(wa / w).addInPlace(b.position.scale(wb / w));
    a.diffuse = a.diffuse.scale(wa / w).add(b.diffuse.scale(wb / w));
    a.range = Math.min(12, Math.max(a.range, b.range) + best / 2);
    a.intensity = w;
    a.metadata = { ...(a.metadata as object), base: w };
    b.dispose();
    live.splice(bj, 1);
  }
  return live;
}

export class VillageLights {
  /** A2-01 snuffs the hanging lamps independently of incense dimming. */
  hangingLevel = 1;
  /** Story-authored practical lamp levels, independent of wick flicker and incense. */
  readonly practicalLevels = new Map<string, number>();
  readonly flames: PointLight[] = [];
  readonly lamp: PointLight;
  readonly storm = new Lightning(Math.random, FARM_STORM_GAP);
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

  /** The previews' practical lights, merged to the preset's budget, in one clustered container. */
  readonly clustered: PointLight[] = [];
  private readonly practicals: ClusteredLightContainer | null;
  /** The volumetric fog's light list, refilled each frame with the lamp and the flames that matter most to Sora. */
  fogLights: PointLight[] | null = null;
  private readonly camera: Camera;

  /** `budget`: how many clustered lights the quality preset allows (QualityPreset.clusteredLights). */
  constructor(scene: Scene, area: Area, camera: Camera, budget = 32) {
    this.camera = camera;
    // Rain-heavy sky with the moon somewhere behind the clouds: near black, the
    // storm dome and fog just light enough that roofs, palms and the flag read as
    // silhouettes (Art Bible 1, 3).
    scene.clearColor = new Color4(...VILLAGE_NIGHT.clearColor, 1);
    this.sky = new HemisphericLight("night_sky", new Vector3(0.2, 1, -0.3), scene);
    this.sky.diffuse = new Color3(0.48, 0.56, 0.72);
    this.sky.groundColor = new Color3(0.13, 0.16, 0.2);
    this.sky.specular = new Color3(0.03, 0.04, 0.06);
    // Soft cloud bounce exposes leaf veins and bark between pools of lamplight.
    this.sky.intensity = VILLAGE_NIGHT.skyIntensity;
    // The moon hides low in the south, over the flooded fields: their water catches it.
    this.moon = new DirectionalLight("moonlight", new Vector3(-0.25, -0.45, -0.85), scene);
    // Cool and weak through the cloud: the forest reads only as dim shapes in blue.
    this.moon.diffuse = Color3.FromHexString("#7F9FD6");
    this.moon.specular = new Color3(0.1, 0.13, 0.18);
    this.moon.intensity = VILLAGE_NIGHT.moonIntensity;

    this.flash = new DirectionalLight("lightning", new Vector3(0.4, -1, 0.5), scene);
    this.flash.diffuse = new Color3(0.75, 0.82, 1);
    this.flash.intensity = 0;

    // Include authored runtime props at their actual world positions.
    for (const mesh of scene.meshes) mesh.computeWorldMatrix(true);
    // The approved previews' lights (Nov 22, 2026) carry their Cycles strength in watts
    // (tools/areas/rebuild-farmstead.py): they all go into one clustered container, which
    // takes a single light slot in every material however many candles burn. The older
    // markers keep their own intensity and a light of their own.
    const practicals: PointLight[] = [];
    for (const [id, marker] of area.level.flames) {
      const watts = Number(marker.extras.watts) || 0;
      const light = new PointLight(id, marker.position.clone(), scene);
      light.diffuse = flameColour(marker.extras.color);
      light.range = Number(marker.extras.radius) || 4;
      light.intensity = watts > 0 ? watts * WATT : Number(marker.extras.intensity) || 2;
      light.metadata = { base: light.intensity, fogScatter: watts > 0 ? FOG_SCATTER : 1 };
      if (watts > 0) {
        practicals.push(light);
        continue;
      }
      // Each flame lights only what it reaches, so a mesh's light slots go to the
      // flames near it rather than the first ones in the list.
      limitLightToRange(light, scene.meshes);
      this.flames.push(light);
    }
    this.clustered.push(...mergeLights(practicals, Math.max(4, budget)));
    this.flames.push(...this.clustered);
    for (let i = 0; i < this.flames.length; i++) this.phases.push(Math.random() * 10);
    this.practicals = this.clustered.length
      ? new ClusteredLightContainer("village_practicals", this.clustered, scene)
      : null;
    if (this.practicals) {
      this.practicals.maxRange = 12;
      // After the lamp, the lightning, the moon and the sky: always given a slot.
      this.practicals.renderPriority = 2;
    }

    // Sora's hurricane lamp; the vigil places it just below her eyes. It casts no
    // shadows: from (nearly) the eye, what she can see the lamp lights, and a shadow
    // map turning with her head only made shadows swim over bark and leaves.
    this.lamp = new PointLight("hurricane_lamp", new Vector3(-0.06, -0.14, 0.1), scene);
    this.lamp.range = LAMP_RANGE;
    useSoftFalloff(this.lamp);
    this.lamp.parent = camera;
    // The glass globe is warm white. Saturated orange lost the green channel
    // needed to see living foliage, especially after the episode's warm grade.
    this.lamp.diffuse = Color3.FromHexString("#FFD4A0");
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
        applyRainWetness(material);
      }
  }

  /**
   * 0-1: how far Sora is inside the funeral room. The sky's and the moon's cool fill
   * reach in through no roof in this light model; indoors they fall back and the
   * candles carry the room (ActOne.candlelitSight, Nov 20, 2026).
   */
  indoors = 0;
  private atDawn = false;

  dawn(): void {
    this.atDawn = true;
    this.sky.intensity = DAWN_LOOK.skyIntensity;
    this.sky.diffuse.set(0.65, 0.72, 0.8);
    this.moon.intensity = DAWN_LOOK.moonIntensity;
    this.moon.diffuse.set(0.7, 0.76, 0.84);
    this.flash.intensity = 0;
  }

  get flashing(): boolean {
    return this.storm.flashing;
  }

  /** The air Sora stirs (data/draught.ts): a candle she sweeps past gutters and dims. */
  draught: Draught | null = null;
  private readonly gusts: number[] = [];

  update(dt: number): void {
    this.time += dt;
    const t = this.time;
    const draught = this.draught;
    // Flames are never steady (Art Bible); each one out of step with the others. The
    // funeral's (under the house now: fu_) dim as the corner incense burns down and go
    // out in A2-01's gust, but for the fire pot, which sinks to its embers. The bulb
    // holds steady but for a stutter in the wire.
    this.flames.forEach((light, i) => {
      const p = this.phases[i];
      const base = (light.metadata as { base: number }).base;
      const funeral = FUNERAL_LIGHT.test(light.name);
      const hanging = !funeral
        ? 1
        : light.name === "fu_fire"
          ? 0.3 + 0.7 * this.hangingLevel
          : this.hangingLevel;
      let flicker =
        light.name === "fu_bulb"
          ? 0.97 + 0.03 * Math.sin(t * 50 + p) * (Math.sin(t * 0.7 + p) > 0.97 ? 8 : 0)
          : 0.88 + 0.07 * Math.sin(t * 8.3 + p) + 0.05 * Math.sin(t * 15.1 + p * 2);
      if (draught && light.name !== "fu_bulb" && light.name !== "fu_fire") {
        const at = light.position;
        const target = draught.at(at.x, at.y, at.z);
        const g0 = this.gusts[i] ?? 0;
        const g = g0 + (target - g0) * Math.min(1, dt * (target > g0 ? 9 : 1.6));
        this.gusts[i] = g;
        flicker *= 1 - g * (0.4 + 0.2 * Math.sin(t * 31 + p * 3));
      }
      light.intensity =
        base *
        (this.practicalLevels.get(light.name) ?? 1) *
        (funeral ? this.tentLevel : 1) *
        hanging *
        Math.max(0, flicker);
    });
    this.chooseFogLights();
    // Strong enough for a warm pool round Sora that the dark eats a few metres out.
    const shade = Math.max(SHADE_FLOOR, Math.min(1, (this.lookingAt / SHADE_FROM) ** 2));
    this.shade += (shade - this.shade) * Math.min(1, dt * 5);
    this.lamp.intensity =
      LAMP_INTENSITY *
      this.lampFlame *
      this.shade *
      (0.9 + 0.06 * Math.sin(t * 7.3) + 0.04 * Math.sin(t * 13.1));
    this.flash.intensity = this.storm.update(dt) * 3;
    if (!this.atDawn) {
      this.sky.intensity = VILLAGE_NIGHT.skyIntensity * (1 - 0.75 * this.indoors);
      this.moon.intensity = VILLAGE_NIGHT.moonIntensity * (1 - 0.8 * this.indoors);
    }
  }

  private readonly fogPick: PointLight[] = [];
  private readonly fogScore: number[] = [];

  /**
   * The volumetric fog lights five lights' halos: Sora's lamp and the four flames that
   * reach her eye most strongly (a strong light far off beats a candle near by), so the
   * funeral's glow hangs in the rain between the stilts from the yard.
   */
  private chooseFogLights(): void {
    const fog = this.fogLights;
    if (!fog) return;
    const eye = this.camera.globalPosition;
    const pick = this.fogPick,
      score = this.fogScore;
    pick.length = 0;
    score.length = 0;
    for (const light of this.flames) {
      if (light.intensity < 0.02) continue;
      const s = light.intensity / Math.max(4, Vector3.DistanceSquared(eye, light.position));
      let at = pick.length;
      while (at > 0 && score[at - 1] < s) at--;
      if (at >= FOG_FLAMES) continue;
      pick.splice(at, 0, light);
      score.splice(at, 0, s);
      if (pick.length > FOG_FLAMES) {
        pick.length = FOG_FLAMES;
        score.length = FOG_FLAMES;
      }
    }
    fog.length = 0;
    fog.push(this.lamp, ...pick);
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
