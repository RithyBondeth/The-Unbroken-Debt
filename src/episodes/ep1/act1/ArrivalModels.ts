import type { Scene } from "@babylonjs/core/scene";
import { RelicCraft } from "../act3/RelicCraft";

/** The family have left: their note, a hall telephone and a prepared matchbox. */
export class ArrivalModels {
  readonly note;
  readonly phone;
  readonly receiver;
  readonly matches;
  constructor(scene: Scene) {
    const c = new RelicCraft(scene);
    const wood = c.surface("arrival_table", "#493021", "wood");
    const paper = c.surface("arrival_note", "#d5c7a1", "paper");
    const black = c.mat("arrival_phone", "#191d19", 0.45);
    const brass = c.mat("arrival_dial", "#94805a", 0.5, 0.65);
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
    this.phone = c.root("arrival_phone", [2.75, 3.7, -17.2]);
    c.box(this.phone, "arrival_phone_back", [0.12, 0.38, 0.26], [0, 0, 0], black);
    c.box(this.phone, "arrival_phone_mount", [0.18, 0.3, 0.22], [0.14, 0, 0], black);
    const dial = c.cylinder(
      this.phone,
      "arrival_phone_dial",
      0.19,
      0.016,
      [-0.07, -0.04, 0],
      brass,
    );
    dial.rotation.z = Math.PI / 2;
    this.receiver = c.root("arrival_receiver", [-0.13, 0.11, 0], this.phone);
    c.box(this.receiver, "arrival_receiver_handle", [0.05, 0.05, 0.28], [0, 0, 0], black);
    for (const z of [-0.14, 0.14])
      c.sphere(this.receiver, "arrival_receiver_cup", [0.1, 0.09, 0.1], [0, 0, z], black);
    c.tube(
      this.phone,
      "arrival_phone_cord",
      [
        [-0.1, 0.1, 0.14],
        [-0.16, -0.25, 0.14],
        [-0.1, -0.32, 0.05],
        [0, -0.18, 0.05],
      ],
      0.008,
      black,
    );
    this.matches = c.root("arrival_blessed_matches", [-0.65, 3.614, -17.5]);
    c.box(this.matches, "arrival_matchbox", [0.095, 0.025, 0.065], [0, 0, 0], paper);
    c.box(
      this.matches,
      "arrival_matchbox_red_thread",
      [0.012, 0.027, 0.067],
      [0, 0, 0],
      c.mat("arrival_thread", "#8c352b"),
    );
  }
}
