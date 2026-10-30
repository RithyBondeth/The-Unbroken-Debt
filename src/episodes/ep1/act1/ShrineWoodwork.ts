import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { VertexData } from "@babylonjs/core/Meshes/mesh.vertexData";
import type { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import type { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import type { RelicCraft } from "../act3/RelicCraft";

/** Plain household joinery, measured in metres. */
export class ShrineWoodwork {
  constructor(
    private readonly c: RelicCraft,
    private readonly root: TransformNode,
  ) {}

  /** A household-built shelter: one plain gable, reclaimed boards and a
   * rectangular opening. The small spirit house has no ceremonial roof tiers. */
  household(timber: PBRMaterial, roof: PBRMaterial, repair: PBRMaterial): void {
    const c = this.c,
      half = 0.61,
      rise = 0.39,
      base = 1.98,
      angle = Math.atan2(rise, half),
      slope = Math.hypot(half, rise);
    for (const side of [-1, 1]) {
      for (let k = 0; k < 10; k++) {
        const board = c.box(
          this.root,
          "phra_phum_salvaged_roof_board",
          [slope + 0.035, 0.022, 0.11],
          [(side * half) / 2, base + rise / 2 + Math.sin(k * 3.1) * 0.003, (k - 4.5) * 0.101],
          k === 7 && side === -1 ? repair : roof,
        );
        board.rotation.z = -side * angle;
      }
      for (const z of [-0.52, 0.52]) {
        const fascia = c.box(
          this.root,
          "phra_phum_plain_roof_fascia",
          [slope + 0.05, 0.045, 0.035],
          [(side * half) / 2, base + rise / 2 - 0.012, z],
          timber,
        );
        fascia.rotation.z = -side * angle;
      }
      c.box(
        this.root,
        "phra_phum_plain_door_jamb",
        [0.049, 0.64, 0.05],
        [side * 0.247, 1.61, 0.287],
        timber,
      );
      c.box(
        this.root,
        "phra_phum_door_repair_cleat",
        [0.083, 0.022, 0.019],
        [side * 0.247, side < 0 ? 1.43 : 1.77, 0.322],
        repair,
      );
    }
    c.box(this.root, "phra_phum_plain_door_lintel", [0.61, 0.062, 0.06], [0, 1.943, 0.287], timber);
    c.box(this.root, "phra_phum_plain_threshold", [0.56, 0.034, 0.07], [0, 1.3, 0.29], timber);
    c.box(
      this.root,
      "phra_phum_roof_ridge_board",
      [0.06, 0.028, 1.08],
      [0, base + rise + 0.022, 0],
      roof,
    );
    // Three individual gable boards close the triangular end, without relief.
    for (let k = 0; k < 3; k++) {
      const y0 = base + k * 0.115,
        y1 = y0 + 0.11,
        w0 = half * (1 - (y0 - base) / rise),
        w1 = half * (1 - (y1 - base) / rise);
      this.surface(
        "phra_phum_plain_gable_board",
        [-w0, y0, 0.512, w0, y0, 0.512, w1, y1, 0.512, -w1, y1, 0.512],
        [0, 2, 1, 0, 3, 2],
        [0, 0, 1, 0, 1, 1, 0, 1],
        timber,
      );
    }
  }

  private surface(
    name: string,
    positions: number[],
    indices: number[],
    uvs: number[],
    material: PBRMaterial,
  ): Mesh {
    const normals: number[] = [];
    VertexData.ComputeNormals(positions, indices, normals);
    const data = new VertexData();
    data.positions = positions;
    data.indices = indices;
    data.normals = normals;
    data.uvs = uvs;
    const mesh = new Mesh(name, this.c.scene);
    data.applyToMesh(mesh);
    mesh.parent = this.root;
    mesh.material = material;
    this.c.meshes.push(mesh);
    return mesh;
  }
}
