import type { Scene } from "@babylonjs/core/scene";
import type { Camera } from "@babylonjs/core/Cameras/camera";
import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import type { Material } from "@babylonjs/core/Materials/material";
import { MultiMaterial } from "@babylonjs/core/Materials/multiMaterial";
import { InteractionHint } from "./InteractionHint";
import type { Node } from "@babylonjs/core/node";
import { Ray } from "@babylonjs/core/Culling/ray";
import { Color4 } from "@babylonjs/core/Maths/math.color";
import "@babylonjs/core/Rendering/edgesRenderer";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { EventBus } from "../../core/EventBus";
import type { GameEvents } from "../../core/events";

/** How far Sora can reach to use something, in metres. */
const REACH = 1.8;

/** Warm ivory complements the lamp and remains legible on dark wood. */
const OUTLINE = new Color4(0.82, 0.74, 0.57, 0);
/** Faces meeting at more than this angle's cosine apart draw a line (0.95: about 18°). */
const EDGE_EPSILON = 0.95;
const EDGE_PIXELS = 1.35;
const FADE_SECONDS = 0.14;

interface Target {
  id: string;
  meshes: AbstractMesh[];
  hintMeshes: AbstractMesh[];
}

/** Every mesh under `node`, and the node itself if it is one. */
export function meshesOf(node: Node): AbstractMesh[] {
  const own = "getTotalVertices" in node ? [node as AbstractMesh] : [];
  return [...own, ...node.getChildMeshes(false)].filter((m) => m.getTotalVertices() > 0);
}

/**
 * The object at the centre of the view, within reach and not hidden behind a
 * wall, is focused: it gets a warm rim and ivory contour and `interact:focus`. E uses
 * it (`interact:use`). There is no crosshair (Controls and Interface, section 3).
 */
export class Interaction {
  /** Off while a scripted moment, the satchel or the sketchbook has the player's hands. */
  active = true;
  /** Which targets can be focused right now (P02: only the illustration). */
  allow: (id: string) => boolean = () => true;
  /** How far the nearest solid thing straight ahead is (m), or Infinity beyond reach. */
  distance = Infinity;

  private readonly targets = new Map<string, Target>();
  private readonly byMesh = new Map<number, Target>();
  private focused: Target | null = null;
  private readonly hintStrength = new Map<AbstractMesh, number>();
  private readonly hintedMaterials = new WeakSet<Material>();
  private readonly viewPosition = Vector3.Zero();
  private readonly reducedMotion =
    typeof matchMedia === "function" ? matchMedia("(prefers-reduced-motion: reduce)") : null;
  private readonly ray = new Ray(Vector3.Zero(), Vector3.Forward(), REACH);
  constructor(
    private readonly scene: Scene,
    private readonly camera: Camera,
    private readonly bus: EventBus<GameEvents>,
  ) {}

  get focus(): string | null {
    return this.focused?.id ?? null;
  }

  /** Makes the whole node usable. Large props may limit the visual cue to a
   * small detail without narrowing their reach or interaction ray. */
  add(id: string, node: Node | AbstractMesh[], hintMeshes?: readonly AbstractMesh[]): void {
    this.remove(id);
    const meshes = Array.isArray(node) ? node : meshesOf(node);
    const target = {
      id,
      meshes,
      hintMeshes: hintMeshes ? meshes.filter((m) => hintMeshes.includes(m)) : meshes,
    };
    this.targets.set(id, target);
    for (const mesh of meshes) {
      this.byMesh.set(mesh.uniqueId, target);
    }
    for (const mesh of target.hintMeshes) this.prepareMaterial(mesh.material);
  }

  remove(id: string): void {
    const target = this.targets.get(id);
    if (!target) return;
    if (this.focused === target) this.setFocus(null);
    for (const mesh of target.meshes) {
      if (this.byMesh.get(mesh.uniqueId) === target) {
        this.byMesh.delete(mesh.uniqueId);
        this.clearHint(mesh);
      }
    }
    this.targets.delete(id);
  }

  update(): void {
    if (!this.active) {
      this.setFocus(null);
      this.distance = Infinity;
      // Menus, books and cutscenes take over immediately, without a lingering cue.
      for (const mesh of this.hintStrength.keys()) this.clearHint(mesh);
      return;
    }
    this.camera.getForwardRayToRef(this.ray, REACH);
    // Pick everything solid, so a wall between Sora and an object hides it.
    const hit = this.scene.pickWithRay(
      this.ray,
      (m) => m.isEnabled() && m.isVisible && m.isPickable && m.renderingGroupId === 0,
    );
    this.distance = hit?.pickedMesh ? hit.distance : Infinity;
    const target = hit?.pickedMesh ? this.byMesh.get(hit.pickedMesh.uniqueId) : undefined;
    this.setFocus(target && this.allow(target.id) ? target : null);
    this.updateHints();
  }

  /** E: uses the focused object. Returns its id, or null if nothing is in focus. */
  use(): string | null {
    if (!this.active || !this.focused) return null;
    const id = this.focused.id;
    this.bus.emit("interact:use", { id });
    return id;
  }

  private prepareMaterial(material: Material | null): void {
    if (!material || this.hintedMaterials.has(material)) return;
    this.hintedMaterials.add(material);
    if (material instanceof MultiMaterial) {
      material.subMaterials.forEach((part) => this.prepareMaterial(part));
    } else if (
      material.getClassName().startsWith("PBR") ||
      material.getClassName() === "StandardMaterial"
    ) {
      new InteractionHint(material, (mesh) => this.hintStrength.get(mesh) ?? 0);
    }
  }

  private clearHint(mesh: AbstractMesh): void {
    if (mesh.edgesRenderer) mesh.edgesRenderer.isEnabled = false;
    this.hintStrength.delete(mesh);
  }

  /** All registered targets share the hint; invisible pickup volumes never draw. */
  private setFocus(target: Target | null): void {
    if (target === this.focused) return;
    this.focused = target;
    for (const mesh of target?.hintMeshes ?? []) {
      if (mesh.isDisposed() || !mesh.isEnabled() || !mesh.isVisible || mesh.visibility <= 0)
        continue;
      // Texture-based offering slots already have a soft focus ring. Their
      // transparent interaction patch must not acquire an opaque disc border.
      if (mesh.material?.alpha === 0) continue;
      this.prepareMaterial(mesh.material);
      if (!mesh.edgesRenderer) mesh.enableEdgesRendering(EDGE_EPSILON);
      mesh.edgesColor = OUTLINE.clone();
      this.hintStrength.set(mesh, this.hintStrength.get(mesh) ?? 0);
      if (mesh.edgesRenderer) mesh.edgesRenderer.isEnabled = true;
    }
    if (target) this.bus.emit("interact:focus", { id: target.id });
  }

  private updateHints(): void {
    const engine = this.scene.getEngine();
    const step = this.reducedMotion?.matches
      ? 1
      : Math.min(engine.getDeltaTime() / 1000, 0.05) / FADE_SECONDS;
    const height = engine.getRenderingCanvas()?.clientHeight || engine.getRenderHeight();
    for (const [mesh, strength] of this.hintStrength) {
      const visible =
        !mesh.isDisposed() && mesh.isEnabled() && mesh.isVisible && mesh.visibility > 0;
      const focused = visible && this.byMesh.get(mesh.uniqueId) === this.focused;
      const next = focused ? Math.min(1, strength + step) : Math.max(0, strength - step);
      if (!visible || (!focused && next === 0)) {
        this.clearHint(mesh);
        continue;
      }
      this.hintStrength.set(mesh, next);
      // Match a CSS-pixel stroke at different distances and render resolutions.
      Vector3.TransformCoordinatesToRef(
        mesh.getBoundingInfo().boundingSphere.centerWorld,
        this.camera.getViewMatrix(),
        this.viewPosition,
      );
      mesh.edgesWidth =
        (EDGE_PIXELS * 100 * Math.max(0.05, Math.abs(this.viewPosition.z))) / height;
      mesh.edgesColor.a = next * 0.85;
    }
  }
}
