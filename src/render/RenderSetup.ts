import { PointLight } from "@babylonjs/core/Lights/pointLight";
import { ShadowGenerator } from "@babylonjs/core/Lights/Shadows/shadowGenerator";
import { ClusteredLightContainer } from "@babylonjs/core/Lights/Clustered/clusteredLightContainer";
import { SSAO2RenderingPipeline } from "@babylonjs/core/PostProcesses/RenderPipeline/Pipelines/ssao2RenderingPipeline";
import { TAARenderingPipeline } from "@babylonjs/core/PostProcesses/RenderPipeline/Pipelines/taaRenderingPipeline";
import { DefaultRenderingPipeline } from "@babylonjs/core/PostProcesses/RenderPipeline/Pipelines/defaultRenderingPipeline";
import { ImageProcessingConfiguration } from "@babylonjs/core/Materials/imageProcessingConfiguration";
import { ColorCurves } from "@babylonjs/core/Materials/colorCurves";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { Scene } from "@babylonjs/core/scene";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { Camera } from "@babylonjs/core/Cameras/camera";
import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import type { QualityPreset } from "./QualityPresets";
import { VolumetricFog } from "./VolumetricFog";
import "@babylonjs/core/Lights/Shadows/shadowGeneratorSceneComponent";
import "@babylonjs/core/Lights/Clustered/clusteredLightingSceneComponent";
import "@babylonjs/core/Rendering/prePassRendererSceneComponent";
import "@babylonjs/core/Rendering/geometryBufferRendererSceneComponent";
import "@babylonjs/core/PostProcesses/RenderPipeline/postProcessRenderPipelineManagerSceneComponent";

/** Kerosene lamp and flame colour from the Art Bible (#FF9A3C). */
export const FLAME_COLOR = Color3.FromHexString("#FF9A3C");

/**
 * A point light that casts soft shadows. Point lights render a cube map (six
 * views), so each one only draws casters within its range, chosen every frame.
 */
export function createShadowedPointLight(
  scene: Scene,
  name: string,
  position: Vector3,
  range: number,
  mapSize: number,
  isCaster: (mesh: AbstractMesh) => boolean,
): { light: PointLight; shadows: ShadowGenerator } {
  const light = new PointLight(name, position, scene);
  light.diffuse = FLAME_COLOR.clone();
  light.range = range;

  const shadows = new ShadowGenerator(mapSize, light);
  // Point lights fall back from PCF to Poisson sampling on cube maps; it is soft and cheap.
  shadows.usePoissonSampling = true;
  shadows.bias = 0.004;
  shadows.normalBias = 0.02;
  shadows.darkness = 0;

  const map = shadows.getShadowMap();
  if (map) {
    map.renderList = null;
    map.renderListPredicate = (mesh) => {
      if (!isCaster(mesh)) return false;
      const sphere = mesh.getBoundingInfo().boundingSphere;
      const reach = range + sphere.radiusWorld;
      return (
        Vector3.DistanceSquared(sphere.centerWorld, light.getAbsolutePosition()) < reach * reach
      );
    };
  }
  return { light, shadows };
}

/** Small unshadowed lights (candles, embers, incense) handled by clustered lighting. */
export function createClusteredLights(
  scene: Scene,
  positions: Vector3[],
  range: number,
  intensity: number,
): { container: ClusteredLightContainer; lights: PointLight[] } {
  const lights = positions.map((p, i) => {
    const light = new PointLight(`candle_${i}`, p, scene);
    light.diffuse = FLAME_COLOR.clone();
    light.range = range;
    light.intensity = intensity;
    light.shadowEnabled = false;
    return light;
  });
  const container = new ClusteredLightContainer("candles", lights, scene);
  return { container, lights };
}

export interface PostPipeline {
  ssao: SSAO2RenderingPipeline | null;
  fog: VolumetricFog | null;
  taa: TAARenderingPipeline | null;
  main: DefaultRenderingPipeline;
  dispose(): void;
}

/**
 * Builds the post-processing chain, in order: SSAO → volumetric fog → TAA →
 * bloom, chromatic aberration, grain, vignette, tone mapping and the 1930s grade.
 * Creation order is the order the effects run.
 */
export function createPostPipeline(
  scene: Scene,
  camera: Camera,
  preset: QualityPreset,
  /** Switch effects off on top of the preset (spikes use this to measure costs). */
  overrides: { ssao?: boolean; fog?: boolean } = {},
): PostPipeline {
  let ssao: SSAO2RenderingPipeline | null = null;
  if (preset.ssao && overrides.ssao !== false) {
    ssao = new SSAO2RenderingPipeline(
      "ssao",
      scene,
      { ssaoRatio: preset.ssaoRatio, blurRatio: 1 },
      [camera],
    );
    ssao.samples = preset.ssaoSamples;
    ssao.radius = 1.2;
    ssao.totalStrength = 1.1;
    ssao.maxZ = 40;
    ssao.expensiveBlur = preset.ssaoRatio >= 1;
  }

  let fog: VolumetricFog | null = null;
  if (overrides.fog !== false) {
    if (preset.volumetricFog) {
      fog = new VolumetricFog(scene, camera, { ratio: preset.fogRatio, steps: preset.fogSteps });
    } else {
      // Low: classic exponential fog in the materials. No glow around the lamp,
      // but distance still disappears into darkness the same way.
      scene.fogMode = Scene.FOGMODE_EXP2;
      scene.fogDensity = 0.06;
      scene.fogColor = new Color3(0.012, 0.011, 0.012);
    }
  }

  let taa: TAARenderingPipeline | null = null;
  if (preset.taa) {
    taa = new TAARenderingPipeline("taa", scene, [camera]);
    taa.samples = 8;
    taa.reprojectHistory = true;
    taa.clampHistory = true;
    taa.disableOnCameraMove = false;
  }

  const main = new DefaultRenderingPipeline("main", true, scene, [camera]);
  main.fxaaEnabled = !preset.taa;
  main.bloomEnabled = true;
  main.bloomThreshold = 0.9;
  main.bloomWeight = 0.35;
  main.bloomKernel = 64;
  main.bloomScale = 0.5;
  main.chromaticAberrationEnabled = true;
  main.chromaticAberration.aberrationAmount = 8;
  main.chromaticAberration.radialIntensity = 0.6;
  main.grainEnabled = true;
  main.grain.intensity = 9;
  main.grain.animated = true;

  const ip = main.imageProcessing;
  ip.toneMappingEnabled = true;
  ip.toneMappingType = ImageProcessingConfiguration.TONEMAPPING_ACES;
  ip.exposure = 1.5;
  ip.contrast = 1.15;
  ip.vignetteEnabled = true;
  ip.vignetteWeight = 2.2;
  ip.vignetteColor.set(0.05, 0.03, 0.02, 0);
  // Warm, slightly desaturated 1930s grade (Art Bible, colour script).
  const curves = new ColorCurves();
  curves.globalSaturation = -25;
  curves.highlightsHue = 35;
  curves.highlightsDensity = 25;
  curves.shadowsHue = 210;
  curves.shadowsDensity = 15;
  ip.colorCurvesEnabled = true;
  ip.colorCurves = curves;

  return {
    ssao,
    fog,
    taa,
    main,
    dispose() {
      main.dispose();
      taa?.dispose();
      fog?.dispose();
      ssao?.dispose();
    },
  };
}
