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

/** Seconds between lightning flashes (Episode 1 Beat Sheet, section 4.1: every 20–40 s). */
const LIGHTNING_GAP = { min: 20, max: 40 };

/**
 * The studio's lights (Beat Sheet 4.1): the green glass desk lamp as the key
 * light, the shelf candle as fill, and lightning through the south window.
 * The candle can be put out (P05).
 */
export class StudioLights {
  readonly deskLamp: PointLight;
  readonly candle: PointLight;
  readonly lightning: SpotLight;
  private readonly candleFlame: Mesh;
  private readonly windowGlass: PBRMaterial | null;
  private candleLit = true;
  private nextFlash: number;
  private flash: { start: number; pulses: number[] } | null = null;
  private time = 0;

  constructor(scene: Scene, area: Area, preset: QualityPreset) {
    const { markers, flames } = area.level;
    const at = (m: { position: Vector3 } | undefined, fallback: Vector3) =>
      m?.position.clone() ?? fallback;

    // Dim night sky through the window, so the room is never pure black.
    const sky = new HemisphericLight("night_sky", new Vector3(0, 1, -0.4), scene);
    sky.diffuse = new Color3(0.35, 0.42, 0.6);
    sky.groundColor = new Color3(0.04, 0.035, 0.03);
    sky.intensity = 0.05;

    const lamp = createShadowedPointLight(
      scene,
      "desk_lamp",
      at(markers.get("desk_lamp"), new Vector3(-0.3, 1.1, -2.45)),
      6,
      preset.lampShadowMapSize,
      (m) => m.isVisible && m.renderingGroupId === 0 && !m.name.startsWith("desk_lamp"),
    );
    this.deskLamp = lamp.light;
    // An electric bulb under green glass: warmer than daylight, cooler than a flame.
    this.deskLamp.diffuse = new Color3(1, 0.86, 0.62);
    this.deskLamp.intensity = 4;

    const candleAt = flames.get("candle");
    this.candle = new PointLight("candle", at(candleAt, new Vector3(-2.33, 1.53, -4.83)), scene);
    this.candle.diffuse = FLAME_COLOR.clone();
    this.candle.range = Number(candleAt?.extras.radius) || 3;
    this.candle.intensity = Number(candleAt?.extras.intensity) || 2;
    this.candleFlame = CreateSphere(
      "candle_flame",
      { diameterX: 0.02, diameterY: 0.045, segments: 8 },
      scene,
    );
    this.candleFlame.position.copyFrom(this.candle.position);
    const flameMat = new PBRMaterial("M_candle_flame", scene);
    flameMat.emissiveColor = FLAME_COLOR.scale(4);
    flameMat.albedoColor = Color3.Black();
    flameMat.disableLighting = true;
    this.candleFlame.material = flameMat;

    const outside = at(markers.get("lightning"), new Vector3(-3, 2.4, 1.5));
    this.lightning = new SpotLight("lightning", outside, new Vector3(0, -0.35, -1), 1.3, 2, scene);
    this.lightning.diffuse = new Color3(0.75, 0.82, 1);
    this.lightning.intensity = 0;
    this.lightning.range = 12;
    const glass = scene.getMeshByName("window_glass");
    this.windowGlass = glass?.material instanceof PBRMaterial ? glass.material : null;

    this.nextFlash = 6 + Math.random() * 6;
  }

  get candleIsLit(): boolean {
    return this.candleLit;
  }

  /** A flash now, for a scripted scare; the 20–40 s rhythm carries on after it. */
  strike(): void {
    this.nextFlash = this.time;
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
    for (const l of [this.deskLamp, this.candle]) {
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
      this.candle.intensity = 2 * (0.88 + 0.07 * Math.sin(t * 9.1) + 0.05 * Math.sin(t * 17.3 + 1));
    }
    // Lightning: one to three quick pulses, then darkness again.
    if (!this.flash && this.time >= this.nextFlash) {
      const pulses = [0, 0.09 + Math.random() * 0.08, 0.25 + Math.random() * 0.2].slice(
        0,
        1 + Math.floor(Math.random() * 3),
      );
      this.flash = { start: this.time, pulses };
      this.nextFlash =
        this.time + LIGHTNING_GAP.min + Math.random() * (LIGHTNING_GAP.max - LIGHTNING_GAP.min);
    }
    let level = 0;
    if (this.flash) {
      const since = this.time - this.flash.start;
      for (const p of this.flash.pulses)
        level = Math.max(level, Math.exp(-Math.max(0, since - p) / 0.05) * (since >= p ? 1 : 0));
      if (since > 1) this.flash = null;
    }
    this.lightning.intensity = level * 60;
    if (this.windowGlass)
      this.windowGlass.emissiveColor = new Color3(0.6, 0.68, 0.85).scale(level * 1.5 + 0.03);
  }

  /** True during a lightning flash (thunder follows a few seconds later). */
  get flashing(): boolean {
    return this.flash !== null;
  }
}
