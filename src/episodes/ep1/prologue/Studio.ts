import type { Scene } from "@babylonjs/core/scene";
import { HemisphericLight } from "@babylonjs/core/Lights/hemisphericLight";
import { PointLight } from "@babylonjs/core/Lights/pointLight";
import { SpotLight } from "@babylonjs/core/Lights/spotLight";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { CreateSphere } from "@babylonjs/core/Meshes/Builders/sphereBuilder";
import type { Mesh } from "@babylonjs/core/Meshes/mesh";
import type { QualityPreset } from "../../../render/QualityPresets";
import { createShadowedPointLight, FLAME_COLOR } from "../../../render/RenderSetup";
import type { Area } from "../../../core/AreaLoader";
import { Lightning } from "../Lightning";
import { useSoftFalloff } from "../../../render/softLampFalloff";

/**
 * The studio's lights (Beat Sheet 4.1): the green glass desk lamp as the key
 * light, the shelf candle as fill, and lightning through the south window.
 * The candle can be put out (P05).
 */
export class StudioLights {
  /** Soft falloff caps the close wall; this level keeps cloth and paper readable. */
  private readonly candlePower = 3.2;
  readonly deskLamp: PointLight;
  readonly candle: PointLight;
  readonly lightning: SpotLight;
  readonly writingLight: PointLight;
  private readonly candleFlame: Mesh;
  private readonly candleBounce: PointLight;
  private readonly windowGlass: PBRMaterial | null;
  private candleLit = true;
  private readonly storm = new Lightning();
  private time = 0;

  constructor(scene: Scene, area: Area, preset: QualityPreset) {
    // Imported materials must include the shelf candle as well as the other room lights.
    for (const material of scene.materials)
      if (material instanceof PBRMaterial) material.maxSimultaneousLights = 8;
    const { markers, flames } = area.level;
    const at = (m: { position: Vector3 } | undefined, fallback: Vector3) =>
      m?.position.clone() ?? fallback;

    // Dim night sky through the window, so the room is never pure black.
    const sky = new HemisphericLight("night_sky", new Vector3(0, 1, -0.4), scene);
    sky.diffuse = new Color3(0.35, 0.42, 0.6);
    sky.groundColor = new Color3(0.04, 0.035, 0.03);
    sky.intensity = 0.13;
    sky.specular = new Color3(0.12, 0.15, 0.2);

    const lamp = createShadowedPointLight(
      scene,
      "desk_lamp",
      at(markers.get("desk_lamp"), new Vector3(-0.3, 1.1, -2.45)),
      6,
      preset.lampShadowMapSize,
      (m) =>
        m.isEnabled() &&
        m.isVisible &&
        m.visibility > 0 &&
        m.renderingGroupId === 0 &&
        !m.name.startsWith("desk_lamp") &&
        m.name !== "ink_line" &&
        m.name !== "ink_blot",
    );
    this.deskLamp = lamp.light;
    // An electric bulb under green glass: warmer than daylight, cooler than a flame.
    this.deskLamp.diffuse = new Color3(1, 0.86, 0.62);
    this.deskLamp.intensity = 4;
    useSoftFalloff(this.deskLamp);

    // A shaded writing light makes the drawer's pale lining and printed matchbox
    // readable. Its soft core avoids bleaching paper and nearby brass to white.
    this.writingLight = new PointLight("writing_sconce", new Vector3(-0.27, 1.55, -2.5), scene);
    this.writingLight.diffuse = new Color3(1, 0.81, 0.53);
    this.writingLight.range = 3.8;
    this.writingLight.intensity = 3.2;
    this.writingLight.shadowEnabled = false;
    useSoftFalloff(this.writingLight);
    const windowBounce = new SpotLight(
      "studio_window_bounce",
      new Vector3(-3, 2.15, 0.1),
      new Vector3(0, -0.3, -1),
      2.2,
      1,
      scene,
    );
    windowBounce.diffuse = new Color3(0.45, 0.59, 0.76);
    windowBounce.specular = new Color3(0.15, 0.2, 0.28);
    windowBounce.intensity = 1.4;
    windowBounce.range = 7;
    windowBounce.shadowEnabled = false;

    const candleAt = flames.get("candle");
    this.candle = new PointLight("candle", at(candleAt, new Vector3(-2.33, 1.53, -4.83)), scene);
    this.candle.diffuse = FLAME_COLOR.clone();
    this.candle.range = Number(candleAt?.extras.radius) || 3;
    this.candle.intensity = this.candlePower;
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
    // Light returning from the wall and ledge reaches the forward-facing cloth spines.
    this.candleBounce = new PointLight(
      "shelf_candle_bounce",
      new Vector3(-3.2, 1.63, -4.44),
      scene,
    );
    this.candleBounce.diffuse = FLAME_COLOR.clone();
    this.candleBounce.range = 1.4;
    this.candleBounce.intensity = 1.6;
    this.candleBounce.includedOnlyMeshes = scene.meshes.filter((mesh) =>
      mesh.material?.name.startsWith("M_studio_book_"),
    );
    useSoftFalloff(this.candleBounce);

    const outside = at(markers.get("lightning"), new Vector3(-3, 2.4, 1.5));
    this.lightning = new SpotLight("lightning", outside, new Vector3(0, -0.35, -1), 1.3, 2, scene);
    this.lightning.diffuse = new Color3(0.75, 0.82, 1);
    this.lightning.intensity = 0;
    this.lightning.range = 12;
    const glass = scene.getMeshByName("window_glass");
    this.windowGlass = glass?.material instanceof PBRMaterial ? glass.material : null;
  }

  get candleIsLit(): boolean {
    return this.candleLit;
  }

  /** A flash now, for a scripted scare; the 20–40 s rhythm carries on after it. */
  strike(): void {
    this.storm.strike();
  }

  /** P05: the shelf candle goes out. */
  snuffCandle(): void {
    this.candleLit = false;
    this.candle.setEnabled(false);
    this.candleFlame.setEnabled(false);
    this.candleBounce.setEnabled(false);
  }

  /** Light reaching Sora's eyes for eye adaptation (1 = her lamp at arm's length). */
  lightAtEye(eye: Vector3): number {
    let light = 0;
    for (const l of [this.deskLamp, this.writingLight, this.candle]) {
      if (!l.isEnabled()) continue;
      const d = Math.max(0.5, Vector3.Distance(eye, l.getAbsolutePosition()));
      light += l.intensity / (d * d) / 14;
    }
    return light + 0.15 + this.lightning.intensity * 0.05;
  }

  update(dt: number): void {
    this.time += dt;
    // Candle: never steady (Art Bible), out of phase with everything else.
    if (this.candleLit) {
      const t = this.time;
      this.candle.intensity =
        this.candlePower * (0.88 + 0.07 * Math.sin(t * 9.1) + 0.05 * Math.sin(t * 17.3 + 1));
      this.candleBounce.intensity = this.candle.intensity * 0.5;
    }
    const level = this.storm.update(dt);
    this.lightning.intensity = level * 60;
    if (this.windowGlass)
      this.windowGlass.emissiveColor = new Color3(0.6, 0.68, 0.85).scale(level * 1.5 + 0.03);
  }

  /** True during a lightning flash (thunder follows a few seconds later). */
  get flashing(): boolean {
    return this.storm.flashing;
  }
}
