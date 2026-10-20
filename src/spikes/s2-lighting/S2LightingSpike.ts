import type { WebGPUEngine } from "@babylonjs/core/Engines/webgpuEngine";
import { Scene } from "@babylonjs/core/scene";
import { UniversalCamera } from "@babylonjs/core/Cameras/universalCamera";
import { Camera } from "@babylonjs/core/Cameras/camera";
import { HemisphericLight } from "@babylonjs/core/Lights/hemisphericLight";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { CreateCylinder } from "@babylonjs/core/Meshes/Builders/cylinderBuilder";
import { CreateSphere } from "@babylonjs/core/Meshes/Builders/sphereBuilder";
import { CreateCapsule } from "@babylonjs/core/Meshes/Builders/capsuleBuilder";
import { Color3, Color4 } from "@babylonjs/core/Maths/math.color";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { PointLight } from "@babylonjs/core/Lights/pointLight";
import type { ShadowGenerator } from "@babylonjs/core/Lights/Shadows/shadowGenerator";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { enablePhysics } from "../../core/Physics";
import { KeyboardMouseInput } from "../../player/InputSource";
import { PlayerController } from "../../player/PlayerController";
import { PerfOverlay } from "../../debug/PerfOverlay";
import { formatBenchmark, runBenchmark, type BenchmarkResult } from "../../debug/Benchmark";
import { getPreset, isQualityName, type QualityPreset } from "../../render/QualityPresets";
import {
  createClusteredLights,
  createPostPipeline,
  createShadowedPointLight,
  FLAME_COLOR,
} from "../../render/RenderSetup";
import { mergeStaticMeshes } from "../../render/StaticBatcher";
import { ShadowScheduler } from "../../render/ShadowScheduler";
import { SpikeHud } from "../SpikeHud";
import { buildHall } from "./hall";

/** Results exposed for automated checks (`window.spikeResult`). */
export interface S2Result {
  preset: QualityPreset;
  features: Record<string, boolean>;
  benchmark?: BenchmarkResult;
}

/**
 * Spike S2 (Development Plan, section 2.2): can the full lighting target run on
 * minimum spec? Pass: 60 fps at 1080p on an RTX 2060-class GPU with the lamp,
 * 4 shadowed flames, 32+ unshadowed lights, SSAO and volumetric fog.
 *
 * URL options: `quality=medium|high|ultra` (default medium), `flames=0–4`
 * (default 4, the spike target), `candles=<n>` (default from the preset),
 * `ssao=0`, `fog=0`, `taa=0` (switch features off to find their cost),
 * `merge=0` (no static batching), `flameRefresh=all|rotate` (flame shadows every
 * frame, or 2 per frame in rotation, instead of cached and re-rendered only when
 * the spirit is in range), `spirit=0` (no moving shadow caster),
 * `bench=1` (scripted 20 s run at 1080p), `res=1440` (bench at 2560×1440).
 */
export async function runS2(engine: WebGPUEngine, params: URLSearchParams): Promise<void> {
  const canvas = engine.getRenderingCanvas() as HTMLCanvasElement;
  const qualityParam = params.get("quality");
  const quality = isQualityName(qualityParam) ? qualityParam : "medium";
  const flag = (name: string) => params.get(name) !== "0";
  const preset = getPreset(quality, {
    shadowedFlames: clampInt(params.get("flames"), 0, 4, 4),
    clusteredLights: clampInt(params.get("candles"), 0, 256, getPreset(quality).clusteredLights),
    taa: flag("taa") && getPreset(quality).taa,
  });
  const features = { ssao: flag("ssao"), fog: flag("fog"), taa: preset.taa, merge: flag("merge") };
  const flameRefresh = params.get("flameRefresh") ?? "cached";
  const flamesEveryFrame = flameRefresh === "all";
  const withSpirit = flag("spirit");
  const bench = params.get("bench") === "1";

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
  let noShadow = hall.noShadow;
  if (features.merge) {
    const statics = scene.meshes.filter((m): m is Mesh => m instanceof Mesh && m.isVisible);
    const batches = mergeStaticMeshes(statics, {
      cellSize: 3,
      group: (m) => (noShadow.has(m) ? "noShadow" : ""),
    });
    noShadow = new Set(
      batches.filter((m) => (m.metadata as { batchGroup?: string }).batchGroup === "noShadow"),
    );
  }
  const isCaster = (mesh: { isVisible: boolean }) => mesh.isVisible && !noShadow.has(mesh as Mesh);

  // Moonlight through the gaps: almost nothing, so the lamp matters.
  const moon = new HemisphericLight("moon", new Vector3(0.3, 1, -0.2), scene);
  moon.diffuse = new Color3(0.25, 0.3, 0.45);
  moon.groundColor = new Color3(0.02, 0.02, 0.03);
  moon.intensity = 0.04;

  // Sora's kerosene lamp, held low in the left hand.
  const lampRig = createShadowedPointLight(
    scene,
    "lamp",
    new Vector3(-0.28, -0.3, 0.45),
    8,
    preset.lampShadowMapSize,
    isCaster,
  );
  lampRig.light.parent = camera;
  lampRig.light.intensity = 14;
  const lampMeshes = buildLampMesh(scene, camera);
  for (const m of lampMeshes) noShadow.add(m);

  const flames: PointLight[] = [];
  const flameShadows: ShadowGenerator[] = [];
  for (let i = 0; i < preset.shadowedFlames; i++) {
    // Useful light radius: about 4 m for candles and the altar lamp, 6 m for the brazier.
    const rig = createShadowedPointLight(
      scene,
      `flame_${i}`,
      hall.flamePositions[i],
      i === 3 ? 6 : 4,
      preset.flameShadowMapSize,
      isCaster,
    );
    rig.light.intensity = i === 3 ? 14 : 6;
    flames.push(rig.light);
    flameShadows.push(rig.shadows);
  }
  const scheduler = flamesEveryFrame
    ? null
    : new ShadowScheduler(scene, flameShadows, {
        rotatePerFrame: flameRefresh === "rotate" ? 2 : 0,
        maxDirtyPerFrame: 2,
      });

  // A spirit stand-in walking slowly around the coffin: it casts shadows from the
  // lamp and flames, and makes nearby flame shadows re-render (the realistic case).
  if (withSpirit) {
    const spirit = CreateCapsule("spirit", { height: 1.9, radius: 0.28, tessellation: 24 }, scene);
    const spiritMat = new PBRMaterial("M_spirit", scene);
    spiritMat.albedoColor = new Color3(0.02, 0.02, 0.025);
    spiritMat.roughness = 0.9;
    spirit.material = spiritMat;
    spirit.receiveShadows = true;
    scene.onBeforeRenderObservable.add(() => {
      const angle = (performance.now() / 1000) * 0.2;
      spirit.position.set(Math.cos(angle) * 3.4, 0.95, Math.sin(angle) * 2.6);
      scheduler?.markDirtyNear(spirit.position, 1);
    });
  }
  const candles = createClusteredLights(scene, hall.candlePositions, 2.5, 0.9);

  const pipeline = createPostPipeline(scene, camera, preset, features);
  pipeline.fog?.lights.push(lampRig.light, ...flames);

  // Flicker: each flame breathes on its own rhythm (Audio and Art Bibles: never steady).
  const baseIntensity = new Map<PointLight, number>(
    [lampRig.light, ...flames, ...candles.lights].map((l) => [l, l.intensity]),
  );
  scene.onBeforeRenderObservable.add(() => {
    const t = performance.now() / 1000;
    let i = 0;
    for (const [light, base] of baseIntensity) {
      const k = i++ * 1.7;
      light.intensity =
        base * (0.9 + 0.06 * Math.sin(t * 7.3 + k) + 0.04 * Math.sin(t * 13.1 + k * 2.3));
    }
  });

  const perf = new PerfOverlay(engine, scene);
  const hud = new SpikeHud(
    "Spike S2 · Lamp lighting",
    `Can the full lighting target hold 60 fps at 1080p on an RTX 2060? Preset: ${preset.name} (${preset.target}).`,
    [
      "Click to look",
      "WASD move",
      "B benchmark",
      "Q next preset",
      "1 SSAO",
      "2 fog",
      "3 TAA",
      "4 flames",
      "5 batching",
      "6 flame refresh",
      "7 spirit",
      "F2 hide panel",
      "F3 stats",
    ],
  );
  const result: S2Result = { preset, features };
  (window as unknown as { spikeResult: S2Result }).spikeResult = result;
  if (import.meta.env.DEV)
    (window as unknown as { spike: unknown }).spike = { scene, pipeline, camera };

  const describe = () => [
    `lamp: shadow ${preset.lampShadowMapSize}px cube · shadowed flames: ${flames.length} × ${preset.flameShadowMapSize}px (${{ all: "every frame", cached: "cached, re-rendered when the spirit is near", rotate: "2 per frame in rotation" }[flameRefresh] ?? flameRefresh})`,
    `static batching ${features.merge ? "on (3 m cells)" : "off"} · meshes ${scene.meshes.length} · spirit ${withSpirit ? "walking" : "off"}`,
    `clustered lights: ${candles.lights.length} · SSAO ${features.ssao ? `on (${preset.ssaoRatio}×, ${preset.ssaoSamples} samples)` : "off"}`,
    `fog ${features.fog ? `on (${preset.fogRatio}×, ${preset.fogSteps} steps)` : "off"} · TAA ${features.taa ? "on" : "off"}`,
  ];

  if (bench) {
    // Render at exactly the target resolution, whatever the window size.
    const height = params.get("res") === "1440" ? 1440 : 1080;
    engine.setHardwareScalingLevel(1);
    engine.setSize(Math.round((height * 16) / 9), height);
    const path = hall.benchPath;
    hud.setReadout([...describe(), "benchmark running: 5 s warm-up, then 20 s measured…"]);
    await scene.whenReadyAsync();
    engine.runRenderLoop(() => scene.render());
    const benchmark = await runBenchmark(scene, perf, {
      warmupSec: 5,
      durationSec: 20,
      onProgress: (t) => moveAlongLoop(camera, path, hall.benchLookAt, t * 1.25),
    });
    result.benchmark = benchmark;
    const text = `${formatBenchmark(benchmark)}\n${describe().join("\n")}`;
    hud.showReport(text, benchmark.budget.pass);
    console.info(`[S2] ${text.replace(/\n/g, " | ")}`);
    return;
  }

  const keyboard = new KeyboardMouseInput(canvas, 0.0022);
  const player = new PlayerController(scene, camera, keyboard, hall.spawn);
  hud.setReadout([
    ...describe(),
    "Walk around: watch fps and GPU time (F3) near the flames and the door.",
  ]);

  const reloadWith = (changes: Record<string, string | null>) => {
    const next = new URLSearchParams(window.location.search);
    for (const [key, value] of Object.entries(changes)) {
      if (value === null) next.delete(key);
      else next.set(key, value);
    }
    window.location.search = next.toString();
  };
  const toggle = (name: string) => reloadWith({ [name]: params.get(name) === "0" ? null : "0" });
  window.addEventListener("keydown", (e) => {
    if (e.code === "KeyB") reloadWith({ bench: "1" });
    if (e.code === "KeyQ")
      reloadWith({ quality: { medium: "high", high: "ultra", ultra: "medium" }[quality] });
    if (e.code === "Digit1") toggle("ssao");
    if (e.code === "Digit2") toggle("fog");
    if (e.code === "Digit3") toggle("taa");
    if (e.code === "Digit4") reloadWith({ flames: preset.shadowedFlames > 0 ? "0" : null });
    if (e.code === "Digit5") toggle("merge");
    if (e.code === "Digit6")
      reloadWith({
        flameRefresh: { cached: "rotate", rotate: "all", all: null }[flameRefresh] ?? null,
      });
    if (e.code === "Digit7") toggle("spirit");
  });
  if (import.meta.env.DEV)
    (window as unknown as { spike: Record<string, unknown> }).spike.player = player;
  engine.runRenderLoop(() => scene.render());
}

/** Moves the camera smoothly around a closed loop of points, looking towards a target. */
function moveAlongLoop(
  camera: UniversalCamera,
  points: Vector3[],
  lookAt: Vector3,
  t: number,
): void {
  const n = points.length;
  const f = (((t % 1) + 1) % 1) * n;
  const i = Math.floor(f);
  const p = Vector3.CatmullRom(
    points[(i - 1 + n) % n],
    points[i],
    points[(i + 1) % n],
    points[(i + 2) % n],
    f - i,
  );
  camera.position.copyFrom(p);
  // Look partly ahead along the path and partly at the coffin, like a player would.
  const ahead = Vector3.CatmullRom(
    points[i],
    points[(i + 1) % n],
    points[(i + 2) % n],
    points[(i + 3) % n],
    f - i,
  );
  camera.setTarget(Vector3.Lerp(ahead, lookAt, 0.6));
}

function buildLampMesh(scene: Scene, camera: Camera): Mesh[] {
  const glassMat = new PBRMaterial("M_lampGlass", scene);
  glassMat.albedoColor = new Color3(0.9, 0.85, 0.7);
  glassMat.alpha = 0.35;
  glassMat.roughness = 0.1;
  const flameMat = new PBRMaterial("M_lampFlame", scene);
  flameMat.emissiveColor = FLAME_COLOR.scale(5);
  flameMat.disableLighting = true;
  flameMat.albedoColor = Color3.Black();

  const glass = CreateCylinder(
    "lamp_glass",
    { diameterTop: 0.07, diameterBottom: 0.1, height: 0.14, tessellation: 24 },
    scene,
  );
  glass.material = glassMat;
  const flame = CreateSphere(
    "lamp_flame",
    { diameterX: 0.02, diameterY: 0.045, diameterZ: 0.02, segments: 8 },
    scene,
  );
  flame.material = flameMat;
  for (const mesh of [glass, flame]) {
    mesh.parent = camera;
    mesh.position.set(-0.28, -0.32, 0.45);
    mesh.isPickable = false;
  }
  return [glass, flame];
}

function clampInt(value: string | null, min: number, max: number, fallback: number): number {
  const n = value === null ? NaN : Number.parseInt(value, 10);
  return Number.isFinite(n) ? Math.max(min, Math.min(max, n)) : fallback;
}
