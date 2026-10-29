import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { CreateSphere } from "@babylonjs/core/Meshes/Builders/sphereBuilder";
import { VertexData } from "@babylonjs/core/Meshes/mesh.vertexData";
import type { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import type { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import type { RelicCraft } from "../act3/RelicCraft";

type XYZ = [number, number, number];

/** Solid joinery and chisel relief. All measurements are metres, not decals. */
export class ShrineWoodwork {
  constructor(
    private readonly c: RelicCraft,
    private readonly root: TransformNode,
  ) {}

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

  /** Raised flame-leaf with a bevelled perimeter and a convex carved spine. */
  leaf(at: XYZ, length: number, width: number, angle: number, material: PBRMaterial): void {
    const outline: [number, number][] = [];
    const steps = 12;
    for (const side of [-1, 1])
      for (let j = 0; j <= steps; j++) {
        const t = side < 0 ? j / steps : 1 - j / steps;
        const lobe = Math.sin(Math.PI * t) ** 0.75 * (0.72 + 0.28 * Math.cos(t * Math.PI * 6));
        outline.push([side * width * 0.5 * lobe + width * 0.23 * t ** 4, t * length]);
      }
    const positions: number[] = [],
      indices: number[] = [],
      uvs: number[] = [];
    const ca = Math.cos(angle),
      sa = Math.sin(angle),
      count = outline.length;
    const place = (x: number, y: number, z: number) => {
      positions.push(at[0] + x * ca - y * sa, at[1] + x * sa + y * ca, at[2] + z);
      uvs.push(x / Math.max(width, 0.001) + 0.5, y / length);
    };
    for (const [scale, z] of [
      [1, 0],
      [0.91, 0.005],
      [0.72, 0.013],
    ])
      for (const [x, y] of outline) place(x * scale, length * 0.5 + (y - length * 0.5) * scale, z);
    for (let ring = 0; ring < 2; ring++)
      for (let j = 0; j < count; j++) {
        const a = ring * count + j,
          b = ring * count + ((j + 1) % count);
        indices.push(a, b, a + count, b, b + count, a + count);
      }
    const centre = positions.length / 3;
    place(0, length * 0.5, 0.021);
    for (let j = 0; j < count; j++)
      indices.push(centre, count * 2 + j, count * 2 + ((j + 1) % count));
    this.surface("phra_phum_chiselled_leaf_relief", positions, indices, uvs, material);
  }

  /** Solid bevelled timber arch and connected botanical relief, rather than
   * a round gold tube and identical floating motifs on a flat doorway. */
  entrance(timber: PBRMaterial, relief: PBRMaterial, gilt: PBRMaterial, shadow: PBRMaterial): void {
    const c = this.c;
    for (const side of [-1, 1]) {
      c.box(
        this.root,
        "phra_phum_recessed_jamb_panel",
        [0.108, 0.63, 0.055],
        [side * 0.274, 1.605, 0.264],
        timber,
      );
      for (const offset of [-0.046, 0.046])
        c.box(
          this.root,
          "phra_phum_jamb_rebate",
          [0.005, 0.59, 0.003],
          [side * 0.274 + offset, 1.605, 0.293],
          shadow,
        );
      const path: XYZ[] = [];
      for (let k = 0; k <= 10; k++) path.push([side * 0.202, 1.29 + k * 0.033, 0.3]);
      for (let k = 1; k <= 18; k++) {
        const t = k / 18;
        path.push([side * 0.202 * (1 - t), 1.62 + 0.25 * t + Math.sin(t * Math.PI) * 0.028, 0.3]);
      }
      const positions: number[] = [],
        indices: number[] = [],
        uvs: number[] = [];
      // A stepped chisel profile across each solid band: dark rebate, broad
      // bevel, raised centre, narrow worn arris, and a thick rear face.
      const profile = [
        [-0.014, -0.022],
        [-0.014, 0.005],
        [-0.009, 0.015],
        [0.018, 0.015],
        [0.027, 0.005],
        [0.027, -0.022],
      ];
      for (let k = 0; k < path.length; k++) {
        const a = path[Math.max(0, k - 1)],
          b = path[Math.min(path.length - 1, k + 1)];
        const length = Math.hypot(b[0] - a[0], b[1] - a[1]);
        const nx = (side * (b[1] - a[1])) / length,
          ny = (-side * (b[0] - a[0])) / length;
        for (const [across, depth] of profile) {
          positions.push(path[k][0] + nx * across, path[k][1] + ny * across, path[k][2] + depth);
          uvs.push(across * 12, k / 16);
        }
        if (k)
          for (let j = 0; j < profile.length; j++) {
            const a = (k - 1) * 6 + j,
              b = (k - 1) * 6 + ((j + 1) % 6);
            indices.push(a, a + 6, b, b, a + 6, b + 6);
          }
      }
      // Mirroring the band also mirrors its winding. Both front faces must
      // face the lantern; otherwise one jamb becomes a black silhouette.
      if (side < 0)
        for (let i = 0; i < indices.length; i += 3)
          [indices[i + 1], indices[i + 2]] = [indices[i + 2], indices[i + 1]];
      this.surface("phra_phum_bevelled_timber_door_arch", positions, indices, uvs, relief);
      // Aged gold survives only as a fine broken line on the inside arris.
      c.tube(this.root, "phra_phum_arch_remaining_gold_leaf", path.slice(10), 0.0015, gilt);
      const stem: XYZ[] = Array.from({ length: 49 }, (_, k) => {
        const t = k / 48;
        return [side * (0.273 + Math.sin(t * Math.PI * 5) * 0.019), 1.32 + t * 0.53, 0.299];
      });
      c.tube(this.root, "phra_phum_connected_carved_vine", stem, 0.0038, relief);
      for (let k = 0; k < 9; k++) {
        const t = (k + 0.3) / 9,
          alternate = k % 2 ? -1 : 1;
        const x = side * (0.273 + Math.sin(t * Math.PI * 5) * 0.019);
        this.leaf(
          [x, 1.32 + t * 0.53, 0.298],
          0.036 + (k % 3) * 0.006,
          0.021,
          side * alternate * 0.88,
          relief,
        );
      }
      // Pierced spiral at the foot of each vine and a larger terminal bud.
      c.tube(
        this.root,
        "phra_phum_jamb_scroll",
        Array.from({ length: 33 }, (_, k) => {
          const t = k / 32,
            angle = t * Math.PI * 2.4,
            radius = 0.031 * (1 - t * 0.8);
          return [
            side * (0.273 + Math.cos(angle) * radius),
            1.355 + Math.sin(angle) * radius,
            0.302,
          ] as XYZ;
        }),
        0.004,
        relief,
      );
      this.leaf([side * 0.273, 1.82, 0.3], 0.074, 0.038, side * 0.1, relief);
      c.box(
        this.root,
        "phra_phum_jamb_foot_block",
        [0.13, 0.043, 0.085],
        [side * 0.274, 1.292, 0.274],
        relief,
      );
      c.box(
        this.root,
        "phra_phum_jamb_capital",
        [0.13, 0.033, 0.08],
        [side * 0.274, 1.905, 0.27],
        relief,
      );
    }
    c.box(this.root, "phra_phum_carved_lintel", [0.76, 0.095, 0.065], [0, 1.91, 0.277], timber);
    for (const side of [-1, 1]) {
      const curl: XYZ[] = Array.from({ length: 41 }, (_, k) => {
        const t = k / 40,
          a = t * Math.PI * 2.4,
          r = 0.075 * (1 - t * 0.8);
        return [side * (0.105 + Math.cos(a) * r), 1.906 + Math.sin(a) * r * 0.37, 0.319];
      });
      c.tube(this.root, "phra_phum_lintel_floral_scroll", curl, 0.006, relief);
      this.leaf([side * 0.07, 1.877, 0.321], 0.07, 0.033, side * -0.7, relief);
      for (let k = 0; k < 8; k++) {
        const y = 1.33 + k * 0.072;
        this.leaf([side * 0.31, y, 0.306], 0.056, 0.024, side * -0.22, relief);
      }
    }
    this.leaf([0, 1.875, 0.325], 0.075, 0.045, 0, gilt);
    for (const [y, width, depth] of [
      [1.27, 0.69, 0.13],
      [1.295, 0.6, 0.1],
    ])
      c.box(this.root, "phra_phum_worn_door_sill", [width, 0.025, depth], [0, y, 0.27], timber);
  }

  /** A tapered, bevelled flame blade. Unlike a round tube, its broad carved
   * face and thin curling tip read against the sky like the reference. */
  private flameBlade(path: XYZ[], width: number, material: PBRMaterial): void {
    const controls = path;
    path = [];
    for (let segment = 0; segment < controls.length - 1; segment++)
      for (let j = 0; j < 6; j++) {
        const t = j / 6,
          q: XYZ = [0, 0, 0];
        for (let axis = 0; axis < 3; axis++) {
          const a = controls[Math.max(0, segment - 1)][axis],
            b = controls[segment][axis],
            c = controls[segment + 1][axis],
            d = controls[Math.min(controls.length - 1, segment + 2)][axis];
          q[axis] =
            0.5 *
            (2 * b +
              (-a + c) * t +
              (2 * a - 5 * b + 4 * c - d) * t * t +
              (-a + 3 * b - 3 * c + d) * t * t * t);
        }
        path.push(q);
      }
    path.push(controls[controls.length - 1]);
    const positions: number[] = [],
      indices: number[] = [],
      uvs: number[] = [];
    for (let k = 0; k < path.length; k++) {
      const a = path[Math.max(0, k - 1)],
        b = path[Math.min(path.length - 1, k + 1)];
      const length = Math.hypot(b[0] - a[0], b[1] - a[1]);
      const nx = (b[1] - a[1]) / length,
        ny = -(b[0] - a[0]) / length;
      const w = width * (1 - k / (path.length - 1)) ** 0.75 + 0.0004;
      for (const [across, z] of [
        [-1, -0.012],
        [-1, 0.002],
        [-0.65, 0.015],
        [0.65, 0.015],
        [1, 0.002],
        [1, -0.012],
      ]) {
        positions.push(path[k][0] + nx * w * across, path[k][1] + ny * w * across, path[k][2] + z);
        uvs.push(across * 0.5 + 0.5, k / 5);
      }
      if (k)
        for (let j = 0; j < 6; j++) {
          const a = (k - 1) * 6 + j,
            b = (k - 1) * 6 + ((j + 1) % 6);
          indices.push(a, a + 6, b, b, a + 6, b + 6);
        }
    }
    this.surface("phra_phum_carved_flame_blade", positions, indices, uvs, material);
  }

  /** Solid pediment with a raised tree-of-flames, curling stems and a bead
   * border. Three stepped gables repeat this densely carved front. */
  private pediment(
    half: number,
    base: number,
    rise: number,
    z: number,
    panel: PBRMaterial,
    relief: PBRMaterial,
    gilt: PBRMaterial,
  ): void {
    const outline: XYZ[] = [
      [-half * 0.91, base, z],
      [half * 0.91, base, z],
    ];
    for (let k = 0; k <= 24; k++) {
      const x = half * 0.91 * (1 - k / 12);
      outline.push([x, base + rise * (1 - Math.abs(x) / half) ** 1.15 - 0.033, z]);
    }
    const positions = [0, base + rise * 0.29, z],
      indices: number[] = [],
      uvs = [0.5, 0.3];
    for (const [x, y, zz] of outline) {
      positions.push(x, y, zz);
      uvs.push((x / half) * 0.5 + 0.5, (y - base) / rise);
    }
    for (let k = 0; k < outline.length; k++) indices.push(0, ((k + 1) % outline.length) + 1, k + 1);
    this.surface("phra_phum_solid_carved_pediment", positions, indices, uvs, panel);
    const top = base + rise * 0.83;
    this.flameBlade(
      [
        [0, base + 0.025, z + 0.01],
        [0, base + rise * 0.35, z + 0.01],
        [-0.008, base + rise * 0.62, z + 0.01],
        [0.014, top, z + 0.01],
      ],
      0.025,
      relief,
    );
    for (const side of [-1, 1]) {
      for (let row = 0; row < 3; row++) {
        const x = half * (0.18 + row * 0.19),
          y = base + rise * (0.12 + (2 - row) * 0.055);
        const curl: XYZ[] = Array.from({ length: 33 }, (_, k) => {
          const t = k / 32,
            a = t * Math.PI * 2.45,
            radius = half * (0.11 - row * 0.018) * (1 - t * 0.76);
          return [side * (x + Math.cos(a) * radius), y + Math.sin(a) * radius, z + 0.022];
        });
        this.c.tube(this.root, "phra_phum_dense_gable_scroll", curl, 0.005, relief);
        this.leaf(
          [side * x, y, z + 0.019],
          rise * (0.34 - row * 0.055),
          half * 0.09,
          side * -0.52,
          relief,
        );
        this.leaf(
          [side * (x + 0.025), y - 0.025, z + 0.021],
          rise * 0.18,
          half * 0.063,
          side * 1.1,
          relief,
        );
      }
      // Feathered flame branches fill the upper triangle, like the heavily
      // worked pediments in the supplied reference rather than a bare board.
      for (let level = 0; level < 4; level++) {
        const y = base + rise * (0.18 + level * 0.13),
          spread = half * (0.51 - level * 0.115);
        const stem: XYZ[] = [
          [side * 0.012, y - 0.025, z + 0.019],
          [side * spread * 0.38, y + 0.01, z + 0.025],
          [side * spread, y + 0.045, z + 0.025],
        ];
        this.c.tube(this.root, "phra_phum_ascending_flame_branch", stem, 0.0045, relief);
        this.leaf(
          [side * spread * 0.62, y + 0.018, z + 0.023],
          rise * (0.23 - level * 0.022),
          half * 0.075,
          side * -0.68,
          relief,
        );
        this.leaf(
          [side * spread * 0.88, y + 0.037, z + 0.023],
          rise * 0.145,
          half * 0.053,
          side * -0.45,
          relief,
        );
      }
      for (let k = 1; k < 10; k++) {
        const u = k / 11;
        const bead = this.c.finish(
          CreateSphere("phra_phum_pediment_bead", { diameter: 1, segments: 6 }, this.c.scene),
          this.root,
          [side * half * u, base + 0.009, z + 0.019],
          gilt,
        );
        bead.scaling.set(0.012, 0.012, 0.008);
      }
    }
  }

  /** Timber gable, pierced scrolls and individual overlapping, chipped shingles. */
  roof(
    half: number,
    depth: number,
    base: number,
    rise: number,
    tile: PBRMaterial,
    timber: PBRMaterial,
    carving: PBRMaterial,
    gilt: PBRMaterial,
  ): void {
    const c = this.c;
    const h = (u: number) => base + rise * (1 - u) ** 1.15 + 0.035 * u ** 8;
    for (const side of [-1, 1]) {
      // Shingles have top, underside and end grain. Courses overlap downhill.
      for (let row = 0; row < 5; row++)
        for (let col = 0; col < 12; col++) {
          const u0 = row / 5,
            u1 = Math.min(1.025, (row + 1) / 5 + 0.035);
          const z0 = (col / 12 - 0.5) * depth + 0.0008;
          const z1 = ((col + 1) / 12 - 0.5) * depth - 0.0008;
          const positions: number[] = [],
            indices: number[] = [],
            uvs: number[] = [];
          const chipped = row === 4 && (col === 3 || col === 9);
          for (let layer = 0; layer < 2; layer++)
            for (let across = 0; across < 2; across++)
              for (let j = 0; j <= 4; j++) {
                const t = j / 4;
                const u = Math.min(
                  1.025,
                  u0 + (u1 - u0) * t - (chipped && across === 1 && j === 4 ? 0.045 : 0),
                );
                const warp = Math.sin(col * 3.7 + row) * 0.0012 * t;
                positions.push(
                  side * half * u,
                  h(Math.min(1, u)) + 0.008 + (1 - t) * 0.004 + warp - layer * 0.008,
                  across ? z1 : z0,
                );
                uvs.push((col + across) / 4, row / 3 + t * 0.36);
              }
          for (let j = 0; j < 4; j++) {
            indices.push(j, j + 1, j + 5, j + 1, j + 6, j + 5);
            indices.push(j + 10, j + 15, j + 11, j + 11, j + 15, j + 16);
            indices.push(j, j + 10, j + 1, j + 1, j + 10, j + 11);
            indices.push(j + 5, j + 6, j + 15, j + 6, j + 16, j + 15);
          }
          indices.push(0, 5, 10, 5, 15, 10, 4, 14, 9, 9, 14, 19);
          tile.backFaceCulling = false;
          this.surface("phra_phum_overlapping_roof_shingle", positions, indices, uvs, tile);
        }
      // Five true rafters, with smaller cross purlins visible beneath the eaves.
      for (let k = 0; k < 5; k++) {
        const z = (k / 4 - 0.5) * depth * 0.96;
        const a: XYZ = [0, base + rise - 0.018, z],
          b: XYZ = [side * half, base + 0.012, z];
        const length = Math.hypot(b[0] - a[0], b[1] - a[1]);
        const beam = c.box(
          this.root,
          "phra_phum_exposed_roof_rafter",
          [length, 0.024, 0.027],
          [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2, z],
          timber,
        );
        beam.rotation.z = Math.atan2(b[1] - a[1], b[0] - a[0]);
      }
      for (const u of [0.28, 0.68, 0.97])
        c.box(
          this.root,
          "phra_phum_roof_purlin",
          [0.022, 0.024, depth * 1.03],
          [side * half * u, h(u) - 0.028, 0],
          timber,
        );
      for (const end of [-1, 1]) {
        const z = end * (depth * 0.5 + 0.009);
        const path: XYZ[] = Array.from({ length: 13 }, (_, i) => [
          (side * half * i) / 12,
          h(i / 12),
          z,
        ]);
        const board: number[] = [],
          boardIndices: number[] = [],
          boardUVs: number[] = [];
        for (let i = 0; i < path.length; i++) {
          const [x, y, zz] = path[i];
          for (const dz of [0.01, -0.01])
            for (const dy of [0.018, -0.067]) {
              board.push(x, y + dy, zz + dz);
              boardUVs.push(i / 6, dy > 0 ? 0 : 0.15);
            }
          if (i < path.length - 1) {
            const a = i * 4;
            boardIndices.push(
              a,
              a + 1,
              a + 4,
              a + 1,
              a + 5,
              a + 4,
              a + 2,
              a + 6,
              a + 3,
              a + 3,
              a + 6,
              a + 7,
              a,
              a + 4,
              a + 2,
              a + 2,
              a + 4,
              a + 6,
              a + 1,
              a + 3,
              a + 5,
              a + 3,
              a + 7,
              a + 5,
            );
          }
        }
        this.surface("phra_phum_solid_carved_bargeboard", board, boardIndices, boardUVs, carving);
        c.tube(
          this.root,
          "phra_phum_gilt_hairline",
          path.map(([x, y, zz]) => [x, y + 0.019, zz] as XYZ),
          0.003,
          gilt,
        );
        this.flameBlade(
          [
            [side * (half - 0.09), base + 0.015, z + 0.012],
            [side * (half - 0.008), base + 0.09, z + 0.012],
            [side * (half + 0.035), base + 0.215, z + 0.012],
            [side * (half + 0.032), base + 0.335, z + 0.012],
            [side * (half + 0.004), base + 0.425, z + 0.012],
          ],
          0.031,
          carving,
        );
        if (end > 0) {
          for (let k = 1; k < 7; k++) {
            const u = k / 8;
            this.leaf(
              [side * half * u, h(u) - 0.026, z + 0.013],
              0.065,
              0.035,
              side * 1.04,
              carving,
            );
          }
          // Curling scroll is pierced: there is real darkness between its turns.
          const scroll: XYZ[] = Array.from({ length: 25 }, (_, j) => {
            const a = (j / 24) * Math.PI * 2.2,
              r = 0.055 * (1 - j / 32);
            return [side * (0.115 + Math.cos(a) * r), base + 0.075 + Math.sin(a) * r, z + 0.012];
          });
          c.tube(this.root, "phra_phum_pierced_gable_scroll", scroll, 0.006, carving);
        }
      }
    }
    // Separate ridge caps bridge the apex; their end faces catch the lamp.
    for (let k = 0; k < 10; k++) {
      const z0 = (k / 10 - 0.53) * depth,
        z1 = ((k + 1) / 10 - 0.53) * depth + 0.006;
      const positions: number[] = [],
        indices: number[] = [],
        uvs: number[] = [];
      for (const z of [z0, z1])
        for (let j = 0; j <= 8; j++) {
          const a = (j / 8) * Math.PI;
          positions.push(Math.cos(a) * 0.032, base + rise + Math.sin(a) * 0.032 + 0.005, z);
          uvs.push(j / 8, k / 4);
        }
      for (let j = 0; j < 8; j++) indices.push(j, j + 9, j + 1, j + 1, j + 9, j + 10);
      this.surface("phra_phum_separate_ridge_cap", positions, indices, uvs, carving);
    }
    // The reference has closed, richly carved gables, not exposed roof voids.
    this.pediment(half, base + 0.025, rise - 0.03, depth * 0.5 + 0.017, timber, carving, gilt);
    this.c.box(
      this.root,
      "phra_phum_stepped_gable_cornice",
      [half * 1.92, 0.035, 0.065],
      [0, base + 0.008, depth * 0.5 + 0.012],
      carving,
    );
    for (let k = 0; k < 13; k++) {
      const x = (k / 12 - 0.5) * half * 1.76;
      this.leaf([x, base - 0.065, depth * 0.5 + 0.045], 0.07, 0.032, k % 2 ? 0.16 : -0.16, carving);
    }
  }
}
