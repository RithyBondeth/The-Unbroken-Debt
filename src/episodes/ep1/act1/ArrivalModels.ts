import type { Scene } from "@babylonjs/core/scene";
import { RelicCraft } from "../act3/RelicCraft";
import { WallTelephone } from "./WallTelephone";
import type { Vector3 } from "@babylonjs/core/Maths/math.vector";

/** The family have left: their note, a hall telephone and a prepared matchbox. */
export class ArrivalModels {
  readonly note;
  readonly phone;
  readonly receiver;
  readonly matches;
  private readonly telephone: WallTelephone;
  constructor(scene: Scene) {
    const c = new RelicCraft(scene);
    const wood = c.surface("arrival_table", "#493021", "wood");
    const paper = c.surface("arrival_note", "#d5c7a1", "paper");
    const table = c.root("arrival_note_table", [2.7, 0, -2.6]);
    c.box(table, "arrival_table_top", [0.65, 0.06, 0.5], [0, 0.75, 0], wood);
    for (const x of [-0.25, 0.25])
      for (const z of [-0.18, 0.18])
        c.box(table, "arrival_table_leg", [0.055, 0.72, 0.055], [x, 0.36, z], wood);
    this.note = c.root("arrival_note", [2.7, 0.788, -2.6]);
    c.box(this.note, "arrival_note_paper", [0.24, 0.004, 0.3], [0, 0, 0], paper);
    // Raised ink strokes keep the note legible as a written prop under the lamp.
    for (let i = 0; i < 8; i++)
      c.box(
        this.note,
        "arrival_note_ink",
        [0.13 + (i % 3) * 0.018, 0.001, 0.002],
        [0, 0.003, -0.1 + i * 0.025],
        wood,
      );
    const telephone = (this.telephone = new WallTelephone(scene));
    this.phone = telephone.root;
    this.receiver = telephone.receiver;
    this.matches = c.root("arrival_blessed_matches", [-0.65, 3.614, -21.5]);
    c.box(this.matches, "arrival_matchbox", [0.095, 0.025, 0.065], [0, 0, 0], paper);
    const striker = c.mat("arrival_matchbox_striker", "#563529", 0.97);
    c.box(this.matches, "arrival_matchbox_drawer", [0.094, 0.021, 0.062], [0.0017, 0, 0], wood);
    for (const z of [-0.0328, 0.0328]) {
      c.box(this.matches, "arrival_matchbox_striker", [0.08, 0.014, 0.001], [0, 0, z], striker);
      for (let i = 0; i < 18; i++)
        c.box(
          this.matches,
          "arrival_matchbox_striker_grain",
          [0.001, 0.012, 0.0005],
          [-0.036 + i * 0.004, 0, z * 1.02],
          paper,
        );
    }
    const thread = c.surface("arrival_thread", "#8c352b", "cloth");
    for (const x of [-0.002, 0, 0.002])
      c.tube(
        this.matches,
        "arrival_matchbox_red_thread",
        [
          [x, -0.0128, -0.033],
          [x, 0.0135, -0.033],
          [x, 0.0135, 0.033],
          [x, -0.0128, 0.033],
          [x, -0.0128, -0.033],
        ],
        0.00055,
        thread,
      );
    c.sphere(
      this.matches,
      "arrival_matchbox_knot",
      [0.007, 0.003, 0.004],
      [0, 0.014, 0.009],
      thread,
    );
    for (const side of [-1, 1])
      c.tube(
        this.matches,
        "arrival_matchbox_thread_end",
        [
          [0, 0.014, 0.009],
          [side * 0.009, 0.014, 0.014],
          [side * 0.013, 0.0136, 0.012],
        ],
        0.0005,
        thread,
      );
  }

  updateTelephoneCord(heldEnd: Vector3 | null): void {
    this.telephone.updateTelephoneCord(heldEnd);
  }
}
