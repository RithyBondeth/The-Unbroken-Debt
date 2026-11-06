import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import { CreateBox } from "@babylonjs/core/Meshes/Builders/boxBuilder";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Quaternion } from "@babylonjs/core/Maths/math.vector";
import type { Game } from "@/core/Game";
const ROOF_PART =
  /^hawtrai_(?:crown_)?(?:roof|gable|bargeboard|ridge|finial|rafter|purlin|eave|ceiling_panel|trusses)/;
export const COLLAPSE_KEEP = [ROOF_PART, /^archive_cabinet(?:\.|$)/];
export function fallingHeight(elapsed: number, start: number, floor = 1.4): number {
  return Math.max(floor, start - 4.9 * Math.max(0, elapsed) ** 2);
}
interface MovingPart {
  node: TransformNode;
  rest: Vector3;
  side: number;
  delay: number;
  roof: boolean;
}
/** Actual roof panels, cabinets, planks and manuscript bundles move; the central exit stays clear. */
export class LibraryCollapse {
  private readonly parts: MovingPart[] = [];
  private readonly debris: { mesh: AbstractMesh; at: Vector3; delay: number; spin: number }[] = [];
  private active = false;
  private elapsed = 0;
  constructor(game: Game) {
    const scene = game.scene;
    for (const mesh of [...scene.meshes]) {
      const roof = ROOF_PART.test(mesh.name),
        cabinet = /^archive_cabinet(?:\.|$)/.test(mesh.name);
      if (!roof && !cabinet) continue;
      mesh.computeWorldMatrix(true);
      const center = mesh.getBoundingInfo().boundingBox.centerWorld.clone();
      const pivot = new TransformNode("collapse_pivot_" + mesh.name, scene);
      pivot.position.copyFrom(center);
      mesh.setParent(pivot, true);
      pivot.rotationQuaternion = Quaternion.Identity();
      this.parts.push({
        node: pivot,
        rest: center,
        side: center.x < 0 ? -1 : 1,
        delay: roof ? 0.3 + (this.parts.length % 3) * 0.5 : 1.8 + (this.parts.length % 2) * 0.6,
        roof,
      });
    }
    const wood = scene.getMaterialByName("M_ep2_post") ?? scene.getMaterialByName("M_ep2_teak");
    const paper = scene.getMaterialByName("M_ep2_paper");
    for (let i = 0; i < 20; i++) {
      const side = i % 2 ? -1 : 1;
      const mesh = CreateBox(
        "library_falling_" + i,
        { width: i < 12 ? 0.7 : 0.24, height: i < 12 ? 0.065 : 0.05, depth: i < 12 ? 0.12 : 0.16 },
        scene,
      );
      mesh.material = i < 12 ? wood : paper;
      mesh.isPickable = false;
      const at = new Vector3(side * (2.25 + (i % 3) * 0.36), 4.4 + (i % 4) * 0.3, -29.5 - (i % 6));
      mesh.position.copyFrom(at);
      mesh.setEnabled(false);
      this.debris.push({ mesh, at, delay: 0.4 + (i % 7) * 0.35, spin: ((i % 3) - 1) * 0.8 + 0.4 });
    }
  }
  start(): void {
    this.active = true;
    this.elapsed = 0;
    for (const d of this.debris) d.mesh.setEnabled(true);
  }
  get time(): number {
    return this.elapsed;
  }
  /** Script frames and gameplay use the same deterministic destruction pose. */
  pose(elapsed: number): void {
    this.elapsed = Math.max(0, elapsed);
    for (const part of this.parts) {
      const t = Math.max(0, this.elapsed - part.delay),
        k = Math.min(1, t / 3);
      part.node.position.copyFrom(part.rest);
      if (part.roof) {
        part.node.position.x += part.side * 3.4 * k * k;
        part.node.position.y = Math.max(1.8, part.rest.y - 2.3 * k * k);
        part.node.rotationQuaternion = Quaternion.RotationYawPitchRoll(
          0,
          part.side * 0.2 * k,
          part.side * 0.5 * k,
        );
      } else {
        // Shelves fall into their wall recess, away from the 2m central passage.
        part.node.position.x += part.side * 0.35 * k;
        part.node.position.y -= 0.3 * k;
        part.node.rotationQuaternion = Quaternion.RotationYawPitchRoll(0, 0, part.side * 0.23 * k);
      }
    }
    for (const d of this.debris) {
      const t = Math.max(0, this.elapsed - d.delay);
      d.mesh.position.copyFrom(d.at);
      d.mesh.position.y = fallingHeight(t, d.at.y);
      d.mesh.rotation.set(
        Math.min(t, 1.6) * d.spin,
        Math.min(t, 1.6) * 0.4,
        Math.min(t, 1.6) * d.spin * 0.6,
      );
    }
  }
  update(dt: number, active: boolean): void {
    if (this.active && active) this.pose(this.elapsed + dt);
  }
  restoreBroken(): void {
    this.start();
    this.pose(8);
  }
}
