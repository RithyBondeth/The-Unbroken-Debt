import type { WebGPUEngine } from "@babylonjs/core/Engines/webgpuEngine";
import { Scene } from "@babylonjs/core/scene";
import { UniversalCamera } from "@babylonjs/core/Cameras/universalCamera";
import { Camera } from "@babylonjs/core/Cameras/camera";
import { HemisphericLight } from "@babylonjs/core/Lights/hemisphericLight";
import { DirectionalLight } from "@babylonjs/core/Lights/directionalLight";
import { PointLight } from "@babylonjs/core/Lights/pointLight";
import { LoadAssetContainerAsync } from "@babylonjs/core/Loading/sceneLoader";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import type { BaseTexture } from "@babylonjs/core/Materials/Textures/baseTexture";
import { Color3, Color4 } from "@babylonjs/core/Maths/math.color";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { registerBuiltInLoaders } from "@babylonjs/loaders/dynamic";
import { EventBus } from "../../core/EventBus";
import type { GameEvents } from "../../core/events";
import { enablePhysics } from "../../core/Physics";
import { buildLevel, type Level } from "../../core/LevelBuilder";
import { KeyboardMouseInput } from "../../player/InputSource";
import { PlayerController } from "../../player/PlayerController";
import { PerfOverlay } from "../../debug/PerfOverlay";
import { SpikeHud } from "../SpikeHud";
import { SnagDetector } from "../s1-movement/SnagDetector";
import { WaypointBot, type BotReport } from "../s1-movement/WaypointBot";
import type { Waypoint } from "../s1-movement/course";
import { readGlbInfo, textureFormatName, type GlbInfo } from "./glbInfo";
import { runRenderLoop } from "../../render/renderLoop";
import { renderStallNotice } from "../../ui/html/RenderStallNotice";

/** Results exposed for automated checks (`window.spikeResult`). */
export interface S3Result {
  file: string;
  bytes: number;
  loadMs: number;
  glb: GlbInfo;
  triangles: number;
  materials: { name: string; textures: string[]; formats: string[] }[];
  colliders: Level["colliders"];
  ladders: number;
  warnings: string[];
  snags: number;
  bot?: BotReport;
}

const DEFAULT_FILE = "assets/spikes/s3_test_room.glb";
/** Budgets for the test room: a small area file (Art Bible, section 5.3). */
const MAX_BYTES = 3 * 1024 * 1024;
/** Textured materials in the test room and the slots each must fill. */
const TEXTURED = ["M_teak_planks", "M_bamboo_wall", "M_chest_wood"];

/**
 * Spike S3 (Development Plan, section 2.2): can a Blender model reach the
 * browser compressed? Loads an optimised .glb (meshopt + KTX2), checks its
 * materials and texture formats, builds colliders, a ladder and a bot route
 * from Blender node names, and walks the route.
 * URL: `?spike=s3` (add `&auto=1` for the bot, `&file=assets/…glb` for another file).
 */
export async function runS3(engine: WebGPUEngine, params: URLSearchParams): Promise<void> {
  registerBuiltInLoaders();
  const canvas = engine.getRenderingCanvas() as HTMLCanvasElement;
  const scene = new Scene(engine);
  scene.clearColor = new Color4(0.55, 0.62, 0.7, 1);
  await enablePhysics(scene);

  const sky = new HemisphericLight("sky", new Vector3(0.2, 1, 0.1), scene);
  sky.intensity = 0.9;
  sky.groundColor = new Color3(0.3, 0.25, 0.2);
  const sun = new DirectionalLight("sun", new Vector3(-0.4, -1, 0.5), scene);
  sun.intensity = 1.6;
  // A warm light by the chest shows off the normal and metal maps.
  const lamp = new PointLight("lamp", new Vector3(-0.3, 3.2, -4.4), scene);
  lamp.diffuse = new Color3(1, 0.69, 0.37);
  lamp.intensity = 6;

  const hud = new SpikeHud(
    "Spike S3 · Asset pipeline",
    "Can a Blender model reach the browser compressed?",
    [
      "Click to look",
      "WASD move",
      "Shift hurry",
      "C crouch",
      "B auto-walk",
      "R reset",
      "F2 hide panel",
      "F3 stats",
    ],
  );
  hud.addCheck("loaded", "Loads the optimised .glb (meshopt geometry, KTX2 textures)");
  hud.addCheck("budget", "File within 3 MB");
  hud.addCheck("materials", "Textured materials have colour, normal, ORM and occlusion maps");
  hud.addCheck("gpuCompressed", "Every texture stays compressed on the GPU");
  hud.addCheck("level", "col_, ladder_, spawn_ and patrol_ nodes build without warnings");
  hud.addCheck("route", "Bot walks the patrol_ route: stairs, deck, mound, ladder; no snags");
  new PerfOverlay(engine, scene);

  // Fetch the bytes ourselves to measure size and read the glTF JSON before loading.
  const file = params.get("file") ?? DEFAULT_FILE;
  const started = performance.now();
  const response = await fetch(file);
  if (!response.ok) {
    hud.showReport(
      `FAIL: ${file} not found (${response.status}). Run npm run export && npm run assets.`,
      false,
    );
    return;
  }
  const bytes = new Uint8Array(await response.arrayBuffer());
  const glb = readGlbInfo(bytes);
  const container = await LoadAssetContainerAsync(bytes, scene, { pluginExtension: ".glb" });
  container.addAllToScene();
  const level = buildLevel(scene, [...container.transformNodes, ...container.meshes]);
  await scene.whenReadyAsync();
  const loadMs = performance.now() - started;

  // Skip the loader's placeholder for meshes without a material (the hidden col_ boxes).
  const materials = container.materials.filter(
    (m): m is PBRMaterial => m instanceof PBRMaterial && !m.name.startsWith("__GLTFLoader"),
  );
  const textureList = (m: PBRMaterial) =>
    (
      [
        ["colour", m.albedoTexture],
        ["normal", m.bumpTexture],
        ["ORM", m.metallicTexture],
        ["occlusion", m.ambientTexture],
      ] as [string, BaseTexture | null][]
    ).filter((entry): entry is [string, BaseTexture] => entry[1] !== null);
  const result: S3Result = {
    file,
    bytes: bytes.byteLength,
    loadMs,
    glb,
    triangles: container.meshes.reduce(
      (sum, mesh) => sum + (mesh.isVisible ? mesh.getTotalIndices() / 3 : 0),
      0,
    ),
    materials: materials.map((m) => ({
      name: m.name,
      textures: textureList(m).map(([slot]) => slot),
      formats: textureList(m).map(([, t]) => textureFormatName(t.getInternalTexture()?.format)),
    })),
    colliders: level.colliders,
    ladders: level.ladders.length,
    warnings: level.warnings,
    snags: 0,
  };
  (window as unknown as { spikeResult: S3Result }).spikeResult = result;
  for (const warning of level.warnings) console.warn(`[S3] ${warning}`);

  hud.check(
    "loaded",
    glb.extensionsUsed.includes("EXT_meshopt_compression") &&
      glb.extensionsUsed.includes("KHR_texture_basisu"),
  );
  hud.check("budget", bytes.byteLength <= MAX_BYTES);
  hud.check(
    "materials",
    TEXTURED.every((name) => result.materials.find((m) => m.name === name)?.textures.length === 4),
  );
  hud.check(
    "gpuCompressed",
    result.materials.length > 0 &&
      result.materials.every((m) => m.formats.every((f) => f !== "uncompressed")),
  );
  const route: Waypoint[] = (level.patrols.get("bot") ?? []).map((node) => ({
    x: node.position.x,
    z: node.position.z,
    y: node.extras.reach === true ? node.position.y : undefined,
  }));
  const spawn = level.spawns.get("player");
  hud.check(
    "level",
    level.warnings.length === 0 && !!spawn && level.ladders.length === 1 && route.length > 0,
  );

  const camera = new UniversalCamera("eye", Vector3.Zero(), scene);
  camera.fovMode = Camera.FOVMODE_HORIZONTAL_FIXED;
  camera.fov = (80 * Math.PI) / 180;
  camera.minZ = 0.05;
  scene.activeCamera = camera;

  const bus = new EventBus<GameEvents>();
  const keyboard = new KeyboardMouseInput(canvas, 0.0022);
  const start = spawn?.position ?? new Vector3(0, 0, 0);
  const player = new PlayerController(scene, camera, keyboard, start, bus);
  player.yaw = spawn?.yaw ?? 0;
  for (const ladder of level.ladders) player.addLadder(ladder);
  if (import.meta.env.DEV)
    (window as unknown as { spike: unknown }).spike = { scene, player, level };

  const snags = new SnagDetector();
  const kb = (n: number) => `${(n / 1024).toFixed(0)} KB`;
  scene.onAfterRenderObservable.add(() => {
    const dt = Math.min(engine.getDeltaTime() / 1000, 1 / 30);
    // The test room has no walls across the route, so any stop while moving is a snag.
    snags.update({
      dt,
      supported: player.supported,
      climbing: player.climbing,
      wishSpeed: player.wishSpeed,
      speed: player.speed,
      blockedAhead: false,
    });
    result.snags = snags.count;
    const feet = player.feet;
    hud.setReadout([
      `${file} · ${kb(result.bytes)} · loaded and ready in ${loadMs.toFixed(0)} ms`,
      `extensions ${glb.extensionsUsed.join(", ") || "none"}`,
      `images ${glb.imageTypes.join(", ") || "none"} · ${result.triangles.toLocaleString()} triangles`,
      ...result.materials.map(
        (m) =>
          `${m.name}: ${m.textures.join(" ") || "factors only"} ${m.formats.length ? `→ ${[...new Set(m.formats)].join("/")}` : ""}`,
      ),
      `colliders ${level.colliders.map((c) => c.shape).join(" ")} · ladders ${level.ladders.length} · route ${route.length} nodes`,
      ...level.warnings.map((w) => `⚠ ${w}`),
      `feet ${feet.x.toFixed(2)}, ${feet.y.toFixed(2)}, ${feet.z.toFixed(2)}${player.climbing ? " · climbing" : ""} · snags ${snags.count}`,
    ]);
  });

  const reset = () => {
    player.input = keyboard;
    player.teleport(start, spawn?.yaw ?? 0);
    player.pitch = 0;
  };

  const startBot = () => {
    reset();
    snags.reset();
    const bot = new WaypointBot(route, (report) => {
      result.bot = report;
      player.input = keyboard;
      const pass = report.finished && snags.count === 0;
      hud.check("route", pass);
      const text = [
        pass ? "PASS: bot walked the Blender route with no snags" : "FAIL: see below",
        `time ${report.seconds.toFixed(1)} s · snags ${snags.count}`,
        report.stuckAt.length
          ? `stuck at waypoints ${report.stuckAt.join(", ")}`
          : "reached every waypoint",
      ].join("\n");
      hud.showReport(text, pass);
      console.info(`[S3] ${text.replace(/\n/g, " | ")}`);
    });
    bot.attach(player);
    player.input = bot;
  };

  window.addEventListener("keydown", (e) => {
    if (e.code === "KeyR") reset();
    if (e.code === "KeyB") startBot();
  });

  if (params.get("auto") === "1") startBot();
  runRenderLoop(engine, () => scene.render(), renderStallNotice);
}
