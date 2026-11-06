import { CreateCylinder } from "@babylonjs/core/Meshes/Builders/cylinderBuilder";
import { Lamp } from "./Lamp";
import { HeldLamp } from "@/player/HeldLamp";
import type { Game } from "@/core/Game";
import type { PointLight } from "@babylonjs/core/Lights/pointLight";

export interface ExpeditionLights {
  readonly lamp: PointLight;
  update(dt: number, flame: number): void;
}

/** The same physical lantern as Episode 1, with Sophal's sliding shutter. */
export class LanternEquipment {
  readonly lamp: Lamp;
  held!: HeldLamp;
  memory = false;
  private time = 0;
  private striking = false;
  private raised = false;
  private readonly abort = new AbortController();
  private shutter: ReturnType<typeof CreateCylinder> | null = null;
  constructor(
    private readonly game: Game,
    private readonly lights: ExpeditionLights,
    private readonly matchHint = "No matches. Sophal keeps spares at his table.",
  ) {
    this.lamp = new Lamp(game.bus, game.savedLamp?.oil ?? 1, game.savedLamp?.state ?? "open");
    this.lamp.restoreAtLeast(0.5);
  }
  get visibleFlame(): number {
    return this.memory ? 0.32 : this.lamp.state === "open" ? this.lamp.flame(this.time) : 0;
  }
  async load(): Promise<void> {
    const g = this.game;
    this.held = await HeldLamp.load(g.scene, g.camera);
    g.hands.attachLamp(this.held.root, () => this.memory || this.lamp.burning);
    this.lights.lamp.excludedMeshes.push(...this.held.meshes, ...g.hands.meshes);
    // A real opaque sleeve closes over the chimney; its state also extinguishes exterior light.
    const material = this.held.meshes.find((m) => /brass/i.test(m.material?.name ?? ""))?.material;
    this.shutter = CreateCylinder(
      "lamp_sliding_shutter",
      { diameter: 0.15, height: 0.22, tessellation: 24 },
      g.scene,
    );
    this.shutter.parent = this.held.root;
    this.shutter.position.set(0, 0.13, 0);
    this.shutter.material = material ?? null;
    this.shutter.renderingGroupId = 1;
    this.shutter.isPickable = false;
    this.lights.lamp.excludedMeshes.push(this.shutter);
    window.addEventListener(
      "keydown",
      (e) => {
        if (!e.repeat) void this.key(e.code);
      },
      { signal: this.abort.signal },
    );
    window.addEventListener(
      "mousedown",
      (e) => {
        if (e.button === 2 && g.input.pointerLocked) this.raised = true;
      },
      { signal: this.abort.signal },
    );
    window.addEventListener(
      "mouseup",
      (e) => {
        if (e.button === 2) this.raised = false;
      },
      { signal: this.abort.signal },
    );
    window.addEventListener(
      "blur",
      () => {
        this.raised = false;
      },
      { signal: this.abort.signal },
    );
    g.scene.onDisposeObservable.addOnce(() => this.dispose());
    window.addEventListener(
      "contextmenu",
      (e) => {
        if (g.input.pointerLocked) e.preventDefault();
      },
      { signal: this.abort.signal },
    );
  }
  update(dt: number): void {
    const g = this.game;
    this.time += dt;
    if (
      !this.memory &&
      !g.cutscene &&
      !document.hidden &&
      !g.satchel.isOpen &&
      !g.sketchbook?.isOpen &&
      g.input.pointerLocked
    )
      this.lamp.update(dt);
    this.held.update(dt, this.visibleFlame, this.lamp.oil, this.raised, g.player.speed);
    if (this.shutter) this.shutter.setEnabled(!this.memory && this.lamp.state === "shuttered");
    this.lights.update(dt, this.visibleFlame);
  }
  async key(code: string): Promise<void> {
    const g = this.game;
    if (this.memory || g.cutscene || g.gated.reading || g.satchel.isOpen || !g.input.pointerLocked)
      return;
    if (code === "KeyX") {
      this.lamp.toggleShutter();
      void g.subtitles.say(
        "Sora",
        this.lamp.state === "shuttered"
          ? "Shutter closed. The wick is still burning."
          : "Shutter open.",
        2,
      );
      return;
    }
    if (code === "KeyF") {
      if (this.striking) return;
      if (this.lamp.burning) {
        this.lamp.putOut();
        return;
      }
      if (this.lamp.oil <= 0) {
        void g.subtitles.say("Sora", "The lamp is dry. R to refill it.", 3);
        return;
      }
      if (!g.inventory.remove("matches")) {
        void g.subtitles.say("Sora", this.matchHint, 3);
        return;
      }
      this.striking = true;
      g.hands.animate("strike");
      await new Promise((r) => setTimeout(r, 550));
      this.lamp.light();
      this.striking = false;
    }
    if (code === "KeyR" && this.lamp.oil < 0.9 && g.inventory.remove("oil")) {
      this.lamp.refill();
      g.hands.animate("pour");
    }
  }
  dispose(): void {
    this.abort.abort();
    this.held.dispose();
    this.shutter?.dispose();
  }
}
