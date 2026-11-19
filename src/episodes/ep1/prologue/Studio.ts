import type { Scene } from "@babylonjs/core/scene";
import { HemisphericLight } from "@babylonjs/core/Lights/hemisphericLight";
import { Light } from "@babylonjs/core/Lights/light";
import { PointLight } from "@babylonjs/core/Lights/pointLight";
import { SpotLight } from "@babylonjs/core/Lights/spotLight";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { Texture } from "@babylonjs/core/Materials/Textures/texture";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { CreateSphere } from "@babylonjs/core/Meshes/Builders/sphereBuilder";
import type { Mesh } from "@babylonjs/core/Meshes/mesh";
import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import { VertexBuffer } from "@babylonjs/core/Buffers/buffer";
import { ShadowGenerator } from "@babylonjs/core/Lights/Shadows/shadowGenerator";
import { RenderTargetTexture } from "@babylonjs/core/Materials/Textures/renderTargetTexture";
import "@babylonjs/core/Lights/Shadows/shadowGeneratorSceneComponent";
import "@babylonjs/core/Materials/Textures/Loaders/ktxTextureLoader";
import type { QualityPreset } from "@/render/qualityPresets";
import { createShadowedPointLight, FLAME_COLOR } from "@/render/renderSetup";
import type { Area } from "@/core/areaLoader";
import { Lightning } from "@/render/weather/Lightning";
import { useSoftFalloff } from "@/render/softLampFalloff";
import { powerAt, POWER_RETURN } from "../data/powerCut";

/**
 * The lightmap stores light x this, RGBD-encoded (LIGHTMAP_GAIN in
 * tools/areas/bake_studio_lightmap.py); the shader decodes RGBD and scales back.
 */
export const STUDIO_LIGHTMAP_GAIN = 8;

/** Overall brightness of the baked light in the game, tuned against the runtime lights. */
const BAKED_EXPOSURE = 1.6;

/**
 * Loads the studio's baked lightmap: RGBD in a KTX2 tagged linear, so every GPU
 * returns the stored bytes and the shader decodes them. The Low preset reads the
 * half-size copy.
 */
export async function loadStudioLightmap(
  scene: Scene,
  preset: QualityPreset,
): Promise<Texture | null> {
  const file = preset.name === "low" ? "studio_lightmap_2k.ktx2" : "studio_lightmap.ktx2";
  const url = `${import.meta.env.BASE_URL}assets/ep1/${file}`;
  return new Promise((resolve) => {
    const texture: Texture = new Texture(url, scene, {
      noMipmap: false,
      invertY: false,
      samplingMode: Texture.TRILINEAR_SAMPLINGMODE,
    });
    texture.onLoadObservable.addOnce(() => resolve(texture));
    // A missing lightmap leaves the room lit by its runtime lights only, not black.
    setTimeout(() => {
      if (!texture.isReady()) {
        console.warn(`[Studio] lightmap ${file} did not load`);
        resolve(null);
      }
    }, 20000);
  });
}

/**
 * The studio's light (Beat Sheet 4.1, rebuilt November 2026 as a shophouse floor).
 *
 * Baked: the green banker's lamp (the key light), the writing sconce, the bulb
 * under the airwell roof, the oil lamp on the altar, the glow up the stairs and the
 * night sky, with soft shadows, bounce light and the room's grime, in one lightmap
 * on every `_LM` material. On those surfaces the lightmap is the diffuse light; the
 * desk lamp adds only its highlight on varnish, brass and tile (Babylon's
 * LIGHTMAP_SPECULAR mode), so nothing there is lit twice and no shadow map is drawn
 * for the lamp at all.
 *
 * Runtime: the same lamps light what is not baked (props, things that move or are
 * picked up), each only within its reach; the shelf candle, which goes out in P05,
 * and the lightning through the balcony doors, both with shadow maps drawn only
 * when something has changed.
 */
/** How much light is left while the lights are held down (lightsOut). */
const HELD_LIGHT = 0.3;

export class StudioLights {
  private readonly candlePower = 2.6;
  readonly deskLamp: PointLight;
  readonly candle: PointLight;
  readonly lightning: SpotLight;
  /** The writing sconce over the desk (runtime part, for the props on the desk). */
  readonly writingLight: PointLight;
  /** Lightmapped meshes. */
  readonly baked: AbstractMesh[] = [];
  private readonly airwellBulb: PointLight;
  /** Paraffin flames baked steady (the altar lamp, the tea-table lamp), flickered live. */
  private readonly flames: { light: PointLight; base: number; phase: number }[] = [];
  private readonly candleFlame: Mesh;
  /** Live flames other than the shelf candle's (the desk candle by the diary). */
  private readonly flameMeshes: Mesh[] = [];
  private readonly glass: PBRMaterial[] = [];
  private candleLit = true;
  /** Seconds since every light in the house went out (POWER_CUT), or null. */
  private cutAt: number | null = null;
  /** The lights are held out (lightsOut) until lightsBack. */
  private held = false;
  /** How much of the house's light is on (0–1): the power cut's level now. */
  power = 1;
  private readonly lightmap: Texture | null;
  private readonly lightmapLevel: number = 0;
  /** The electric lamps' runtime parts at full power: [light, intensity]. */
  private readonly lamps: [Light, number][] = [];
  /** Whatever glows in the house (bulbs, shades, flames): [material, colour at full]. */
  private readonly glows: [PBRMaterial, Color3][] = [];
  private readonly storm = new Lightning();
  private time = 0;
  private readonly flashShadows: ShadowGenerator;
  private readonly candleShadows: ShadowGenerator | null = null;

  constructor(scene: Scene, area: Area, preset: QualityPreset, lightmap: Texture | null) {
    const { markers, flames } = area.level;
    const at = (name: string, fallback: Vector3) => markers.get(name)?.position.clone() ?? fallback;

    // -------------------------------------------------- the lightmap
    const bakedMaterials = new Set<PBRMaterial>();
    // The asset build merges identical materials, so a `_LM` material can also be
    // worn by small props that were never baked (no lightmap UVs). They get a plain
    // copy, lit by the runtime lights like every other prop.
    const plainCopies = new Map<PBRMaterial, PBRMaterial>();
    for (const mesh of scene.meshes) {
      const mat = mesh.material;
      if (!(mat instanceof PBRMaterial) || !mat.name.endsWith("_LM")) continue;
      if (!mesh.isVerticesDataPresent(VertexBuffer.UV2Kind)) {
        let copy = plainCopies.get(mat);
        if (!copy) {
          copy = mat.clone(mat.name.replace(/_LM$/, ""));
          plainCopies.set(mat, copy);
        }
        mesh.material = copy;
        continue;
      }
      this.baked.push(mesh);
      bakedMaterials.add(mat);
    }
    this.lightmap = lightmap;
    if (lightmap) {
      lightmap.coordinatesIndex = 1;
      lightmap.level = BAKED_EXPOSURE / STUDIO_LIGHTMAP_GAIN;
      this.lightmapLevel = lightmap.level;
      // fromRGBD() linearises the colour itself, so the texture is not marked gamma.
      lightmap.gammaSpace = false;
      lightmap.isRGBD = true;
      lightmap.wrapU = lightmap.wrapV = Texture.CLAMP_ADDRESSMODE;
      for (const mat of bakedMaterials) {
        mat.lightmapTexture = lightmap;
        mat.useLightmapAsShadowmap = false;
      }
    }
    const bakedSet = new Set(this.baked);
    for (const material of scene.materials)
      if (material instanceof PBRMaterial) material.maxSimultaneousLights = 8;

    /**
     * What a runtime light leaves out: baked surfaces (its light is already in the
     * lightmap) unless `alsoBaked`, whatever is beyond its reach, and its own shade and
     * bulb (lit from a few centimetres they burn white). Meshes made later (the drawing
     * sheet, Sora's hands, what she carries) are not listed, so they are lit.
     */
    const exclude = (light: Light, p: Vector3, reach: number, alsoBaked = false) => {
      light.excludedMeshes = scene.meshes.filter((m) => {
        if (!alsoBaked && bakedSet.has(m)) return true;
        const s = m.getBoundingInfo().boundingSphere;
        const d = Vector3.Distance(s.centerWorld, p);
        return d >= reach + s.radiusWorld || (d < 0.25 && s.radiusWorld < 0.2);
      });
    };

    // -------------------------------------------------- runtime lights
    // Dim night sky for what is not baked, so props are never pure black.
    const sky = new HemisphericLight("night_sky", new Vector3(0, 1, -0.4), scene);
    sky.diffuse = new Color3(0.35, 0.42, 0.6);
    sky.groundColor = new Color3(0.04, 0.035, 0.03);
    sky.intensity = 0.1;
    sky.specular = new Color3(0.12, 0.15, 0.2);
    sky.excludedMeshes = [...this.baked];

    const lampAt = at("desk_lamp", new Vector3(-2.05, 1.16, -0.7));
    // An electric bulb under green glass: warmer than daylight, cooler than a flame.
    this.deskLamp = new PointLight("desk_lamp", lampAt, scene);
    this.deskLamp.diffuse = new Color3(1, 0.86, 0.62);
    this.deskLamp.intensity = 12;
    this.deskLamp.range = 7;
    this.deskLamp.shadowEnabled = false;
    useSoftFalloff(this.deskLamp);
    exclude(this.deskLamp, lampAt, 7);
    // On baked surfaces: the lightmap's diffuse plus this lamp's highlight. It reaches
    // every baked mesh (each must have exactly one such light) and outranks the rest.
    const highlight = new PointLight("desk_lamp_highlight", lampAt, scene);
    highlight.diffuse = new Color3(1, 0.86, 0.62);
    highlight.intensity = 0.6;
    highlight.range = 30;
    highlight.shadowEnabled = false;
    highlight.lightmapMode = Light.LIGHTMAP_SPECULAR;
    highlight.renderPriority = 10;
    if (this.baked.length) highlight.includedOnlyMeshes = [...this.baked];
    else highlight.setEnabled(false);

    const sconceAt = at("writing_sconce", new Vector3(-0.21, 1.55, -2.15));
    this.writingLight = new PointLight("writing_sconce", sconceAt, scene);
    this.writingLight.diffuse = new Color3(1, 0.81, 0.53);
    this.writingLight.range = 3.2;
    this.writingLight.intensity = 7;
    this.writingLight.shadowEnabled = false;
    exclude(this.writingLight, sconceAt, 3.2);

    const bulbAt = at("airwell_bulb", new Vector3(-1.95, 2.02, -8.0));
    this.airwellBulb = new PointLight("airwell_bulb", bulbAt, scene);
    this.airwellBulb.diffuse = new Color3(1, 0.78, 0.5);
    this.airwellBulb.range = 4.5;
    this.airwellBulb.intensity = 3;
    this.airwellBulb.shadowEnabled = false;
    exclude(this.airwellBulb, bulbAt, 4.5);

    // The oil lamps on the altar and the tea table: baked steady, flickered live.
    for (const [name, fallback, phase] of [
      ["altar_lamp", new Vector3(-1.53, 2.2, -13.83), 0],
      ["tea_lamp", new Vector3(-4.0, 0.75, -2.95), 2.1],
    ] as const) {
      const p = at(name, fallback);
      const light = new PointLight(name, p, scene);
      light.diffuse = FLAME_COLOR.clone();
      light.range = 3.5;
      light.intensity = 0.35;
      light.shadowEnabled = false;
      exclude(light, p, 3.5, true);
      this.flames.push({ light, base: 0.35, phase });
    }

    // The shelf candle on the partition: not baked, since it goes out (P05).
    const candleAt = flames.get("candle");
    const candlePosition = candleAt?.position.clone() ?? new Vector3(-3.38, 1.53, -5.84);
    const candleRange = Number(candleAt?.extras.radius) || 3;
    if (preset.shadowedFlames > 0) {
      // The books, the vase and the shelf edge throw shadows up the partition boards.
      const shadowed = createShadowedPointLight(
        scene,
        "candle",
        candlePosition,
        candleRange,
        Math.min(1024, preset.lampShadowMapSize),
        (m) => castsShadow(m) && !m.getBoundingInfo().intersectsPoint(candlePosition),
      );
      this.candle = shadowed.light;
      this.candleShadows = shadowed.shadows;
      // Drawn once; redrawn only when something near it is taken (refreshShadows).
      const map = shadowed.shadows.getShadowMap();
      if (map) map.refreshRate = RenderTargetTexture.REFRESHRATE_RENDER_ONCE;
    } else {
      this.candle = new PointLight("candle", candlePosition, scene);
      this.candle.shadowEnabled = false;
    }
    this.candle.diffuse = FLAME_COLOR.clone();
    this.candle.range = candleRange;
    this.candle.intensity = this.candlePower;
    exclude(this.candle, candlePosition, candleRange, true);
    useSoftFalloff(this.candle);
    this.candleFlame = CreateSphere(
      "candle_flame",
      { diameterX: 0.012, diameterY: 0.03, diameterZ: 0.012, segments: 12 },
      scene,
    );
    this.candleFlame.position.copyFrom(this.candle.position);
    const flameMat = new PBRMaterial("M_candle_flame", scene);
    flameMat.emissiveColor = FLAME_COLOR.scale(2);
    flameMat.albedoColor = Color3.Black();
    flameMat.disableLighting = true;
    this.candleFlame.material = flameMat;

    // The candle by Sora's diary on the writing desk (the save point): baked steady like
    // the oil lamps and flickered live; it dies with everything else in the power cut.
    const deskCandle = flames.get("desk_candle");
    if (deskCandle) {
      const p = deskCandle.position.clone();
      const light = new PointLight("desk_candle", p, scene);
      light.diffuse = FLAME_COLOR.clone();
      light.range = Number(deskCandle.extras.radius) || 1.6;
      light.intensity = 0.3;
      light.shadowEnabled = false;
      exclude(light, p, light.range, true);
      this.flames.push({ light, base: 0.3, phase: 4.2 });
      const flame = CreateSphere(
        "desk_candle_flame",
        { diameterX: 0.009, diameterY: 0.024, diameterZ: 0.009, segments: 10 },
        scene,
      );
      flame.position.copyFrom(p);
      flame.material = flameMat;
      flame.isPickable = false;
      this.flameMeshes.push(flame);
    }

    // Lightning through the two balcony doors: the bars, the drafting table and
    // everything in the front room thrown across the floor and up the walls.
    const outside = at("lightning", new Vector3(-2.6, 3.8, 4.0));
    this.lightning = new SpotLight("lightning", outside, new Vector3(0, -0.35, -1), 1.35, 2, scene);
    this.lightning.diffuse = new Color3(0.75, 0.82, 1);
    this.lightning.intensity = 0;
    this.lightning.range = 16;
    this.lightning.shadowMinZ = 0.3;
    this.lightning.shadowMaxZ = 16;
    this.lightning.renderPriority = 5;
    this.flashShadows = new ShadowGenerator(
      Math.min(2048, preset.lampShadowMapSize),
      this.lightning,
    );
    this.flashShadows.usePercentageCloserFiltering = true;
    this.flashShadows.filteringQuality = ShadowGenerator.QUALITY_MEDIUM;
    this.flashShadows.bias = 0.0015;
    this.flashShadows.normalBias = 0.012;
    // A whole sky, not a point: the flash's shadows are deep but not black.
    this.flashShadows.darkness = 0.12;
    const flashMap = this.flashShadows.getShadowMap();
    if (flashMap) {
      flashMap.renderList = scene.meshes.filter(
        (m) =>
          castsShadow(m) &&
          Vector3.Distance(m.getBoundingInfo().boundingSphere.centerWorld, outside) < 16,
      );
      flashMap.refreshRate = RenderTargetTexture.REFRESHRATE_RENDER_ONCE;
    }
    for (const mesh of scene.meshes) if (receivesShadow(mesh)) mesh.receiveShadows = true;
    for (const light of [this.deskLamp, highlight, this.writingLight, this.airwellBulb])
      this.lamps.push([light, light.intensity]);
    // What glows inside (not the neighbours' windows or the lightning on the glass).
    for (const material of scene.materials)
      if (
        material instanceof PBRMaterial &&
        material.emissiveColor.toLuminance() > 0.001 &&
        !/neighbour|glass_window|window_glass/i.test(material.name)
      )
        this.glows.push([material, material.emissiveColor.clone()]);
    for (const mesh of scene.meshes)
      if (/^window_glass/.test(mesh.name) && mesh.material instanceof PBRMaterial)
        this.glass.push(mesh.material);
  }

  get candleIsLit(): boolean {
    return this.candleLit;
  }

  /** A flash now, for a scripted scare; the 20–40 s rhythm carries on after it. */
  strike(): void {
    this.storm.strike();
  }

  /** Something near the candle was taken or moved: draw its shadows again once. */
  refreshShadows(): void {
    this.candleShadows?.getShadowMap()?.resetRefreshCounter();
    this.flashShadows.getShadowMap()?.resetRefreshCounter();
  }

  /**
   * Every light on the floor dies at once and comes back stuttering (POWER_CUT): the
   * baked light, the electric lamps, the oil flames, the candle. Outside, the street and
   * the storm go on.
   */
  powerCut(): void {
    this.held = false;
    this.cutAt = 0;
  }

  /**
   * Every light on the floor drops at once to a glow (HELD_LIGHT: enough to make out the
   * room, the user found it too dark at nothing) and stays there until lightsBack().
   */
  lightsOut(): void {
    this.held = true;
    this.cutAt = 0;
  }

  /** The lights stutter back on after lightsOut() (the end of POWER_CUT). */
  lightsBack(): void {
    this.held = false;
    this.cutAt = POWER_RETURN;
  }

  /** The lights are held down for the dancer (lightsOut), not out in the stutter. */
  get dimmed(): boolean {
    return this.held;
  }

  /** P05: the shelf candle goes out. */
  snuffCandle(): void {
    this.candleLit = false;
    this.candle.setEnabled(false);
    this.candleFlame.setEnabled(false);
  }

  /** Light reaching Sora's eyes for eye adaptation (1 = her lamp at arm's length). */
  lightAtEye(eye: Vector3): number {
    let light = 0;
    // Runtime intensities are matched to the bake, not to each other: weigh them as seen.
    for (const [l, weight] of [
      [this.deskLamp, 0.2],
      [this.writingLight, 0.3],
      [this.candle, 1],
      [this.airwellBulb, 0.3],
    ] as const) {
      if (!l.isEnabled()) continue;
      const d = Math.max(0.5, Vector3.Distance(eye, l.getAbsolutePosition()));
      light += (l.intensity * weight) / (d * d) / 14;
    }
    for (const { light: flame } of this.flames) {
      const d = Math.max(0.5, Vector3.Distance(eye, flame.getAbsolutePosition()));
      light += 0.6 / (d * d) / 14;
    }
    return light + 0.15 + this.lightning.intensity * 0.05;
  }

  update(dt: number): void {
    this.time += dt;
    const t = this.time;
    // Candle: never steady (Art Bible), out of phase with everything else.
    if (this.candleLit)
      this.candle.intensity =
        this.candlePower * (0.88 + 0.07 * Math.sin(t * 9.1) + 0.05 * Math.sin(t * 17.3 + 1));
    // Each oil lamp's flicker rides on its baked glow.
    for (const { light, base, phase } of this.flames)
      light.intensity =
        base * (0.75 + 0.18 * Math.sin(t * 6.3 + phase) + 0.07 * Math.sin(t * 14.1 + phase * 3));
    for (const flame of this.flameMeshes) flame.scaling.y = 1 + 0.1 * Math.sin(t * 11.7 + 2.3);
    // The power cut, over everything above.
    if (this.cutAt !== null) {
      this.cutAt += dt;
      this.power = this.held ? HELD_LIGHT : powerAt(this.cutAt);
      if (this.power === 1 && this.cutAt > 2) this.cutAt = null;
      for (const [light, full] of this.lamps) light.intensity = full * this.power;
      for (const { light } of this.flames) light.intensity *= this.power;
      if (this.candleLit) this.candle.intensity *= this.power;
      this.candleFlame.isVisible = this.power > 0.5;
      for (const flame of this.flameMeshes) flame.isVisible = this.power > 0.5;
      if (this.lightmap) this.lightmap.level = this.lightmapLevel * this.power;
      for (const [material, full] of this.glows)
        material.emissiveColor.copyFrom(full).scaleInPlace(this.power);
    }
    const level = this.storm.update(dt);
    this.lightning.intensity = level * 60;
    // Things are picked up and drawers opened between flashes: redraw while lit.
    if (level > 0) this.flashShadows.getShadowMap()?.resetRefreshCounter();
    for (const glass of this.glass)
      glass.emissiveColor = new Color3(0.6, 0.68, 0.85).scale(level * 1.2);
  }

  /** True during a lightning flash (thunder follows a few seconds later). */
  get flashing(): boolean {
    return this.storm.flashing;
  }
}

/** Solid, lit, world-space geometry: what can stand between a light and a wall. */
function castsShadow(m: AbstractMesh): boolean {
  const material = m.material;
  return (
    m.isEnabled() &&
    m.isVisible &&
    m.visibility > 0 &&
    m.renderingGroupId === 0 &&
    m.getTotalVertices() > 0 &&
    !!material &&
    material.alpha >= 1 &&
    // Blended decals (the plaster cracks) would throw their whole quad as a shadow.
    !material.needAlphaBlending() &&
    !m.name.startsWith("desk_lamp") &&
    !/glass|flame|rain|ink_line|ink_blot|pickup_volume|ceiling|roof/.test(m.name)
  );
}

function receivesShadow(m: AbstractMesh): boolean {
  const material = m.material;
  return (
    m.renderingGroupId === 0 &&
    m.getTotalVertices() > 0 &&
    !!material &&
    !/flame|rain/.test(m.name) &&
    !("disableLighting" in material && material.disableLighting === true)
  );
}
