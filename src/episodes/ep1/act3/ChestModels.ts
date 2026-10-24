import type { Scene } from "@babylonjs/core/scene";
import type { Area } from "../../../core/AreaLoader";
import type { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import type { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { RelicCraft } from "./RelicCraft";
import { CHEST_ITEMS, type ChestItem } from "./ChestProgress";

export const CHEST_AT = [-4.5, 2.16, -12.52] as const;
/** A shallow coffer between the joists, with an actual opening through the visible floor. */
export class ChestModels {
  readonly craft: RelicCraft;
  readonly root: TransformNode;
  readonly planks: TransformNode;
  readonly chest: TransformNode;
  readonly lid: TransformNode;
  readonly token: TransformNode;
  readonly map: TransformNode;
  readonly slip: TransformNode;
  readonly pickups: Record<ChestItem, TransformNode>;
  private boards = 0;
  private opening = 0;
  constructor(scene: Scene, area: Area) {
    const b = (this.craft = new RelicCraft(scene));
    const wood = b.surface("chest_teak", "#55412b", "wood"),
      iron = b.surface("hammered_iron", "#35332e", "metal"),
      bronze = b.surface("bronze_token", "#a6834c", "metal");
    const dark = b.mat("keyhole", "#100f0c", 1),
      paper = b.surface("old_paper", "#d0bd95", "paper"),
      linen = b.surface("chest_linen", "#8c8067", "cloth");
    this.root = b.root("sok_floor_recess", CHEST_AT);
    this.planks = b.root("sok_lifted_floorboards", [0, 0, 0]);
    area.level.interactables
      .find((m) => m.name === "interact_loose_planks")
      ?.node.setEnabled(false);
    this.cutFloor(area, wood);
    // Recess walls leave the original walking support in place: Sora cannot fall through this shallow compartment.
    b.box(this.root, "recess_bottom", [0.96, 0.025, 0.84], [0, -0.055, 0], dark);
    for (const x of [-0.47, 0.47])
      b.box(this.root, "recess_endgrain", [0.025, 0.4, 0.84], [x, 0.15, 0], wood);
    for (const z of [-0.41, 0.41])
      b.box(this.root, "recess_joist_face", [0.96, 0.4, 0.02], [0, 0.15, z], wood);
    for (let k = 0; k < 4; k++) {
      const plank = b.root(
        `chest_loose_board_${k}`,
        [-4.5, 2.505, -12.205 - k * 0.21],
        this.planks,
      );
      b.box(plank, "split_floor_plank", [0.94, 0.045, 0.199], [0, 0, 0], wood);
      for (const x of [-0.4, 0.4]) {
        b.cylinder(plank, "old_floor_nail", 0.008, 0.003, [x, 0.024, 0.01], iron);
        b.box(plank, "nail_slot", [0.006, 0.001, 0.001], [x, 0.026, 0.01], dark);
      }
      b.tube(
        plank,
        "floor_splinter",
        [
          [-0.46, 0.025, 0.07],
          [-0.22, 0.026, 0.076],
          [-0.14, 0.025, 0.069],
        ],
        0.0012,
        dark,
      );
    }
    this.chest = b.root("sok_iron_chest", [0, 0, 0], this.root);
    b.box(this.chest, "chest_hollow_bottom", [0.77, 0.035, 0.56], [0, 0.018, 0], wood);
    for (const x of [-0.38, 0.38])
      b.box(this.chest, "chest_end_wall", [0.025, 0.27, 0.56], [x, 0.15, 0], wood);
    for (const z of [-0.27, 0.27]) {
      for (let k = 0; k < 3; k++)
        b.box(
          this.chest,
          "chest_teak_stave",
          [0.76, 0.085, 0.026],
          [0, 0.065 + k * 0.086, z],
          wood,
        );
      for (const x of [-0.28, 0.28]) {
        b.box(
          this.chest,
          "forged_iron_strap",
          [0.035, 0.29, 0.009],
          [x, 0.15, z + Math.sign(z) * 0.016],
          iron,
        );
        for (const y of [0.04, 0.12, 0.25])
          b.sphere(
            this.chest,
            "hand_set_rivet",
            [0.011, 0.011, 0.005],
            [x, y, z + Math.sign(z) * 0.022],
            iron,
          );
      }
    }
    for (const x of [-0.39, 0.39]) {
      b.box(this.chest, "chest_iron_corner", [0.012, 0.27, 0.035], [x, 0.15, 0.25], iron);
      const handle = b.ring(this.chest, "chest_drop_handle", 0.085, 0.008, [x, 0.145, 0], iron);
      handle.rotation.z = Math.PI / 2;
      for (const z of [-0.03, 0.03])
        b.sphere(this.chest, "handle_pivot", [0.016, 0.016, 0.016], [x, 0.19, z], iron);
    }
    b.box(this.chest, "chest_linen_lining", [0.69, 0.006, 0.46], [0, 0.042, 0], linen);
    b.box(this.chest, "warded_lock_plate", [0.085, 0.11, 0.013], [0, 0.19, 0.291], iron);
    const keyhole = b.cylinder(
      this.chest,
      "chest_keyhole_round",
      0.016,
      0.003,
      [0, 0.212, 0.3],
      dark,
    );
    keyhole.rotation.x = Math.PI / 2;
    b.box(this.chest, "chest_keyhole_ward", [0.01, 0.024, 0.003], [0, 0.196, 0.303], dark);
    for (const x of [-0.033, 0.033])
      for (const y of [0.15, 0.23])
        b.sphere(this.chest, "lock_rivet", [0.009, 0.009, 0.005], [x, y, 0.3], bronze);
    this.lid = b.root("chest_back_hinge", [0, 0.29, -0.29], this.chest);
    b.box(this.lid, "chest_lid_frame", [0.8, 0.035, 0.59], [0, 0.01, 0.29], wood);
    for (const x of [-0.28, 0.28]) {
      b.box(this.lid, "lid_iron_strap", [0.035, 0.009, 0.6], [x, 0.032, 0.29], iron);
      for (const z of [0.04, 0.25, 0.52])
        b.sphere(this.lid, "lid_rivet", [0.011, 0.005, 0.011], [x, 0.04, z], iron);
      const hinge = b.cylinder(
        this.chest,
        "chest_hinge_barrel",
        0.023,
        0.065,
        [x, 0.29, -0.286],
        iron,
      );
      hinge.rotation.z = Math.PI / 2;
    }
    b.box(this.lid, "lid_inner_stretcher", [0.7, 0.018, 0.025], [0, -0.018, 0.3], wood);
    this.token = b.root("bronze_token_pickup", [-0.235, 0.051, 0.075], this.chest);
    b.cylinder(this.token, "bronze_token_disc", 0.112, 0.008, [0, 0, 0], bronze);
    for (const d of [0.103, 0.084])
      b.ring(this.token, "token_concentric_engraving", d, 0.0015, [0, 0.005, 0], bronze);
    for (let i = 0; i < 8; i++) {
      const a = (i * Math.PI) / 4;
      const petal = b.sphere(
        this.token,
        "token_worn_petal",
        [0.012, 0.0015, 0.028],
        [Math.sin(a) * 0.025, 0.0055, Math.cos(a) * 0.025],
        bronze,
      );
      petal.rotation.y = a;
    }
    b.ring(this.token, "token_pendant_eye", 0.015, 0.003, [0, 0.003, -0.064], bronze);
    b.tube(
      this.token,
      "token_old_cord",
      [
        [0, 0.008, -0.064],
        [-0.05, 0.007, -0.095],
        [-0.07, 0.007, -0.03],
        [-0.06, 0.007, 0.045],
        [-0.03, 0.007, 0.08],
      ],
      0.002,
      linen,
    );
    this.map = b.root("sok_folded_map", [0.08, 0.047, -0.03], this.chest);
    const mapMat = b.mat("hand_drawn_map", "#ffffff", 1);
    mapMat.albedoTexture = this.mapTexture(b);
    for (let k = 0; k < 3; k++)
      b.box(this.map, "map_paper_layers", [0.255, 0.002, 0.19], [0, k * 0.002, 0], paper);
    b.box(this.map, "map_ink_face", [0.252, 0.001, 0.188], [0, 0.007, 0], mapMat);
    for (const x of [-0.042, 0.042])
      b.box(this.map, "map_fold_ridge", [0.0015, 0.0015, 0.182], [x, 0.008, 0], paper);
    this.map.rotation.y = -0.16;
    this.slip = b.root("sok_sealed_slip", [0.22, 0.05, 0.13], this.chest);
    for (let k = 0; k < 3; k++)
      b.box(this.slip, "unread_folded_paper", [0.13, 0.002, 0.072], [0, k * 0.002, 0], paper);
    const wax = b.mat("slip_wax", "#68362c", 0.82);
    b.box(
      this.slip,
      "closed_paper_flap",
      [0.12, 0.002, 0.033],
      [0, 0.007, -0.012],
      paper,
    ).rotation.y = 0.025;
    b.cylinder(this.slip, "blank_wax_seal", 0.021, 0.003, [0.015, 0.009, -0.004], wax);
    b.tube(
      this.slip,
      "slip_red_thread",
      [
        [-0.064, 0.009, 0.013],
        [0, 0.01, 0.013],
        [0.064, 0.008, 0.013],
      ],
      0.001,
      wax,
    );
    this.slip.rotation.y = 0.18;
    this.pickups = { bronze_token: this.token, seal_map: this.map, folded_slip: this.slip };
    area.container.meshes.push(...b.meshes);
  }
  get planksReady(): boolean {
    return this.boards > 0.98;
  }
  get lidReady(): boolean {
    return this.opening > 0.95;
  }
  restore(planks: boolean, unlocked: boolean, taken: (item: ChestItem) => boolean): void {
    this.boards = Number(planks);
    this.opening = Number(unlocked);
    this.update(0, planks, unlocked, taken);
  }
  update(
    dt: number,
    planks: boolean,
    unlocked: boolean,
    taken: (item: ChestItem) => boolean,
  ): void {
    const ease = 1 - Math.exp(-dt * 4);
    this.boards += (Number(planks) - this.boards) * ease;
    this.opening += (Number(unlocked) - this.opening) * ease;
    // Slide and lift the four boards in a staggered stack beside the recess.
    this.planks.getChildren().forEach((node, i) => {
      const board = node as TransformNode;
      board.position.x = -4.5 - this.boards * 0.98;
      board.position.y = 2.505 + this.boards * (0.045 + i * 0.048);
      board.rotation.z = this.boards * 0.07;
    });
    this.lid.rotation.x = -this.opening * 1.82;
    for (const item of CHEST_ITEMS) this.pickups[item].setEnabled(unlocked && !taken(item));
  }
  private cutFloor(area: Area, wood: PBRMaterial): void {
    const b = this.craft;
    for (const mesh of area.container.meshes) {
      if (!/^floor_board_(10|11|12|13)(\.|$)/.test(mesh.name) && !/^joist_13(\.|$)/.test(mesh.name))
        continue;
      mesh.computeWorldMatrix(true);
      const bounds = mesh.getBoundingInfo().boundingBox,
        min = bounds.minimumWorld,
        max = bounds.maximumWorld;
      if (/^floor_board_/.test(mesh.name)) {
        const material = mesh.material as PBRMaterial | null;
        for (const [a, z] of [
          [min.x, -4.98],
          [-4.03, max.x],
        ])
          b.box(
            this.root,
            "floor_board_trim",
            [z - a, max.y - min.y, max.z - min.z],
            [
              (a + z) / 2 - CHEST_AT[0],
              (min.y + max.y) / 2 - CHEST_AT[1],
              (min.z + max.z) / 2 - CHEST_AT[2],
            ],
            material ?? wood,
          );
      } else {
        for (const [a, z] of [
          [min.z, -12.94],
          [-12.1, max.z],
        ])
          b.box(
            this.root,
            "joist_trim",
            [max.x - min.x, max.y - min.y, z - a],
            [
              (min.x + max.x) / 2 - CHEST_AT[0],
              (min.y + max.y) / 2 - CHEST_AT[1],
              (a + z) / 2 - CHEST_AT[2],
            ],
            wood,
          );
      }
      mesh.setEnabled(false);
    }
  }
  private mapTexture(b: RelicCraft) {
    return b.painted("sok_map", (c) => {
      c.fillStyle = "#cbb88e";
      c.fillRect(0, 0, 512, 512);
      c.strokeStyle = "#776e58";
      c.lineWidth = 3;
      c.beginPath();
      c.moveTo(340, 0);
      c.bezierCurveTo(220, 130, 420, 200, 275, 330);
      c.bezierCurveTo(160, 430, 280, 470, 210, 512);
      c.stroke();
      c.strokeStyle = "#716247";
      c.lineWidth = 1.5;
      for (let i = 0; i < 5; i++) {
        c.beginPath();
        c.moveTo(20, 70 + i * 84);
        c.bezierCurveTo(140, 30 + i * 90, 390, 120 + i * 70, 500, 55 + i * 92);
        c.stroke();
      }
      c.setLineDash([5, 7]);
      c.beginPath();
      c.moveTo(140, 340);
      c.lineTo(220, 260);
      c.lineTo(375, 205);
      c.lineTo(410, 100);
      c.stroke();
      c.setLineDash([]);
      for (const [x, y] of [
        [140, 340],
        [220, 260],
        [375, 205],
        [410, 100],
        [120, 100],
      ]) {
        c.beginPath();
        c.arc(x, y, 8, 0, Math.PI * 2);
        c.stroke();
      }
      c.font = "italic 17px serif";
      c.fillStyle = "#5c5039";
      c.fillText("Battambang", 28, 38);
      c.fillText("the village", 45, 380);
      c.lineWidth = 1;
      c.strokeRect(14, 14, 484, 484);
      for (const x of [171, 342]) {
        c.fillStyle = "rgba(75,51,25,.12)";
        c.fillRect(x, 0, 3, 512);
      }
    });
  }
}
