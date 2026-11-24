import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { Scene } from "@babylonjs/core/scene";
import type { LevelMarker } from "@/core/levelBuilder";
import { meshesOf } from "@/systems/interaction/Interaction";

/**
 * A door leaf that swings into its room. A leaf in a north-south wall turns about its
 * south jamb, one in an east-west wall about its west jamb (Blender's west: Babylon's
 * larger x). `swing` is the way it turns: -1 for a room west of a north-south wall or
 * north of an east-west one (Sok's study, the tool shed), 1 for the other side.
 */
export class VillageDoor {
  private readonly hinge: TransformNode;
  private opened = false;

  constructor(
    private readonly scene: Scene,
    readonly marker: LevelMarker,
    private readonly collider: string,
    private readonly padlock: string,
    private readonly swing: 1 | -1 = 1,
  ) {
    marker.node.computeWorldMatrix(true);
    const meshes = meshesOf(marker.node);
    const min = new Vector3(Infinity, Infinity, Infinity);
    const max = new Vector3(-Infinity, -Infinity, -Infinity);
    for (const mesh of meshes) {
      mesh.computeWorldMatrix(true);
      const box = mesh.getBoundingInfo().boundingBox;
      min.minimizeInPlace(box.minimumWorld);
      max.maximizeInPlace(box.maximumWorld);
    }
    this.hinge = new TransformNode(`${marker.name}_hinge`, scene);
    const alongX = max.x - min.x > max.z - min.z;
    if (alongX) this.hinge.position.set(max.x, min.y, (min.z + max.z) / 2);
    else this.hinge.position.set((min.x + max.x) / 2, min.y, max.z);
    // Imported glTF nodes inherit a mirror: preserve their world pose on reparenting.
    marker.node.setParent(this.hinge, true);
  }

  open(immediate = false): void {
    if (this.opened) return;
    this.opened = true;
    const anchor = this.scene.getTransformNodeByName(`${this.collider}_body`);
    const shape = anchor?.physicsBody?.shape;
    anchor?.physicsBody?.dispose();
    shape?.dispose();
    anchor?.dispose();
    this.scene.getMeshByName(this.padlock)?.setEnabled(false);
    if (immediate) this.hinge.rotation.y = this.swing * Math.PI * 0.47;
  }

  update(dt: number): void {
    if (this.opened)
      this.hinge.rotation.y =
        this.swing * Math.min(Math.PI * 0.47, Math.abs(this.hinge.rotation.y) + dt * 0.7);
  }
}
