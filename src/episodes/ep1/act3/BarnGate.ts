import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import type { Game } from "@/core/Game";
import type { Area } from "@/core/areaLoader";

/** The barn yard's gate leaf, its padlock and chain (tools/areas/farmstead.py fences). */
export const BARN_GATE_MESH = /^(fs_barn_gate_(leaf|padlock)|fs_gate_(chain|shackle))/;
/** The north gate post the leaf hangs off: Blender (16.5, 23.4) (farmstead.BARN_FENCE, BARN_GATE). */
const HINGE = new Vector3(-16.5, 0, -23.4);

/**
 * O3, the chained barn gate (the approved gameplay map): the iron key from jar J3 opens
 * its padlock; the chain drops and the leaf swings out towards the house. Until then the
 * barn yard, its rice barn and their two jars are shut away.
 */
export class BarnGate {
  private readonly hinge: TransformNode;
  private readonly lock: AbstractMesh[];
  private opened = false;
  private swing = 0;

  constructor(
    private readonly game: Game,
    area: Area,
  ) {
    const scene = game.scene;
    const leaf = area.container.meshes.filter((m) => /^fs_barn_gate_leaf/.test(m.name));
    this.lock = area.container.meshes.filter(
      (m) => BARN_GATE_MESH.test(m.name) && !leaf.includes(m),
    );
    let floor = Infinity;
    for (const mesh of leaf) {
      mesh.computeWorldMatrix(true);
      floor = Math.min(floor, mesh.getBoundingInfo().boundingBox.minimumWorld.y);
    }
    this.hinge = new TransformNode("interact_barn_gate", scene);
    this.hinge.position.set(HINGE.x, Number.isFinite(floor) ? floor : 0, HINGE.z);
    // Imported glTF nodes inherit a mirror: keep their world pose on reparenting.
    for (const mesh of leaf) mesh.setParent(this.hinge, true);
    area.container.transformNodes.push(this.hinge);
    if (game.flags.get("ep1.barnGate.open", false)) this.open(true);
    else if (leaf.length) game.interaction.add("interact_barn_gate", this.hinge);
    game.bus.on("interact:use", ({ id }) => {
      if (id !== "interact_barn_gate" || this.opened) return;
      if (!game.inventory.has("barn_gate_key")) {
        game.hints.show("note.barnGateLocked", 4);
        return;
      }
      this.open();
      game.flags.set("ep1.barnGate.open", true);
      game.hints.show("note.barnGateOpen", 4);
    });
  }

  open(immediate = false): void {
    if (this.opened) return;
    this.opened = true;
    const scene = this.game.scene;
    const anchor = scene.getTransformNodeByName("col_fs_barn_gate_body");
    const shape = anchor?.physicsBody?.shape;
    anchor?.physicsBody?.dispose();
    shape?.dispose();
    anchor?.dispose();
    for (const mesh of this.lock) mesh.setEnabled(false);
    this.game.interaction.remove("interact_barn_gate");
    if (immediate) {
      this.swing = 1;
      this.hinge.rotation.y = Math.PI * 0.55;
    }
  }

  update(dt: number): void {
    if (!this.opened || this.swing >= 1) return;
    // Heavy on its sagging hinge: slow to start, coming to rest against the fence.
    this.swing = Math.min(1, this.swing + dt * 0.45);
    const eased = this.swing * this.swing * (3 - 2 * this.swing);
    // Out to the west, towards the house (Babylon's +x).
    this.hinge.rotation.y = eased * Math.PI * 0.55;
  }

  /** For a restored save: shown already open. */
  get isOpen(): boolean {
    return this.opened;
  }
}
