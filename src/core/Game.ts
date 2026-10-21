import type { WebGPUEngine } from "@babylonjs/core/Engines/webgpuEngine";
import { Scene } from "@babylonjs/core/scene";
import { UniversalCamera } from "@babylonjs/core/Cameras/universalCamera";
import { Camera } from "@babylonjs/core/Cameras/camera";
import type { PointLight } from "@babylonjs/core/Lights/pointLight";
import { Color4 } from "@babylonjs/core/Maths/math.color";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { EventBus } from "./EventBus";
import { Flags } from "./Flags";
import type { GameEvents } from "./events";
import { enablePhysics } from "./Physics";
import type { DeviceProfile } from "../render/DeviceProfile";
import { getPreset, type QualityPreset } from "../render/QualityPresets";
import { createPostPipeline, type PostPipeline } from "../render/RenderSetup";
import { DynamicResolution } from "../render/DynamicResolution";
import { runRenderLoop } from "../render/renderLoop";
import { renderStallNotice } from "../ui/html/RenderStallNotice";
import { Atmosphere } from "../render/Atmosphere";
import { KeyboardMouseInput } from "../player/InputSource";
import { PlayerController } from "../player/PlayerController";
import { PerfOverlay } from "../debug/PerfOverlay";
import { EP1_GRADE } from "../episodes/ep1/data/grade";
import { Prologue } from "../episodes/ep1/prologue/Prologue";

/**
 * Owns the engine, the scene, the shared event bus and flags, the camera and
 * player, the post-processing and the render loop, then hands over to the
 * current episode section. Phase 2: boots straight into the Episode 1 prologue.
 */
export class Game {
  readonly bus = new EventBus<GameEvents>();
  readonly flags = new Flags(this.bus);
  readonly scene: Scene;
  readonly camera: UniversalCamera;
  readonly preset: QualityPreset;
  readonly input: KeyboardMouseInput;
  pipeline!: PostPipeline;
  atmosphere!: Atmosphere;
  player!: PlayerController;
  private resolution!: DynamicResolution;

  constructor(
    private readonly engine: WebGPUEngine,
    device: DeviceProfile,
  ) {
    this.preset = getPreset(device.quality);
    this.scene = new Scene(engine);
    this.scene.clearColor = new Color4(0.01, 0.01, 0.012, 1);
    this.scene.skipPointerMovePicking = true;
    this.camera = new UniversalCamera("eye", new Vector3(0, 1.6, 0), this.scene);
    this.camera.fovMode = Camera.FOVMODE_HORIZONTAL_FIXED;
    // Art Bible section 4: 75° by default.
    this.camera.fov = (75 * Math.PI) / 180;
    this.camera.minZ = 0.05;
    this.camera.maxZ = 60;
    this.scene.activeCamera = this.camera;
    this.input = new KeyboardMouseInput(engine.getRenderingCanvas() as HTMLCanvasElement, 0.0022);
  }

  /** Seconds since the last frame, capped so a stall never jumps the world. */
  get deltaSeconds(): number {
    return Math.min(this.engine.getDeltaTime() / 1000, 0.1);
  }

  async start(): Promise<void> {
    await enablePhysics(this.scene);
    this.resolution = new DynamicResolution(this.engine, this.preset);
    const prologue = new Prologue(this);
    await prologue.load();
    this.pipeline = createPostPipeline(this.scene, this.camera, this.preset);
    this.atmosphere = new Atmosphere(this.scene, this.pipeline.main, EP1_GRADE, this.camera);
    if (import.meta.env.DEV) new PerfOverlay(this.engine, this.scene);
    prologue.begin();
    if (import.meta.env.DEV) (window as unknown as { prologue: Prologue }).prologue = prologue;
    runRenderLoop(this.engine, () => this.scene.render(), renderStallNotice);
  }

  /** Puts Sora at `feet`, facing `yaw`. */
  spawnPlayer(feet = Vector3.Zero(), yaw = 0): void {
    this.player = new PlayerController(this.scene, this.camera, this.input, feet, this.bus);
    this.player.yaw = yaw;
  }

  /** Lights the volumetric fog should glow around. */
  addFlameLights(...lights: PointLight[]): void {
    this.pipeline.fog?.lights.push(...lights);
  }

  /** While text must stay sharp (the sketchbook), hold the render scale up (S5). */
  holdResolution(scale: number | null): void {
    this.resolution.holdAtLeast(scale);
  }
}
