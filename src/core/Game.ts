import { FirstPersonHands } from "../player/FirstPersonHands";
import type { WebGPUEngine } from "@babylonjs/core/Engines/webgpuEngine";
import { Scene } from "@babylonjs/core/scene";
import { UniversalCamera } from "@babylonjs/core/Cameras/universalCamera";
import { Camera } from "@babylonjs/core/Cameras/camera";
import { PointLight } from "@babylonjs/core/Lights/pointLight";
import { Color3, Color4 } from "@babylonjs/core/Maths/math.color";
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
import { keepLightBudgets } from "../render/lightBudget";
import { installSoftLampFalloff } from "../render/softLampFalloff";
import { renderStallNotice } from "../ui/html/RenderStallNotice";
import { Atmosphere } from "../render/Atmosphere";
import { GatedInput, KeyboardMouseInput } from "../player/InputSource";
import { PlayerController } from "../player/PlayerController";
import { FallGuard } from "../player/FallGuard";
import { PerfOverlay } from "../debug/PerfOverlay";
import { AudioSystem } from "../audio/AudioSystem";
import { Footsteps } from "../audio/Footsteps";
import { Inventory } from "../systems/inventory/Inventory";
import { Interaction } from "../systems/interaction/Interaction";
import { SaveStore } from "../systems/saves/SaveStore";
import { Sketchbook } from "../ui/diegetic/Sketchbook";
import { loadSketchbookFonts } from "../ui/diegetic/fonts";
import { SECTIONS } from "../ui/diegetic/sketchbookContent";
import {
  Hints,
  SatchelPanel,
  SaveIndicator,
  ScreenFade,
  Subtitles,
  type SatchelEntry,
} from "../ui/html/StoryUi";
import { EP1_GRADE } from "../episodes/ep1/data/grade";
import { EP1_SKETCHBOOK } from "../episodes/ep1/data/sketchbook";
import { ITEMS } from "../episodes/ep1/data/items";
import { Prologue } from "../episodes/ep1/prologue/Prologue";
import { ActOne } from "../episodes/ep1/act1/ActOne";
import type { SaveData } from "../systems/saves/SaveData";

/** A part of an episode with its own area and script (the prologue, an act). */
interface Section {
  load(): Promise<void>;
  begin(): Promise<void>;
  warmup?(): Promise<void>;
}

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
  readonly hands: FirstPersonHands;
  readonly preset: QualityPreset;
  readonly input: KeyboardMouseInput;
  /** What the player controller reads: the keyboard and mouse, as the story allows. */
  readonly gated: GatedInput;
  readonly inventory = new Inventory(this.bus);
  readonly interaction: Interaction;
  readonly hints = new Hints();
  readonly subtitles = new Subtitles();
  readonly fade = new ScreenFade();
  readonly satchel = new SatchelPanel();
  private readonly saveIndicator = new SaveIndicator();
  readonly saves = new SaveStore((saving) => this.saveIndicator.set(saving));
  /** Null if the browser refused to create audio. */
  audio: AudioSystem | null = null;
  /** Sora's footsteps; null without audio. */
  footsteps: Footsteps | null = null;
  /** Exists once the game has started. */
  sketchbook: Sketchbook | null = null;
  /** The lamp from the save being resumed, if any (the act restores it). */
  savedLamp: SaveData["lamp"] | null = null;
  resumedSave: SaveData | null = null;
  /** A scripted moment has Sora's hands: nothing can be used, opened or read. */
  cutscene = false;
  /** The live threat keeps notebook / inventory menus out of the encounter. */
  threatActive = false;
  hiding = false;
  pipeline!: PostPipeline;
  atmosphere!: Atmosphere;
  player!: PlayerController;
  /** Puts Sora back on solid ground if she ever leaves the world (the area may set walls). */
  readonly fallGuard = new FallGuard();
  private readonly feetNow = new Vector3();
  private resolution!: DynamicResolution;
  private inspection: Vector3 | null = null;
  private inspectionRadius = 0.31;
  private readonly normalFov = (75 * Math.PI) / 180;

  get inspecting(): boolean {
    return this.inspection !== null;
  }

  /** Lean in optically to a small object; mouse look and E still work. */
  inspectObject(at: Vector3, radius = 0.31): void {
    this.inspection = at.clone();
    this.inspectionRadius = radius;
    this.gated.inspecting = true;
    const from = this.camera.globalPosition;
    const dx = at.x - from.x,
      dz = at.z - from.z;
    this.player.yaw = Math.atan2(dx, dz);
    this.player.pitch = Math.atan2(from.y - at.y, Math.hypot(dx, dz));
  }

  stopInspecting(): void {
    this.inspection = null;
    this.gated.inspecting = false;
  }

  constructor(
    private readonly engine: WebGPUEngine,
    device: DeviceProfile,
  ) {
    this.preset = getPreset(device.quality);
    // Before any material compiles: the falloff Sora's lamp uses (VillageLights).
    installSoftLampFalloff();
    this.scene = new Scene(engine);
    this.scene.clearColor = new Color4(0.01, 0.01, 0.012, 1);
    this.scene.skipPointerMovePicking = true;
    keepLightBudgets(this.scene);
    this.camera = new UniversalCamera("eye", new Vector3(0, 1.6, 0), this.scene);
    this.camera.fovMode = Camera.FOVMODE_HORIZONTAL_FIXED;
    // Art Bible section 4: 75° by default.
    this.camera.fov = (75 * Math.PI) / 180;
    this.camera.minZ = 0.05;
    this.camera.maxZ = 60;
    this.scene.activeCamera = this.camera;
    this.hands = new FirstPersonHands(this.scene, this.camera);
    this.input = new KeyboardMouseInput(engine.getRenderingCanvas() as HTMLCanvasElement, 0.0022);
    this.gated = new GatedInput(this.input);
    this.interaction = new Interaction(this.scene, this.camera, this.bus);
    window.addEventListener("keydown", (e) => this.press(e));
    this.bus.on("interact:use", () => {
      if (!this.cutscene && !this.hiding) this.hands.animate("reach");
    });
    this.bus.on("inventory:changed", () => {
      if (this.satchel.isOpen) this.satchel.open(this.satchelEntries());
    });
  }

  /** Seconds since the last frame, capped so a stall never jumps the world. */
  get deltaSeconds(): number {
    return Math.min(this.engine.getDeltaTime() / 1000, 0.1);
  }

  /** Visual review fixtures can omit audio initialization; normal play enables it. */
  async start({ audio = true }: { audio?: boolean } = {}): Promise<void> {
    await Promise.all([enablePhysics(this.scene), loadSketchbookFonts(), this.hands.load()]);
    this.audio = audio
      ? await AudioSystem.create(undefined, { hideUnmuteButton: true }).catch((error: unknown) => {
          console.warn("[Game] no audio", error);
          return null;
        })
      : null;
    this.audio?.attachListener(this.camera);
    if (this.audio) this.footsteps = await Footsteps.load(this.audio, this.bus);
    this.resolution = new DynamicResolution(this.engine, this.preset);
    const section = await this.chooseSection();
    await section.load();
    this.pipeline = createPostPipeline(this.scene, this.camera, this.preset);
    this.atmosphere = new Atmosphere(this.scene, this.pipeline.main, EP1_GRADE, this.camera);
    this.createSketchbook();
    if (section.warmup) {
      await this.fade.to(1, 0);
      await section.warmup();
    }
    if (import.meta.env.DEV) new PerfOverlay(this.engine, this.scene);
    this.scene.onBeforeRenderObservable.add(() => this.update());
    void section.begin();
    runRenderLoop(this.engine, () => this.scene.render(), renderStallNotice);
  }

  /**
   * Where to start: `?continue` resumes the autosave (the prologue reloads into
   * it at CP1), `?start=act1` jumps there with the starting kit for testing.
   */
  private async chooseSection(): Promise<Section> {
    const params = new URLSearchParams(location.search);
    const resumed = params.has("continue") ? (await this.saves.load("autosave")).save : null;
    if (resumed) {
      this.restore(resumed);
      if (resumed.checkpoint === "CP0") return new Prologue(this);
    } else if (params.get("start") === "act1") {
      for (const [item, n] of Object.entries({
        satchel: 1,
        sketchbook: 1,
        matches: 10,
        lamp: 1,
        letters: 1,
      }))
        this.inventory.add(item, n);
      this.flags.set("sketchbook.written", "SB-01");
    } else return new Prologue(this);
    return new ActOne(this);
  }

  /** Puts a save's story state back (the area and position come from its checkpoint). */
  private restore(save: SaveData): void {
    this.resumedSave = save;
    this.flags.load(save.flags);
    this.flags.set("ep1.clock", save.clock);
    this.inventory.load(save.inventory);
    this.savedLamp = save.lamp;
  }

  /** Puts Sora at `feet`, facing `yaw`. */
  spawnPlayer(feet = Vector3.Zero(), yaw = 0): void {
    this.player = new PlayerController(this.scene, this.camera, this.gated, feet, this.bus);
    this.player.yaw = yaw;
    this.fallGuard.reset(feet);
  }

  /** The sketchbook in Sora's hands (S5), lit by its own reading light. */
  private createSketchbook(): void {
    const height = this.preset.name === "low" ? 1024 : 1536;
    const sketchbook = new Sketchbook(this.scene, EP1_SKETCHBOOK, height, this.camera);
    this.sketchbook = sketchbook;
    const written = this.flags.get<string>("sketchbook.written", "");
    if (written) sketchbook.restore(written.split(","));
    // Drawn after the room with its own depth, so the book never sinks into a wall.
    sketchbook.book.setRenderingGroup(1);
    this.scene.setRenderingAutoClearDepthStencil(1, true, true, true);
    // The room's lights would blow the paper out at 30 cm (S5): one soft light of its own.
    const reading = new PointLight("reading_light", new Vector3(-0.3, -0.12, 0.12), this.scene);
    reading.parent = this.camera;
    reading.diffuse = new Color3(1, 0.84, 0.64);
    reading.intensity = 0.26;
    reading.includedOnlyMeshes = sketchbook.book.meshes;
    for (const light of this.scene.lights)
      if (light !== reading) light.excludedMeshes.push(...sketchbook.book.meshes);
  }

  private update(): void {
    this.guardFall();
    const book = this.sketchbook;
    book?.update(this.deltaSeconds);
    if (book?.isOpen || book?.isBusy) this.stopInspecting();
    this.holdResolution(book?.isOpen || book?.isBusy || this.inspecting ? 0.85 : null);
    const distance = this.inspection
      ? Vector3.Distance(this.camera.globalPosition, this.inspection)
      : 0;
    const fov = this.inspection
      ? Math.max(
          0.4,
          Math.min(
            1.2,
            2 *
              Math.atan(
                (this.inspectionRadius *
                  Math.max(1, this.engine.getRenderWidth() / this.engine.getRenderHeight())) /
                  distance,
              ),
          ),
        )
      : this.normalFov;
    this.camera.fov += (fov - this.camera.fov) * (1 - Math.exp(-this.deltaSeconds * 8));
    this.gated.reading = (book?.isOpen || book?.isBusy) ?? false;
    this.interaction.active =
      !this.cutscene && !this.hiding && !this.gated.reading && !this.satchel.isOpen;
    this.interaction.update();
    const documentOpen = !!document.querySelector(".document-reader:not([hidden])");
    this.hands.update(
      this.deltaSeconds,
      this.cutscene || this.hiding || this.satchel.isOpen || documentOpen,
      book?.book.root ?? null,
      this.player?.speed ?? 0,
    );
  }

  /** Back to the last solid footing, behind a brief black, if Sora has dropped out of the world. */
  private guardFall(): void {
    if (!this.player) return;
    const feet = this.player.feetToRef(this.feetNow);
    const respawn = this.fallGuard.update(this.deltaSeconds, feet, this.player.supported);
    if (!respawn) return;
    console.warn(`[Game] fell out of the world at ${feet.toString()}; back to ${respawn.toString()}`);
    this.player.teleport(respawn, this.player.yaw);
    void this.fade.to(1, 0).then(() => this.fade.to(0, 0.8));
  }

  /** E uses, Tab opens the satchel, Q the sketchbook; A/D and 1–5 turn its pages. */
  private press(e: KeyboardEvent): void {
    if (e.code === "Tab") e.preventDefault();
    if (e.repeat) return;
    if (["Escape", "KeyW", "KeyA", "KeyS", "KeyD", "KeyQ", "Tab"].includes(e.code))
      this.stopInspecting();
    const book = this.sketchbook;
    if (e.code === "KeyE" && this.interaction.use()) this.hints.performed("hint.use");
    if (e.code === "Tab") this.toggleSatchel();
    if (e.code === "KeyQ") this.toggleSketchbook();
    if (!book?.isOpen) return;
    if (e.code === "KeyA" || e.code === "KeyD") book.turn(e.code === "KeyD" ? 1 : -1);
    const digit = Number(e.code.replace("Digit", ""));
    if (e.code.startsWith("Digit") && digit >= 1 && digit <= SECTIONS.length)
      book.goToSection(SECTIONS[digit - 1].id);
  }

  toggleSatchel(): void {
    if (this.cutscene || this.threatActive || this.hiding || !this.inventory.has("satchel")) return;
    this.hints.performed("hint.satchel");
    if (this.satchel.isOpen) return this.satchel.close();
    if (this.sketchbook?.isOpen) this.sketchbook.toggle();
    this.satchel.open(this.satchelEntries());
  }

  toggleSketchbook(): void {
    if (
      this.cutscene ||
      this.threatActive ||
      this.hiding ||
      !this.sketchbook ||
      !this.inventory.has("sketchbook")
    )
      return;
    this.hints.performed("hint.sketchbook");
    this.satchel.close();
    this.sketchbook.toggle();
  }

  private satchelEntries(): SatchelEntry[] {
    return this.inventory
      .list()
      .filter(([id]) => ITEMS[id])
      .map(([id, n]) => ({
        name: ITEMS[id].name,
        note: ITEMS[id].note?.replace("{n}", String(n)),
      }));
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
