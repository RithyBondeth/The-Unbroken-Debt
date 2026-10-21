import type { Scene } from "@babylonjs/core/scene";
import type { Camera } from "@babylonjs/core/Cameras/camera";
import { PointLight } from "@babylonjs/core/Lights/pointLight";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Constants } from "@babylonjs/core/Engines/constants";
import { RawTexture3D } from "@babylonjs/core/Materials/Textures/rawTexture3D";
import { Texture } from "@babylonjs/core/Materials/Textures/texture";
import type { ColorCurves } from "@babylonjs/core/Materials/colorCurves";
import type { DefaultRenderingPipeline } from "@babylonjs/core/PostProcesses/RenderPipeline/Pipelines/defaultRenderingPipeline";
import { buildLut, type GradeParams } from "./grade";
import {
  decayScare,
  EyeAdaptation,
  lookValues,
  targetExposure,
  type LookSettings,
  type Mood,
} from "./look";

/** "lut" is the episode's lookup table; "curves" the S2 colour curves; "off" no grade. */
export type GradeMode = "lut" | "curves" | "off";

const LUT_SIZE = 32;

/**
 * Drives the 1930s look on the final post-process each frame (Art Bible,
 * section 4): the episode's colour grade, slow eye adaptation from the light
 * reaching Sora, and grain, vignette and aberration from her fear, scares and
 * the player's settings.
 */
export class Atmosphere {
  readonly eye: EyeAdaptation;
  settings: LookSettings = { grain: true, aberration: true, brightness: 0 };
  mood: Mood = { fear: 0, scare: 0, memory: false };
  /** Exposure with Sora's lamp open at arm's length, and the most the eye ever reaches. */
  baseExposure = 1.5;
  maxExposure = 4.5;
  private lut: RawTexture3D;
  private readonly curves: ColorCurves | null;
  private mode: GradeMode = "lut";
  /**
   * Night sight: a faint, cool, unshadowed light around Sora that grows as her
   * eyes adjust to the dark, so shapes within about 2 m show (Art Bible's
   * darkness rule) while the rest of the room stays black.
   */
  readonly nightSight: PointLight;
  /** Night sight at full adjustment in total darkness. */
  nightSightIntensity = 5;

  constructor(
    private readonly scene: Scene,
    private readonly main: DefaultRenderingPipeline,
    grade: GradeParams,
    camera: Camera,
  ) {
    this.eye = new EyeAdaptation(this.baseExposure);
    this.nightSight = new PointLight("night_sight", new Vector3(0, 0.1, 0), scene);
    this.nightSight.parent = camera;
    this.nightSight.diffuse = new Color3(0.55, 0.62, 0.75);
    this.nightSight.specular = Color3.Black();
    this.nightSight.range = 2.5;
    this.nightSight.intensity = 0;
    this.nightSight.shadowEnabled = false;
    this.curves = main.imageProcessing.colorCurves;
    this.lut = this.makeLut(grade);
    this.gradeMode = "lut";
  }

  get gradeMode(): GradeMode {
    return this.mode;
  }

  set gradeMode(mode: GradeMode) {
    this.mode = mode;
    const ip = this.main.imageProcessing;
    ip.colorGradingEnabled = mode === "lut";
    ip.colorGradingTexture = mode === "lut" ? this.lut : null;
    ip.colorCurvesEnabled = mode === "curves" && this.curves !== null;
  }

  /** Swaps the episode grade (a new lookup table). */
  setGrade(grade: GradeParams): void {
    this.lut.dispose();
    this.lut = this.makeLut(grade);
    this.gradeMode = this.mode;
  }

  /** A scare: the aberration jolts, then fades in about a second. */
  scare(): void {
    this.mood.scare = 1;
  }

  /**
   * @param dt seconds since the last frame, not capped for hitches: eyes adapt in real time
   * @param light light reaching Sora's eyes, 1 = her open lamp at arm's length
   */
  update(dt: number, light: number): void {
    const exposure = this.eye.update(
      dt,
      targetExposure(light, this.baseExposure, this.maxExposure),
    );
    const ip = this.main.imageProcessing;
    ip.exposure = exposure * Math.pow(2, this.settings.brightness);
    // How far the eye has adjusted towards the dark (0 at the base exposure, 1 at the cap).
    const adjusted = Math.max(
      0,
      Math.log(exposure / this.baseExposure) / Math.log(this.maxExposure / this.baseExposure),
    );
    const darkness = Math.max(0, 1 - light);
    this.nightSight.intensity = this.nightSightIntensity * adjusted * darkness;

    const look = lookValues(this.mood, this.settings);
    ip.vignetteWeight = look.vignetteWeight;
    // Turning an effect on or off rebuilds post-processes: only on change.
    if (this.main.grainEnabled !== look.grain > 0) this.main.grainEnabled = look.grain > 0;
    if (look.grain > 0) this.main.grain.intensity = look.grain;
    const aberration = look.aberration > 0;
    if (this.main.chromaticAberrationEnabled !== aberration)
      this.main.chromaticAberrationEnabled = aberration;
    if (aberration) this.main.chromaticAberration.aberrationAmount = look.aberration;
    // Fade the scare after showing it, so its frame always gets the full jolt.
    this.mood.scare = decayScare(this.mood.scare, dt);
  }

  dispose(): void {
    this.nightSight.dispose();
    this.lut.dispose();
  }

  private makeLut(grade: GradeParams): RawTexture3D {
    const lut = new RawTexture3D(
      buildLut(grade, LUT_SIZE),
      LUT_SIZE,
      LUT_SIZE,
      LUT_SIZE,
      Constants.TEXTUREFORMAT_RGBA,
      this.scene,
      false,
      false,
      Texture.BILINEAR_SAMPLINGMODE,
    );
    lut.wrapU = Texture.CLAMP_ADDRESSMODE;
    lut.wrapV = Texture.CLAMP_ADDRESSMODE;
    lut.wrapR = Texture.CLAMP_ADDRESSMODE;
    return lut;
  }
}
