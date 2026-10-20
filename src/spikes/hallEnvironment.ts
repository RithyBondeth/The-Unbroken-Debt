import type { WebGPUEngine } from "@babylonjs/core/Engines/webgpuEngine";
import { Scene } from "@babylonjs/core/scene";
import { UniversalCamera } from "@babylonjs/core/Cameras/universalCamera";
import { Camera } from "@babylonjs/core/Cameras/camera";
import { HemisphericLight } from "@babylonjs/core/Lights/hemisphericLight";
import { PointLight } from "@babylonjs/core/Lights/pointLight";
import type { ShadowGenerator } from "@babylonjs/core/Lights/Shadows/shadowGenerator";
import { Color3, Color4 } from "@babylonjs/core/Maths/math.color";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { enablePhysics } from "../core/Physics";
import type { QualityPreset } from "../render/QualityPresets";
import {
  createClusteredLights,
  createPostPipeline,
  createShadowedPointLight,
  FLAME_COLOR,
  limitLightToRange,
  type PostPipeline,
} from "../render/RenderSetup";
import { mergeStaticMeshes } from "../render/StaticBatcher";
import { buildHall, type Hall } from "./s2-lighting/hall";

export interface HallEnvironment {
  scene: Scene;
  camera: UniversalCamera;
  hall: Hall;
  lamp: { light: PointLight; shadows: ShadowGenerator };
  flames: PointLight[];
  /** Candles and sconces (clustered lights). */
  candles: ReturnType<typeof createClusteredLights>;
  moon: HemisphericLight;
  pipeline: PostPipeline;
}

/** Renders at exactly `height` (16:9) whatever the window size, for screenshots and benchmarks. */
export function lockRenderSize(engine: WebGPUEngine, height: number): void {
  engine.setHardwareScalingLevel(1);
  engine.setSize(Math.round((height * 16) / 9), height);
  engine.resize = () => undefined;
}

/**
 * The night funeral hall from Spike S2 as later spikes use it: static meshes
 * merged in 3 m cells, Sora's lamp (shadowed, held in her left hand), the four
 * flames limited to their range, clustered candles, moonlight and the full
 * post-processing chain for the preset. Meshes in rendering group 1 or above
 * (held items such as the sketchbook) never cast the lamp's shadow.
 */
export async function createHallEnvironment(
  engine: WebGPUEngine,
  preset: QualityPreset,
): Promise<HallEnvironment> {
  const scene = new Scene(engine);
  scene.clearColor = new Color4(0.004, 0.005, 0.008, 1);
  scene.skipPointerMovePicking = true;
  await enablePhysics(scene);

  const camera = new UniversalCamera("eye", new Vector3(0, 1.58, -3.5), scene);
  camera.fovMode = Camera.FOVMODE_HORIZONTAL_FIXED;
  camera.fov = (80 * Math.PI) / 180;
  camera.minZ = 0.05;
  camera.maxZ = 60;
  scene.activeCamera = camera;

  const hall = buildHall(scene, preset.clusteredLights);
  const statics = scene.meshes.filter((m): m is Mesh => m instanceof Mesh && m.isVisible);
  const batches = mergeStaticMeshes(statics, {
    cellSize: 3,
    group: (m) => (hall.noShadow.has(m) ? "noShadow" : ""),
  });
  const noShadow = new Set(
    batches.filter((m) => (m.metadata as { batchGroup?: string }).batchGroup === "noShadow"),
  );

  // Moonlight through the gaps: almost nothing, so the lamp matters.
  const moon = new HemisphericLight("moon", new Vector3(0.3, 1, -0.2), scene);
  moon.diffuse = new Color3(0.25, 0.3, 0.45);
  moon.groundColor = new Color3(0.02, 0.02, 0.03);
  moon.intensity = 0.04;

  const lamp = createShadowedPointLight(
    scene,
    "lamp",
    new Vector3(-0.28, -0.3, 0.45),
    8,
    preset.lampShadowMapSize,
    (m) => m.isVisible && m.renderingGroupId === 0 && !noShadow.has(m as Mesh),
  );
  lamp.light.parent = camera;
  lamp.light.intensity = 14;

  const flames = hall.flamePositions.map((p, i) => {
    const light = new PointLight(`flame_${i}`, p, scene);
    light.diffuse = FLAME_COLOR.clone();
    light.range = i === 3 ? 6 : 4;
    light.intensity = i === 3 ? 14 : 6;
    return light;
  });
  const candles = createClusteredLights(scene, hall.candlePositions, 2.5, 0.9);
  // Each flame shades only the room meshes in its range (S2); held items are not among them.
  const roomMeshes = [...scene.meshes];
  for (const flame of flames) limitLightToRange(flame, roomMeshes);

  const pipeline = createPostPipeline(scene, camera, preset, { ssao: preset.ssao, fog: true });
  pipeline.fog?.lights.push(lamp.light, ...flames);
  return { scene, camera, hall, lamp, flames, candles, moon, pipeline };
}
