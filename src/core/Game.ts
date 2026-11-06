import { loadNotebookPortraits } from "../ui/notebook/notebookPortraits";
import {
  notebookContent as buildNotebookContent,
  type NotebookSnapshot,
} from "../ui/notebook/notebookContent";
import { FirstPersonHands } from "../player/FirstPersonHands";
import type { WebGPUEngine } from "@babylonjs/core/Engines/webgpuEngine";
import { Scene } from "@babylonjs/core/scene";
import { keepSurfaceDetail } from "../render/surfaceDetail";
import { UniversalCamera } from "@babylonjs/core/Cameras/universalCamera";
import { Camera } from "@babylonjs/core/Cameras/camera";
import { PointLight } from "@babylonjs/core/Lights/pointLight";
import { Color3, Color4 } from "@babylonjs/core/Maths/math.color";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { EventBus } from "./EventBus";
import { Flags } from "./Flags";
import type { GameEvents } from "./events";
import { enablePhysics } from "./physics";
import type { DeviceProfile } from "../render/DeviceProfile";
import { getPreset, type QualityPreset } from "../render/qualityPresets";
import { createPostPipeline, type PostPipeline } from "../render/renderSetup";
import { DynamicResolution } from "../render/DynamicResolution";
import { runRenderLoop } from "../render/renderLoop";
import { keepLightBudgets } from "../render/lightBudget";
import { installSoftLampFalloff } from "../render/softLampFalloff";
import { renderStallNotice } from "../ui/html/renderStallNotice";
import { Atmosphere } from "../render/Atmosphere";
import { WindState } from "../render/wind";
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
import { NIGHT_GRADE } from "../render/nightGrade";
import { EP1_SKETCHBOOK } from "../episodes/ep1/data/sketchbook";
import { ITEMS } from "../episodes/ep1/data/items";
import type { ItemInfo } from "../systems/inventory/Inventory";
import { Prologue } from "../episodes/ep1/prologue/Prologue";
import { ActOne } from "../episodes/ep1/act1/ActOne";
import type { SaveData } from "../systems/saves/SaveData";
import { Checkpoints, checkpointName } from "../systems/saves/Checkpoints";
import { NotebookReader } from "../ui/html/NotebookReader";
import { PauseMenu } from "../ui/html/PauseMenu";
import { storyClock } from "../ui/html/StoryUi";
import { TaxiRide } from "../episodes/ep1/travel/TaxiRide";
import { WhisperingPagoda } from "../episodes/ep2/WhisperingPagoda";
import { PagodaProgress, enterPagoda } from "../episodes/ep2/PagodaProgress";
import { EP2_SKETCHBOOK, pagodaNotebook } from "../episodes/ep2/data/notebook";
import { EP2_ITEMS } from "../episodes/ep2/data/pagoda";
import { DrownedVillage } from "../episodes/ep3/DrownedVillage";
import { VillageProgress, enterVillage } from "../episodes/ep3/VillageProgress";
import { EP3_SKETCHBOOK, villageNotebook } from "../episodes/ep3/data/notebook";
import { EP3_ITEMS } from "../episodes/ep3/data/village";

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
  readonly notebook: NotebookReader;
  readonly hints = new Hints();
  readonly subtitles = new Subtitles();
  readonly fade = new ScreenFade();
  readonly satchel = new SatchelPanel();
  private readonly saveIndicator = new SaveIndicator();
  readonly saves: SaveStore;
  readonly checkpoints = new Checkpoints(() => this.saves);
  /** Null if the browser refused to create audio. */
  audio: AudioSystem | null = null;
  /** Sora's footsteps; null without audio. */
  footsteps: Footsteps | null = null;
  /** Exists once the game has started. */
  sketchbook: Sketchbook | null = null;
  /** The lamp from the save being resumed, if any (the act restores it). */
  savedLamp: SaveData["lamp"] | null = null;
  resumedSave: SaveData | null = null;
  /** Escape has frozen the game under the pause menu. */
  paused = false;
  private readonly pauseMenu = new PauseMenu();
  private started = false;
  /** A scripted moment has Sora's hands: nothing can be used, opened or read. */
  cutscene = false;
  handsHidden = false;
  episode = 1;
  /** The live threat keeps notebook / inventory menus out of the encounter. */
  threatActive = false;
  hiding = false;
  pipeline!: PostPipeline;
  atmosphere!: Atmosphere;
  player!: PlayerController;
  /** The outdoor wind: sections set its strength, the story its calm and tension. */
  readonly wind = new WindState();
  /** Puts Sora back on solid ground if she ever leaves the world (the area may set walls). */
  readonly fallGuard = new FallGuard();
  private readonly feetNow = new Vector3();
  private resolution!: DynamicResolution;
  private inspection: Vector3 | null = null;
  private inspectionRadius = 0.31;
  private readonly normalFov = (75 * Math.PI) / 180;
  private debugKey = "none";
  private debugHandledKey = "none";
  private debugUse = "none";

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

  /** Freezes play for a scripted moment: closes the books and satchel, hides hints, releases the mouse. */
  enterCutscene(): void {
    this.cutscene = true;
    this.gated.holdStill = true;
    this.input.clear();
    this.stopInspecting();
    this.closeSketchbook();
    this.satchel.close();
    this.hints.hide();
    document.exitPointerLock();
  }

  stopInspecting(): void {
    this.inspection = null;
    this.gated.inspecting = false;
  }

  constructor(
    private readonly engine: WebGPUEngine,
    device: DeviceProfile,
    saveDatabase?: string,
  ) {
    this.saves = new SaveStore(
      (saving, result) => this.saveIndicator.set(saving, result),
      saveDatabase,
    );
    this.preset = getPreset(device.quality);
    // Before any material compiles: the falloff Sora's lamp uses (VillageLights).
    installSoftLampFalloff();
    this.scene = new Scene(engine);
    keepSurfaceDetail(this.scene, device.quality);
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
    const canvas = engine.getRenderingCanvas() as HTMLCanvasElement;
    canvas.tabIndex = 0;
    this.input = new KeyboardMouseInput(canvas, 0.0022);
    this.gated = new GatedInput(this.input);
    this.interaction = new Interaction(this.scene, this.camera, this.bus);
    this.notebook = new NotebookReader(this);
    // Ahead of every other key handler: while paused nothing else hears the keyboard,
    // and Escape is weighed before a reader or the wardrobe can take it.
    window.addEventListener("keydown", (e) => this.pauseKey(e), { capture: true });
    window.addEventListener("keydown", (e) => this.press(e));
    // Escape while the mouse is captured releases it before the page sees the key:
    // losing the pointer with nothing open on screen pauses too (and so does alt-tab).
    document.addEventListener("pointerlockchange", () => {
      if (document.pointerLockElement || !this.started || this.paused) return;
      setTimeout(() => {
        if (!document.pointerLockElement && !this.paused && !this.cutscene && this.nothingOpen())
          this.pause();
      }, 120);
    });
    if (import.meta.env.DEV)
      window.addEventListener(
        "keydown",
        (e) => {
          this.debugKey = `${e.code || "no code"} / ${e.key} repeat=${e.repeat}`;
        },
        { capture: true },
      );
    this.bus.on("interact:use", ({ id }) => {
      this.debugUse = id;
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
    this.atmosphere = new Atmosphere(this.scene, this.pipeline.main, NIGHT_GRADE, this.camera);
    await loadNotebookPortraits();
    this.createSketchbook();
    if (section.warmup) {
      await this.fade.to(1, 0);
      await section.warmup();
    }
    if (import.meta.env.DEV)
      new PerfOverlay(this.engine, this.scene, document.body, () => [
        `input diagnostic v1`,
        `key received: ${this.debugKey}`,
        `key handled: ${this.debugHandledKey}`,
        `last use: ${this.debugUse}`,
        `target: ${this.interaction.focus ?? "none"} active=${this.interaction.active}`,
        `page focused=${document.hasFocus()} pointer=${this.input.pointerLocked}`,
        `cutscene=${this.cutscene} reading=${this.gated.reading} satchel=${this.satchel.isOpen}`,
        ...(section instanceof Prologue ? [section.debugStatus] : []),
      ]);
    this.scene.onBeforeRenderObservable.add(() => this.update());
    void section.begin();
    this.started = true;
    // Paused, the last frame stays on screen and the world stops (scripts run on frame time).
    runRenderLoop(
      this.engine,
      () => {
        if (!this.paused) this.scene.render();
      },
      renderStallNotice,
    );
  }

  /**
   * Where to start: `?continue` resumes the autosave (the prologue reloads into
   * it at CP1), `?start=act1` jumps there with the starting kit for testing.
   */
  private async chooseSection(): Promise<Section> {
    const params = new URLSearchParams(location.search);
    if (params.get("start") === "ep3" || params.get("episode") === "3") {
      const current = (await this.saves.load("autosave")).save;
      if (current?.episode === 3) {
        this.restore(current);
        await this.checkpoints.load(current);
        return new DrownedVillage(this);
      }
      const previous =
        current?.episode === 2 && current.flags["ep2.complete"] === true
          ? current
          : (await this.saves.load("episode2")).save;
      if (previous?.episode === 2 && previous.flags["ep2.complete"] === true) {
        await this.saves.save("episode2", previous);
        this.restore(enterVillage(previous));
        return new DrownedVillage(this);
      }
      if (import.meta.env.DEV && params.get("start") === "ep3") {
        this.episode = 3;
        this.flags.set("ep3.preview", true);
        this.flags.set("ep3.checkpoint", "CP0");
        for (const [item, n] of Object.entries({
          satchel: 1,
          sketchbook: 1,
          lamp: 1,
          matches: 12,
          oil: 3,
        }))
          this.inventory.add(item, n);
        return new DrownedVillage(this);
      }
      throw new Error("Complete Episode 2 before entering The Drowned Village.");
    }
    // Production handoff requires a real completed Episode 1 save.
    if (params.get("start") === "ep2" || params.get("episode") === "2") {
      const current = (await this.saves.load("autosave")).save;
      if (current?.episode === 2) {
        this.restore(current);
        await this.checkpoints.load(current);
        return new WhisperingPagoda(this);
      }
      const previous =
        current?.episode === 1 && current.flags["ep1.complete"] === true
          ? current
          : (await this.saves.load("episode1")).save;
      if (previous?.episode === 1 && previous.flags["ep1.complete"] === true) {
        // Archive the completion before the pagoda writes its own first checkpoint.
        await this.saves.save("episode1", previous);
        this.restore(enterPagoda(previous));
        return new WhisperingPagoda(this);
      }
      if (import.meta.env.DEV && params.get("start") === "ep2") {
        this.episode = 2;
        this.flags.set("ep2.preview", true);
        this.flags.set("ep2.checkpoint", "CP0");
        for (const [item, n] of Object.entries({
          satchel: 1,
          sketchbook: 1,
          lamp: 1,
          matches: 10,
          oil: 2,
        }))
          this.inventory.add(item, n);
        return new WhisperingPagoda(this);
      }
      throw new Error("Complete Episode 1 before entering The Whispering Pagoda.");
    }
    const resumed = params.has("continue") ? (await this.saves.load("autosave")).save : null;
    if (resumed) {
      this.restore(resumed);
      await this.checkpoints.load(resumed);
      if (resumed.episode === 3) return new DrownedVillage(this);
      if (resumed.episode === 2) return new WhisperingPagoda(this);
      if (resumed.flags["ep1.travel.pending"] === true) return new TaxiRide(this);
      if (resumed.checkpoint === "CP0") return new Prologue(this);
    } else if (params.get("start") === "act1") {
      this.flags.set("ep1.checkpoint", "CP1");
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
    this.episode = save.episode;
    this.flags.load(save.flags);
    this.flags.set(`ep${save.episode}.checkpoint`, save.checkpoint);
    this.flags.set(`ep${save.episode}.clock`, save.clock);
    this.inventory.load(save.inventory);
    this.savedLamp = save.lamp;
  }

  /** Death retries restore the last safe snapshot, not the state at the catch. */
  async retryFromCheckpoint(): Promise<void> {
    this.cutscene = true;
    this.threatActive = false;
    this.gated.holdStill = true;
    this.gated.holdLook = true;
    this.stopInspecting();
    this.sketchbook?.close();
    this.satchel.close();
    this.hints.hide();
    document.exitPointerLock();
    await this.fade.to(1, 0.5);
    const last = this.checkpoints.last;
    let failed = false;
    while (true) {
      await this.fade.show({
        title: failed ? "Retry could not be saved" : "You were caught",
        body: failed
          ? "Your checkpoint is still here. Free browser storage and retry."
          : `Return to ${last ? checkpointName(last) : "your last checkpoint"}.`,
        button: "Retry checkpoint",
      });
      try {
        await this.checkpoints.prepareRetry();
        break;
      } catch {
        failed = true;
      }
    }
    const url = new URL(location.href);
    url.searchParams.set("continue", "");
    url.searchParams.delete("start");
    url.searchParams.delete("episode");
    location.replace(url.toString());
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
    const sketchbook = new Sketchbook(
      this.scene,
      this.episode === 3 ? EP3_SKETCHBOOK : this.episode === 2 ? EP2_SKETCHBOOK : EP1_SKETCHBOOK,
      height,
      this.camera,
      (written) => this.notebookContent(written),
    );
    this.sketchbook = sketchbook;
    const written = this.flags.get<string>("sketchbook.written", "");
    if (written) sketchbook.restore(written.split(","));
    // Drawn after the room with its own depth, so the book never sinks into a wall.
    sketchbook.book.setRenderingGroup(1);
    this.scene.setRenderingAutoClearDepthStencil(1, true, true, true);
    // The room's lights would blow the paper out at 30 cm (S5): one soft light of its own.
    const reading = new PointLight("reading_light", new Vector3(-0.06, 0.1, 0.08), this.scene);
    reading.parent = this.camera;
    reading.diffuse = new Color3(1, 0.84, 0.64);
    reading.intensity = 0.22;
    reading.includedOnlyMeshes = sketchbook.book.meshes;
    for (const light of this.scene.lights)
      if (light !== reading) light.excludedMeshes.push(...sketchbook.book.meshes);
  }

  private update(): void {
    this.guardFall();
    const eye = this.camera.globalPosition;
    this.wind.update(this.deltaSeconds, eye.x, eye.z);
    if (this.wind.push && this.player) {
      this.wind.push.x = this.feetNow.x;
      this.wind.push.z = this.feetNow.z;
    }
    if (
      this.notebook.isOpen &&
      (this.cutscene || this.threatActive || this.hiding || this.satchel.isOpen)
    )
      this.notebook.close();
    const book = this.sketchbook;
    if ((this.threatActive || this.hiding || this.satchel.isOpen) && book?.isRaised)
      this.closeSketchbook();
    book?.update(this.deltaSeconds);
    this.notebook.update(this.deltaSeconds);
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
    this.gated.reading = this.notebook.isOpen || ((book?.isVisible || book?.isBusy) ?? false);
    this.interaction.active =
      !this.cutscene && !this.hiding && !this.gated.reading && !this.satchel.isOpen;
    this.interaction.update();
    const documentOpen = !!document.querySelector(".document-reader:not([hidden])");
    this.hands.update(
      this.deltaSeconds,
      this.cutscene ||
        this.handsHidden ||
        this.hiding ||
        this.satchel.isOpen ||
        documentOpen ||
        this.notebook.isOpen,
      book?.book.root ?? null,
      this.player?.speed ?? 0,
      book?.turnState ?? null,
    );
  }

  /** Back to the last solid footing, behind a brief black, if Sora has dropped out of the world. */
  private guardFall(): void {
    if (!this.player) return;
    const feet = this.player.feetToRef(this.feetNow);
    const respawn = this.fallGuard.update(this.deltaSeconds, feet, this.player.supported);
    if (!respawn) return;
    console.warn(
      `[Game] fell out of the world at ${feet.toString()}; back to ${respawn.toString()}`,
    );
    this.player.teleport(respawn, this.player.yaw);
    void this.fade.to(1, 0).then(() => this.fade.to(0, 0.8));
  }

  /** No book, satchel, reader, title card or entry screen is open over the game. */
  private nothingOpen(): boolean {
    const book = this.sketchbook;
    return (
      !(book?.isVisible || book?.isBusy) &&
      !this.notebook.isOpen &&
      !this.satchel.isOpen &&
      !document.querySelector(
        ".document-reader:not([hidden]), .story-fade.waiting, .story-card.shown, .resolution:not([hidden])",
      )
    );
  }

  private pauseKey(e: KeyboardEvent): void {
    if (this.paused) {
      e.preventDefault();
      e.stopImmediatePropagation();
      if (e.code === "Escape" && !e.repeat) this.pauseMenu.back();
      return;
    }
    if (e.code !== "Escape" || e.repeat || !this.started) return;
    // Escape first steps back out of whatever has Sora's attention.
    if (this.inspecting || this.hiding || !this.nothingOpen()) return;
    e.preventDefault();
    e.stopImmediatePropagation();
    this.pause();
  }

  /** Freezes the world, its sound and its story timing under the pause menu. */
  pause(): void {
    if (this.paused || !this.started) return;
    this.paused = true;
    storyClock.paused = true;
    this.input.clear();
    this.stopInspecting();
    void (this.audio?.context as AudioContext | undefined)?.suspend?.();
    if (document.pointerLockElement) document.exitPointerLock();
    const last = this.checkpoints.last;
    this.pauseMenu.open({
      resume: () => this.resume(),
      restart: last
        ? () =>
            void this.checkpoints
              .prepareRetry()
              .then(() => this.reload(true))
              .catch(() => this.reload(true))
        : null,
      quit: () => this.reload(false),
    });
  }

  resume(): void {
    if (!this.paused) return;
    this.pauseMenu.close();
    this.paused = false;
    storyClock.paused = false;
    this.input.clear();
    void (this.audio?.context as AudioContext | undefined)?.resume?.();
    this.engine.getRenderingCanvas()?.focus({ preventScroll: true });
    // The Resume click or key is a fresh gesture: take the mouse back at once.
    if (!this.cutscene) void this.input.lockPointer();
  }

  /** Back to the last checkpoint (`?continue`), or to the title screen. */
  private reload(toCheckpoint: boolean): void {
    const url = new URL(location.href);
    url.searchParams.delete("start");
    if (toCheckpoint) url.searchParams.set("continue", "");
    else url.searchParams.delete("continue");
    location.replace(url.toString());
  }

  /** E uses, Tab opens the satchel, Q the sketchbook; A/D and 1–5 turn its pages. */
  private press(e: KeyboardEvent): void {
    if (import.meta.env.DEV) this.debugHandledKey = `${e.code || "no code"} / ${e.key}`;
    if (e.code === "Tab") e.preventDefault();
    if (e.repeat) return;
    if (["Escape", "KeyW", "KeyA", "KeyS", "KeyD", "KeyQ", "Tab"].includes(e.code))
      this.stopInspecting();
    const book = this.sketchbook;
    if (e.code === "KeyE" && this.interaction.use()) this.hints.performed("hint.use");
    if (e.code === "Tab") this.toggleSatchel();
    if (e.code === "Escape" && this.satchel.isOpen) this.satchel.close();
    if (e.code === "KeyQ") {
      e.preventDefault();
      this.toggleSketchbook();
      return;
    }
    if (e.code === "Escape" && book?.isVisible) {
      e.preventDefault();
      this.closeSketchbook(true);
      return;
    }
    if (e.code === "KeyR" && book?.isRaised) {
      e.preventDefault();
      this.notebook.show();
      return;
    }
    if (!book?.isRaised) return;
    if (e.code === "KeyA" || e.code === "KeyD") book.turn(e.code === "KeyD" ? 1 : -1);
    const digit = Number(e.code.replace("Digit", ""));
    if (e.code.startsWith("Digit") && digit >= 1 && digit <= SECTIONS.length)
      book.goToSection(SECTIONS[digit - 1].id);
  }

  toggleSatchel(): void {
    if (this.cutscene || this.threatActive || this.hiding || !this.inventory.has("satchel")) return;
    this.hints.performed("hint.satchel");
    this.closeSketchbook();
    if (this.satchel.isOpen) return this.satchel.close();
    this.satchel.open(this.satchelEntries());
  }

  toggleSketchbook(): void {
    if (this.sketchbook?.isRaised || this.notebook.isOpen) {
      this.closeSketchbook(true);
      return;
    }
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
    this.input.clear();
    this.sketchbook.open("now");
    document.exitPointerLock();
  }

  closeSketchbook(relock = false): void {
    this.notebook.back();
    this.sketchbook?.close(this.threatActive || this.hiding || this.cutscene);
    this.input.clear();
    this.gated.notebook = false;
    const canvas = this.engine.getRenderingCanvas();
    canvas?.focus({ preventScroll: true });
    if (relock && !this.cutscene && !this.hiding && !this.threatActive && !this.satchel.isOpen)
      void this.input.lockPointer();
  }

  notebookContent(
    written: ReadonlySet<string> = this.sketchbook?.written ?? new Set<string>(),
  ): NotebookSnapshot {
    const last = this.checkpoints.last;
    const checkpoint = last
      ? `Last checkpoint: ${String(last.flags["checkpoint.location"] ?? last.checkpoint)} · ${last.clock}`
      : this.flags.get("ep1.checkpoint", "CP0") === "CP0"
        ? "Your first checkpoint will be recorded at the writing desk."
        : "Save at the spirit house beyond the front-right corner of the compound fence. Reach it from the front gate.";
    if (this.episode === 3)
      return villageNotebook(
        new VillageProgress(this.flags, this.inventory),
        this.player?.feet ?? Vector3.Zero(),
        last?.episode === 3 ? checkpoint : "The next checkpoint is at Pa Lok’s raft.",
      );
    if (this.episode === 2)
      return pagodaNotebook(
        new PagodaProgress(this.flags, this.inventory),
        this.player?.feet ?? Vector3.Zero(),
        last?.episode === 2 ? checkpoint : "The next checkpoint is at Sophal’s kuti.",
      );
    return buildNotebookContent(
      this.flags,
      this.inventory,
      written,
      this.player?.feet ?? Vector3.Zero(),
      checkpoint,
    );
  }

  private satchelEntries(): SatchelEntry[] {
    const items: Record<string, ItemInfo> = { ...ITEMS, ...EP2_ITEMS, ...EP3_ITEMS };
    return this.inventory
      .list()
      .filter(([id]) => items[id])
      .map(([id, n]) => ({
        name: items[id].name,
        note: items[id].note?.replace("{n}", String(n)),
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
