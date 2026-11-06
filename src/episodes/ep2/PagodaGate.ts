import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import type { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import type { Scene } from "@babylonjs/core/scene";
import { RelicCraft } from "@/shared/RelicCraft";
import { ANCESTORS } from "./data/pagoda";
import type { PagodaProgress } from "./PagodaProgress";

/** A timber grille with a small worked lock; lamplight passes through to the pond. */
export class PagodaGate {
  readonly root: TransformNode;
  private readonly symbols: PBRMaterial[] = [];
  constructor(scene: Scene) {
    const craft = new RelicCraft(scene);
    this.root = craft.root("interact_bridge_lock", [0, 0, -18]);
    const authored = scene.getMaterialByName("M_ep2_post");
    const wood =
      authored instanceof PBRMaterial ? authored : craft.mat("pagoda_gate_wood", "#514739");
    const bronze = craft.mat("pagoda_gate_bronze", "#76634a", 0.68, 0.6);
    for (const x of [-0.9, 0.9])
      craft.box(this.root, "bridge_gate_upright", [0.12, 1.55, 0.12], [x, 0.775, 0], wood);
    for (const y of [0.36, 1.15])
      craft.box(this.root, "bridge_gate_crossbar", [1.8, 0.13, 0.09], [0, y, 0], wood);
    for (const x of [-0.65, -0.325, 0, 0.325, 0.65])
      craft.box(this.root, "bridge_gate_spindle", [0.045, 0.75, 0.045], [x, 0.76, 0], wood);
    const lock = craft.cylinder(
      this.root,
      "bridge_bronze_lock",
      0.27,
      0.065,
      [0, 0.78, 0.08],
      bronze,
    );
    lock.rotation.x = Math.PI / 2;
    const shackle = craft.ring(
      this.root,
      "bridge_lock_shackle",
      0.18,
      0.027,
      [0, 0.95, 0.08],
      bronze,
    );
    shackle.rotation.x = Math.PI / 2;
    for (let i = 0; i < 4; i++) {
      const mat = craft.mat("pagoda_family_symbol_" + i, "#999383", 0.78, 0.5);
      this.symbols.push(mat);
      const x = -0.6 + i * 0.4;
      for (let k = 0; k < 5; k++) {
        const a = (k * Math.PI * 2) / 5;
        craft.sphere(
          this.root,
          "bridge_family_flower_" + i,
          [0.035, 0.045, 0.012],
          [x + Math.cos(a) * 0.028, 1.15 + Math.sin(a) * 0.028, 0.055],
          mat,
        );
      }
    }
  }
  sync(progress: PagodaProgress): void {
    this.root.setEnabled(!progress.flags.get("ep2.bridge.open", false));
    this.symbols.forEach((mat, i) => {
      const k = progress.offered(ANCESTORS[i].id) ? 1 : 0;
      mat.emissiveColor.set(0.08 * k, 0.055 * k, 0.02 * k);
    });
  }
}
