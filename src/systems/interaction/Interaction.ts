import type { Scene } from "@babylonjs/core/scene";
import type { Camera } from "@babylonjs/core/Cameras/camera";
import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import type { Node } from "@babylonjs/core/node";
import { Ray } from "@babylonjs/core/Culling/ray";
import { Color4 } from "@babylonjs/core/Maths/math.color";
import "@babylonjs/core/Rendering/edgesRenderer";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { EventBus } from "../../core/EventBus";
import type { GameEvents } from "../../core/events";

/** How far Sora can reach to use something, in metres. */
export const REACH = 1.8;

/** Pale graphite, like a line Sora is sketching around the object (Controls and Interface, 3). */
const OUTLINE = new Color4(0.42, 0.4, 0.35, 1);
/** Faces meeting at more than this angle's cosine apart draw a line (0.95: about 18°). */
const EDGE_EPSILON = 0.95;
const EDGE_WIDTH = 2;

interface Target {
  id: string;
  meshes: AbstractMesh[];
}

/** Every mesh under `node`, and the node itself if it is one. */
export function meshesOf(node: Node): AbstractMesh[] {
  const own = "getTotalVertices" in node ? [node as AbstractMesh] : [];
  return [...own, ...node.getChildMeshes(false)].filter((m) => m.getTotalVertices() > 0);
}

/**
 * The object at the centre of the view, within reach and not hidden behind a
 * wall, is focused: it gets a faint pencil outline and `interact:focus`. E uses
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
  private readonly ray = new Ray(Vector3.Zero(), Vector3.Forward(), REACH);
  constructor(
    private readonly scene: Scene,
    private readonly camera: Camera,
    private readonly bus: EventBus<GameEvents>,
  ) {}

  get focus(): string | null {
    return this.focused?.id ?? null;
  }

  /** Makes `node` (and everything under it) usable as `id`. */
  add(id: string, node: Node | AbstractMesh[]): void {
    this.remove(id);
    const meshes = Array.isArray(node) ? node : meshesOf(node);
    const target = { id, meshes };
    this.targets.set(id, target);
    for (const mesh of meshes) this.byMesh.set(mesh.uniqueId, target);
  }

  remove(id: string): void {
    const target = this.targets.get(id);
    if (!target) return;
    if (this.focused === target) this.setFocus(null);
    for (const mesh of target.meshes) this.byMesh.delete(mesh.uniqueId);
    this.targets.delete(id);
  }

  update(): void {
    if (!this.active) {
      this.setFocus(null);
      this.distance = Infinity;
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
  }

  /** E: uses the focused object. Returns its id, or null if nothing is in focus. */
  use(): string | null {
    if (!this.active || !this.focused) return null;
    const id = this.focused.id;
    this.bus.emit("interact:use", { id });
    return id;
  }

  /**
   * The pencil outline is the edges of the focused object, drawn as lines over it:
   * its silhouette and sharp creases. (A stroke-only highlight layer paints its
   * colour over the whole object and cuts the object back out with a stencil this
   * render pipeline doesn't keep, washing it out; Babylon's outline renderer draws
   * inside the geometry pre-pass, which blacks out the frame on WebGPU.) The lines
   * are worked out the first time an object is focused, then kept.
   */
  private setFocus(target: Target | null): void {
    if (target === this.focused) return;
    for (const mesh of this.focused?.meshes ?? [])
      if (mesh.edgesRenderer) mesh.edgesRenderer.isEnabled = false;
    this.focused = target;
    for (const mesh of target?.meshes ?? []) {
      if (!mesh.edgesRenderer) {
        mesh.enableEdgesRendering(EDGE_EPSILON);
        mesh.edgesWidth = EDGE_WIDTH;
        mesh.edgesColor = OUTLINE;
      }
      if (mesh.edgesRenderer) mesh.edgesRenderer.isEnabled = true;
    }
    if (target) this.bus.emit("interact:focus", { id: target.id });
  }
}
