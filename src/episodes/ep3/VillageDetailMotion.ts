import type { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import type { Game } from "@/core/Game";

/** Small movement in suspended fabric, with its actual hangers as pivots. */
export class VillageDetailMotion {
  private readonly curtains: TransformNode[];
  private time = 0;
  private readonly reduced = matchMedia("(prefers-reduced-motion: reduce)");
  constructor(game: Game) {
    this.curtains = game.scene.transformNodes.filter((node) =>
      node.name.startsWith("curtain_motion_"),
    );
    for (const node of this.curtains) node.rotationQuaternion = null;
  }
  update(dt: number, storm: boolean): void {
    this.time += dt;
    this.curtains.forEach((node, i) => {
      node.rotation.z = this.reduced.matches
        ? 0
        : Math.sin(this.time * 0.71 + i * 1.47) * (storm ? 0.008 : 0.002) +
          Math.sin(this.time * 1.7 + i) * 0.001;
    });
  }
}
