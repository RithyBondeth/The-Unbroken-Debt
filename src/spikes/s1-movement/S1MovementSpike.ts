import type { WebGPUEngine } from "@babylonjs/core/Engines/webgpuEngine";
import { Scene } from "@babylonjs/core/scene";
import { UniversalCamera } from "@babylonjs/core/Cameras/universalCamera";
import { Camera } from "@babylonjs/core/Cameras/camera";
import { HemisphericLight } from "@babylonjs/core/Lights/hemisphericLight";
import { DirectionalLight } from "@babylonjs/core/Lights/directionalLight";
import { PhysicsRaycastResult } from "@babylonjs/core/Physics/physicsRaycastResult";
import type { PhysicsEngine } from "@babylonjs/core/Physics/v2/physicsEngine";
import { Color3, Color4 } from "@babylonjs/core/Maths/math.color";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { EventBus } from "../../core/EventBus";
import type { GameEvents } from "../../core/events";
import { enablePhysics } from "../../core/Physics";
import { KeyboardMouseInput } from "../../player/InputSource";
import { PlayerController } from "../../player/PlayerController";
import { PerfOverlay } from "../../debug/PerfOverlay";
import { SpikeHud } from "../SpikeHud";
import { buildCourse, type Zone } from "./course";
import { SnagDetector } from "./SnagDetector";
import { WaypointBot, type BotReport } from "./WaypointBot";
import { runRenderLoop } from "../../render/renderLoop";
import { renderStallNotice } from "../../ui/html/RenderStallNotice";

/** Results exposed for automated checks (`window.spikeResult`). */
export interface S1Result {
  snags: number;
  steps: number;
  bot?: BotReport;
}

/**
 * Spike S1 (Development Plan, section 2.2): does first-person movement feel
 * right on raised floors, stairs and ladders, with no snagging on 1 cm floor gaps?
 * URL: `?spike=s1` (play) or `?spike=s1&auto=1` (the bot walks the course).
 */
export async function runS1(engine: WebGPUEngine, params: URLSearchParams): Promise<void> {
  const canvas = engine.getRenderingCanvas() as HTMLCanvasElement;
  const scene = new Scene(engine);
  scene.clearColor = new Color4(0.55, 0.62, 0.7, 1);
  await enablePhysics(scene);

  const sky = new HemisphericLight("sky", new Vector3(0.2, 1, 0.1), scene);
  sky.intensity = 0.75;
  sky.groundColor = new Color3(0.3, 0.25, 0.2);
  const sun = new DirectionalLight("sun", new Vector3(-0.4, -1, 0.3), scene);
  sun.intensity = 0.6;

  const course = buildCourse(scene);

  const camera = new UniversalCamera("eye", Vector3.Zero(), scene);
  camera.fovMode = Camera.FOVMODE_HORIZONTAL_FIXED;
  camera.fov = (80 * Math.PI) / 180;
  scene.activeCamera = camera;

  const bus = new EventBus<GameEvents>();
  const keyboard = new KeyboardMouseInput(canvas, 0.0022);
  const player = new PlayerController(scene, camera, keyboard, course.spawn, bus);
  player.yaw = course.spawnYaw;
  for (const ladder of course.ladders) player.addLadder(ladder);

  const hud = new SpikeHud(
    "Spike S1 · First-person controller",
    "Does movement feel right on raised floors, stairs and ladders?",
    [
      "Click to look",
      "WASD move",
      "Shift hurry",
      "C crouch",
      "H head-bob on/off",
      "R reset",
      "B auto-walk",
      "F2 hide panel",
      "F3 stats",
    ],
  );
  hud.addCheck("floor", "Walk 10 m on the gapped plank floor");
  hud.addCheck("frontStairs", "Climb the front stairs (20 cm steps)");
  hud.addCheck("backStairs", "Use the steep back stairs (25 cm steps)");
  hud.addCheck("lowPassage", "Crouch through the low passage (1.25 m)");
  hud.addCheck("granary", "Climb the ladder to the granary");
  hud.addCheck("plankPad", "Cross the plank stress pad");
  hud.addCheck("noSnags", "No snags (checked after the course is done)");
  new PerfOverlay(engine, scene);

  const result: S1Result = { snags: 0, steps: 0 };
  (window as unknown as { spikeResult: S1Result }).spikeResult = result;
  if (import.meta.env.DEV) (window as unknown as { spike: unknown }).spike = { scene, player };
  bus.on("player:step", () => result.steps++);

  // Snag detection runs after the controller has moved this frame.
  const snags = new SnagDetector();
  const physics = scene.getPhysicsEngine() as PhysicsEngine;
  const ray = new PhysicsRaycastResult();
  const from = new Vector3();
  const to = new Vector3();
  let floorDistance = 0;
  let lastSnag = "";

  const inside = (p: Vector3, z: Zone) =>
    p.x >= z.min.x &&
    p.x <= z.max.x &&
    p.y >= z.min.y &&
    p.y <= z.max.y &&
    p.z >= z.min.z &&
    p.z <= z.max.z;

  scene.onAfterRenderObservable.add(() => {
    const dt = Math.min(engine.getDeltaTime() / 1000, 1 / 30);
    const feet = player.feet;

    // Is something directly ahead (a wall), so that stopping is expected?
    const wish = player.wishVelocity;
    const wishSpeed = player.wishSpeed;
    let blocked = false;
    if (wishSpeed > 0) {
      const reach = player.config.radius + 0.3;
      const height = player.stance === "crouch" ? 0.7 : 0.9;
      from.set(feet.x, feet.y + height, feet.z);
      to.set(
        feet.x + (wish.x / wishSpeed) * reach,
        feet.y + height,
        feet.z + (wish.z / wishSpeed) * reach,
      );
      physics.raycastToRef(from, to, ray);
      blocked = ray.hasHit;
    }
    const snagged = snags.update({
      dt,
      supported: player.supported,
      climbing: player.climbing,
      wishSpeed,
      speed: player.speed,
      blockedAhead: blocked,
    });
    if (snagged) {
      lastSnag = `${feet.x.toFixed(2)}, ${feet.y.toFixed(2)}, ${feet.z.toFixed(2)}`;
      console.warn(`[S1] snag at ${lastSnag}`);
    }
    result.snags = snags.count;

    if (inside(feet, course.zones.houseFloor) && player.supported)
      floorDistance += player.speed * dt;
    if (floorDistance >= 10) hud.check("floor");
    for (const id of ["frontStairs", "backStairs", "lowPassage", "granary", "plankPad"] as const) {
      if (inside(feet, course.zones[id])) hud.check(id);
    }
    const allDone = [
      "floor",
      "frontStairs",
      "backStairs",
      "lowPassage",
      "granary",
      "plankPad",
    ].every((id) => hud.isChecked(id));
    hud.check("noSnags", allDone && snags.count === 0);

    hud.setReadout([
      `feet ${feet.x.toFixed(2)}, ${feet.y.toFixed(2)}, ${feet.z.toFixed(2)}`,
      `speed ${player.speed.toFixed(2)} m/s · ${player.stance}${player.climbing ? " · climbing" : ""}${player.supported ? "" : " · airborne"}`,
      `plank floor walked ${floorDistance.toFixed(1)} m`,
      `snags ${snags.count}${lastSnag ? ` (last at ${lastSnag})` : ""} · footsteps ${result.steps}`,
      `head-bob ${player.headBobEnabled ? "on" : "off"}${keyboard.pointerLocked ? "" : " · click the view to look around"}`,
    ]);
  });

  const reset = () => {
    player.input = keyboard;
    player.teleport(course.spawn, course.spawnYaw);
    player.pitch = 0;
  };

  const startBot = () => {
    reset();
    snags.reset();
    floorDistance = 0;
    const bot = new WaypointBot(course.route, (report) => {
      result.bot = report;
      player.input = keyboard;
      const pass = report.finished && snags.count === 0;
      const text = [
        pass ? "PASS: bot finished the course with no snags" : "FAIL: see below",
        `time ${report.seconds.toFixed(1)} s · snags ${snags.count}`,
        report.stuckAt.length
          ? `stuck at waypoints ${report.stuckAt.join(", ")}`
          : "reached every waypoint",
      ].join("\n");
      hud.showReport(text, pass);
      console.info(`[S1] ${text.replace(/\n/g, " | ")}`);
    });
    bot.attach(player);
    player.input = bot;
  };

  window.addEventListener("keydown", (e) => {
    if (e.code === "KeyR") reset();
    if (e.code === "KeyH") player.headBobEnabled = !player.headBobEnabled;
    if (e.code === "KeyB") startBot();
  });

  if (params.get("auto") === "1") startBot();
  runRenderLoop(engine, () => scene.render(), renderStallNotice);
}
