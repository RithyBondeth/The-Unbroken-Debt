import type { Scene } from "@babylonjs/core/scene";
import type { Material } from "@babylonjs/core/Materials/material";
import type { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { CreateTube } from "@babylonjs/core/Meshes/Builders/tubeBuilder";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";

/** A cloth telephone lead that remains connected on the hook and in Sora's hand. */
export class TelephoneCord {
  private mesh: Mesh | null = null;
  private readonly lastStart = new Vector3(Infinity, Infinity, Infinity);
  private readonly lastEnd = new Vector3(Infinity, Infinity, Infinity);

  constructor(
    private readonly scene: Scene,
    private readonly name: string,
    private readonly terminal: TransformNode,
    private readonly rest: TransformNode,
    private readonly material: Material,
    private readonly radius = 0.0026,
  ) {
    this.update();
  }

  update(heldEnd: Vector3 | null = null): void {
    const start = Vector3.TransformCoordinates(
      Vector3.Zero(),
      this.terminal.computeWorldMatrix(true),
    );
    const end =
      heldEnd ?? Vector3.TransformCoordinates(Vector3.Zero(), this.rest.computeWorldMatrix(true));
    if (
      Vector3.DistanceSquared(start, this.lastStart) < 0.000001 &&
      Vector3.DistanceSquared(end, this.lastEnd) < 0.000001
    )
      return;
    this.lastStart.copyFrom(start);
    this.lastEnd.copyFrom(end);
    const sag = Math.min(0.3, Math.max(0.12, Vector3.Distance(start, end) * 0.22));
    const path = Array.from({ length: 33 }, (_, i) => {
      const t = i / 32;
      const p = Vector3.Lerp(start, end, t);
      p.y -= Math.sin(t * Math.PI) * sag;
      p.x += Math.sin(t * Math.PI) * 0.035;
      return p;
    });
    this.mesh = CreateTube(
      this.name,
      {
        path,
        radius: this.radius,
        tessellation: 8,
        cap: Mesh.CAP_ALL,
        updatable: true,
        instance: this.mesh ?? undefined,
      },
      this.scene,
    );
    this.mesh.material = this.material;
    this.mesh.isPickable = false;
  }
}
