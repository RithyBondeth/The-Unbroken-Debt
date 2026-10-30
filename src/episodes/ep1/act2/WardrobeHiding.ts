import type { Game } from "../../../core/Game";
import type { Lamp } from "../../../systems/lamp/Lamp";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { HidingWardrobe, WalkerModels } from "./WalkerModels";
import "../../../ui/html/walker.css";
import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";

/** E enters; a narrow view through the real louvres keeps the threat in the world. */
export class WardrobeHiding {
  private occupied: HidingWardrobe | null = null;
  private age = 0;
  private opening: string | null = null;
  private openingFor = 0;
  private readonly vignette = document.createElement("div");
  private hintState = "";
  private closeMeshes = new Set<AbstractMesh>();

  constructor(
    private readonly game: Game,
    private readonly models: WalkerModels,
    private readonly lamp: Lamp,
  ) {
    this.vignette.className = "wardrobe-vignette";
    this.vignette.hidden = true;
    document.body.append(this.vignette);
    for (const w of models.wardrobes) game.interaction.add(`interact_wardrobe_${w.id}`, w.root);
    game.bus.on("interact:focus", ({ id }) => {
      if (id.startsWith("interact_wardrobe_") && !game.hiding)
        game.hints.show("hint.wardrobeEnter", 5);
    });
    game.bus.on("interact:use", ({ id }) => {
      const wardrobe = models.wardrobes.find((w) => id === `interact_wardrobe_${w.id}`);
      if (wardrobe && !game.cutscene && !game.hiding && game.flags.get("ep1.sok.unlocked", false))
        this.enter(wardrobe);
    });
    window.addEventListener(
      "keydown",
      (event) => {
        if (!this.occupied || game.cutscene || !["KeyE", "Escape"].includes(event.code)) return;
        event.preventDefault();
        event.stopImmediatePropagation();
        if (!event.repeat && this.age > 0.5) this.exit();
      },
      { capture: true },
    );
  }

  get wardrobe(): HidingWardrobe | null {
    return this.occupied;
  }
  get concealed(): boolean {
    return (
      !!this.occupied && this.age > 0.55 && this.occupied.open < 0.1 && this.lamp.state !== "open"
    );
  }

  update(dt: number): void {
    if (this.openingFor > 0) {
      this.openingFor -= dt;
      if (this.openingFor <= 0) this.opening = null;
    }
    this.models.animate(dt, this.opening);
    if (!this.occupied) return;
    this.age += dt;
    const yaw = this.occupied.yaw;
    const turn = Math.atan2(
      Math.sin(this.game.player.yaw - yaw),
      Math.cos(this.game.player.yaw - yaw),
    );
    this.game.player.yaw = yaw + Math.max(-0.22, Math.min(0.22, turn));
    this.game.player.pitch = Math.max(-0.25, Math.min(0.25, this.game.player.pitch));
    const hint = this.lamp.state === "open" ? "hint.wardrobeLamp" : "hint.wardrobeExit";
    if (hint !== this.hintState) {
      this.hintState = hint;
      this.game.hints.show(hint, 120);
    }
  }

  exit(restorePosition = true): void {
    const w = this.occupied;
    if (!w) return;
    this.occupied = null;
    this.game.hiding = false;
    this.game.gated.hiding = false;
    this.vignette.hidden = true;
    this.game.atmosphere.nightSight.excludedMeshes =
      this.game.atmosphere.nightSight.excludedMeshes.filter((mesh) => !this.closeMeshes.has(mesh));
    this.closeMeshes.clear();
    this.game.hints.hide();
    this.hintState = "";
    this.opening = w.id;
    this.openingFor = 0.45;
    if (restorePosition) {
      this.game.player.teleport(w.front, w.yaw);
      this.game.player.pitch = 0;
    }
  }

  private enter(w: HidingWardrobe): void {
    if (Vector3.Distance(this.game.player.feet, w.root.position) > 1.95) return;
    this.game.stopInspecting();
    this.game.satchel.close();
    if (this.game.sketchbook?.isOpen) this.game.sketchbook.toggle();
    this.occupied = w;
    // Eye adaptation is a near-camera fill; it must not bleach a door 40 cm away.
    this.closeMeshes = new Set(w.root.getChildMeshes());
    this.game.atmosphere.nightSight.excludedMeshes.push(...this.closeMeshes);
    this.age = 0;
    this.opening = w.id;
    this.openingFor = 0.35;
    this.game.hiding = true;
    this.game.gated.hiding = true;
    this.game.player.teleport(w.root.position, w.yaw);
    this.game.player.pitch = 0;
    this.vignette.hidden = false;
    this.hintState = "";
  }
}
