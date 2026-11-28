import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import type { Game } from "@/core/Game";
import type { Area } from "@/core/areaLoader";

/** The hall trapdoor's lid: its boards, the battens under them and the iron ring. */
export const TRAPDOOR_MESH = /^trapdoor_(lid|batten|ring)/;
/** Its hinge runs along the opening's south edge: Blender y 11.85 (stilt_house.TRAP). */
const HINGE_Z = -11.85;

/**
 * O6, the trapdoor in the hall floor (the approved gameplay map): lifted by its ring from
 * above, or pushed up from the ladder below, it swings back to lean against the floor
 * on its south side, and the ladder down to the funeral is open. It stays open.
 */
export class Trapdoor {
  private readonly hinge: TransformNode;
  private opened = false;
  private swing = 0;

  constructor(
    private readonly game: Game,
    area: Area,
  ) {
    const parts = area.container.meshes.filter((m) => TRAPDOOR_MESH.test(m.name));
    let top = -Infinity,
      x = 0;
    for (const mesh of parts) {
      mesh.computeWorldMatrix(true);
      const box = mesh.getBoundingInfo().boundingBox;
      top = Math.max(top, box.maximumWorld.y);
      x += box.centerWorld.x / Math.max(1, parts.length);
    }
    this.hinge = new TransformNode("interact_trapdoor", game.scene);
    this.hinge.position.set(x, Number.isFinite(top) ? top : 2.5, HINGE_Z);
    // Imported glTF nodes inherit a mirror: keep their world pose on reparenting.
    for (const mesh of parts) mesh.setParent(this.hinge, true);
    area.container.transformNodes.push(this.hinge);
    if (game.flags.get("ep1.trapdoor.open", false)) this.open(true);
    else if (parts.length) game.interaction.add("interact_trapdoor", this.hinge);
    game.bus.on("interact:use", ({ id }) => {
      if (id !== "interact_trapdoor" || this.opened) return;
      this.open();
      game.flags.set("ep1.trapdoor.open", true);
    });
  }

  open(immediate = false): void {
    if (this.opened) return;
    this.opened = true;
    const anchor = this.game.scene.getTransformNodeByName("col_trapdoor_lid_body");
    const shape = anchor?.physicsBody?.shape;
    anchor?.physicsBody?.dispose();
    shape?.dispose();
    anchor?.dispose();
    this.game.interaction.remove("interact_trapdoor");
    if (immediate) {
      this.swing = 1;
      this.hinge.rotation.x = OPEN;
    }
  }

  update(dt: number): void {
    if (!this.opened || this.swing >= 1) return;
    // Heavy boards: a slow lift, then falling back past upright onto the floor.
    this.swing = Math.min(1, this.swing + dt * 0.9);
    const eased =
      this.swing < 0.7
        ? (this.swing / 0.7) ** 1.6 * 0.82
        : 0.82 + 0.18 * Math.sin(((this.swing - 0.7) / 0.3) * (Math.PI / 2));
    this.hinge.rotation.x = eased * OPEN;
  }

  get isOpen(): boolean {
    return this.opened;
  }
}

/** Swung up and back, past upright, to lean on the floor south of the opening. */
const OPEN = Math.PI * 0.56;
