import type { Scene } from "@babylonjs/core/scene";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { VertexData } from "@babylonjs/core/Meshes/mesh.vertexData";
import { CreatePlane } from "@babylonjs/core/Meshes/Builders/planeBuilder";
import type { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import type { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { RelicCraft } from "../act3/RelicCraft";
import { seededRandom } from "../../../audio/synth";

/** Wall-mounted rotary phone. The front faces into the hall along negative X. */
export class WallTelephone {
  readonly root: TransformNode;
  readonly receiver: TransformNode;

  constructor(scene: Scene) {
    const c = new RelicCraft(scene);
    const black = c.mat("telephone_bakelite", "#24201b", 0.29);
    black.albedoTexture = c.painted("telephone_bakelite", (ctx) => {
      const random = seededRandom(1932);
      ctx.fillStyle = "#b2aaa0";
      ctx.fillRect(0, 0, 512, 512);
      for (let k = 0; k < 1200; k++) {
        ctx.strokeStyle = `rgba(42,33,24,${random() * 0.09})`;
        const x = random() * 512,
          y = random() * 512;
        ctx.beginPath();
        ctx.moveTo(x, y);
        ctx.lineTo(x + random() * 9, y + random() * 2);
        ctx.stroke();
      }
    });
    const brass = c.surface("telephone_aged_brass", "#8c7146", "metal");
    brass.roughness = 0.43;
    const edge = c.mat("telephone_brass_edges", "#b79b64", 0.35, 0.78);
    const dark = c.mat("telephone_recesses", "#070806", 0.9);
    const cord = c.surface("telephone_braided_cord", "#302b22", "cloth");
    const wood = c.surface("telephone_mounting_board", "#38271d", "wood");
    this.root = c.root("arrival_phone", [2.75, 3.7, -17.2]);
    this.housing(c, this.root, "telephone_mounting_board", 0.166, 0.048, 0.46, 0.31, 0.018, wood);
    this.housing(c, this.root, "telephone_case_seam", 0.091, 0.11, 0.39, 0.275, 0.025, dark);
    this.housing(c, this.root, "telephone_bakelite_case", 0.025, 0.105, 0.375, 0.264, 0.03, black);

    const faceCylinder = (
      name: string,
      diameter: number,
      depth: number,
      x: number,
      y: number,
      z: number,
      material: PBRMaterial,
      parent = this.root,
    ) => {
      const mesh = c.cylinder(parent, name, diameter, depth, [x, y, z], material);
      mesh.rotation.z = Math.PI / 2;
      return mesh;
    };
    const faceRing = (
      name: string,
      diameter: number,
      thickness: number,
      x: number,
      y: number,
      z: number,
      material: PBRMaterial,
      parent = this.root,
    ) => {
      const mesh = c.ring(parent, name, diameter, thickness, [x, y, z], material);
      mesh.rotation.z = Math.PI / 2;
      return mesh;
    };
    for (const y of [-0.204, 0.204]) {
      faceCylinder("telephone_mount_screw", 0.013, 0.003, 0.139, y, 0, brass);
      c.box(this.root, "telephone_mount_screw_slot", [0.001, 0.002, 0.009], [0.137, y, 0], dark);
    }
    for (const z of [-0.105, 0.105]) {
      faceCylinder("telephone_case_screw", 0.008, 0.003, -0.031, -0.15, z, edge);
      c.box(
        this.root,
        "telephone_case_screw_slot",
        [0.001, 0.0015, 0.005],
        [-0.033, -0.15, z],
        dark,
      );
    }
    faceCylinder("arrival_phone_dial", 0.229, 0.022, -0.039, -0.025, 0, brass);
    faceRing("telephone_dial_outer_bezel", 0.221, 0.005, -0.052, -0.025, 0, edge);
    faceCylinder("telephone_rotary_wheel", 0.174, 0.008, -0.056, -0.025, 0, black);
    faceRing("telephone_wheel_edge", 0.17, 0.003, -0.061, -0.025, 0, edge);
    faceCylinder("telephone_number_card_rim", 0.072, 0.007, -0.064, -0.025, 0, edge);
    faceCylinder(
      "telephone_number_card",
      0.064,
      0.003,
      -0.069,
      -0.025,
      0,
      c.mat("telephone_card", "#c6b58c", 0.94),
    );

    // Cutouts read as deep black wells below raised, worn brass lips.
    for (let k = 0; k < 10; k++) {
      const angle = ((-55 + k * 28) * Math.PI) / 180;
      const y = -0.025 + Math.sin(angle) * 0.065;
      const z = -Math.cos(angle) * 0.065;
      faceCylinder("telephone_finger_well", 0.023, 0.002, -0.061, y, z, dark);
      faceRing("telephone_finger_well_lip", 0.024, 0.002, -0.064, y, z, edge);
    }
    c.tube(
      this.root,
      "telephone_finger_stop",
      [
        [-0.048, -0.124, -0.049],
        [-0.078, -0.113, -0.049],
        [-0.078, -0.103, -0.038],
      ],
      0.004,
      edge,
    );

    const markings = c.mat("telephone_dial_print", "#ffffff", 0.92);
    const texture = c.painted("telephone_dial_print", (ctx) => {
      ctx.clearRect(0, 0, 512, 512);
      ctx.fillStyle = "#e1ce9e";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.font = "bold 31px Georgia, serif";
      for (let k = 0; k < 10; k++) {
        const angle = ((-55 + k * 28) * Math.PI) / 180;
        ctx.fillText(
          String((k + 1) % 10),
          256 + Math.cos(angle) * 206,
          256 - Math.sin(angle) * 206,
        );
      }
      ctx.fillStyle = "#352e23";
      ctx.font = "19px Georgia, serif";
      ctx.fillText("No. 17", 256, 256);
    });
    texture.hasAlpha = true;
    markings.albedoTexture = texture;
    markings.useAlphaFromAlbedoTexture = true;
    const print = CreatePlane("telephone_dial_numbers", { size: 0.23 }, scene);
    c.finish(print, this.root, [-0.073, -0.025, 0], markings);
    print.rotation.y = Math.PI / 2;

    for (const z of [-0.108, 0.108]) {
      c.tube(
        this.root,
        "telephone_cradle_hook",
        [
          [0.008, 0.122, z],
          [-0.075, 0.122, z],
          [-0.088, 0.145, z],
        ],
        0.007,
        brass,
      );
      c.cylinder(this.root, "telephone_switch_plunger", 0.009, 0.025, [-0.055, 0.137, z], edge);
    }
    this.receiver = c.root("arrival_receiver", [-0.103, 0.16, 0], this.root);
    c.tube(
      this.receiver,
      "telephone_receiver_handle",
      [
        [0, 0, -0.131],
        [-0.018, 0.023, -0.08],
        [-0.025, 0.03, 0],
        [-0.018, 0.023, 0.08],
        [0, 0, 0.131],
      ],
      0.022,
      black,
    );
    for (const z of [-0.14, 0.14]) {
      c.sphere(this.receiver, "telephone_receiver_bell", [0.081, 0.071, 0.085], [0, 0, z], black);
      faceCylinder("telephone_receiver_cap", 0.076, 0.012, -0.035, 0, z, black, this.receiver);
      faceRing("telephone_receiver_cap_seam", 0.073, 0.002, -0.041, 0, z, brass, this.receiver);
      faceCylinder("telephone_receiver_grille", 0.052, 0.002, -0.043, 0, z, dark, this.receiver);
      for (let k = 0; k < 7; k++) {
        const angle = (k * Math.PI) / 3;
        faceCylinder(
          "telephone_receiver_perforation",
          0.004,
          0.001,
          -0.045,
          k === 6 ? 0 : Math.sin(angle) * 0.016,
          z + (k === 6 ? 0 : Math.cos(angle) * 0.016),
          brass,
          this.receiver,
        );
      }
    }
    faceCylinder("telephone_cord_grommet", 0.023, 0.016, -0.005, -0.149, 0.092, black);
    const path: [number, number, number][] = [];
    for (let i = 0; i <= 96; i++) {
      const t = i / 96;
      // One cloth-covered U-shaped lead, with a shallow helical braid along its length.
      const braid = Math.sin(Math.PI * t) * 0.0015;
      path.push([
        -0.103 + 0.098 * t + Math.cos(t * Math.PI * 72) * braid,
        0.16 - 0.31 * t - Math.sin(Math.PI * t) * 0.3,
        0.17 - 0.078 * t + Math.sin(t * Math.PI * 72) * braid,
      ]);
    }
    c.tube(this.root, "arrival_phone_cord", path, 0.004, cord);
    c.tube(
      this.root,
      "telephone_line_wire",
      [
        [0.15, -0.22, -0.08],
        [0.188, -0.26, -0.08],
        [0.188, -1.2, -0.08],
      ],
      0.0025,
      cord,
    );
  }

  private housing(
    c: RelicCraft,
    parent: TransformNode,
    name: string,
    x: number,
    depth: number,
    height: number,
    width: number,
    radius: number,
    material: PBRMaterial,
  ): void {
    const positions: number[] = [],
      indices: number[] = [];
    const rings = [
      [x - depth / 2, 0.006],
      [x - depth / 2 + 0.009, 0],
      [x + depth / 2 - 0.009, 0],
      [x + depth / 2, 0.006],
    ];
    const outline: [number, number][] = [];
    for (let corner = 0; corner < 4; corner++) {
      const angle = (corner * Math.PI) / 2;
      for (let k = 0; k <= 6; k++) {
        const a = angle + (k * Math.PI) / 12;
        outline.push([
          (height / 2 - radius) * (corner < 2 ? 1 : -1) + Math.sin(a) * radius,
          (width / 2 - radius) * (corner === 0 || corner === 3 ? 1 : -1) + Math.cos(a) * radius,
        ]);
      }
    }
    for (const [at, inset] of rings)
      for (const [y, z] of outline)
        positions.push(at, y - Math.sign(y) * inset, z - Math.sign(z) * inset);
    const n = outline.length;
    for (let r = 0; r < rings.length - 1; r++)
      for (let i = 0; i < n; i++) {
        const a = r * n + i,
          b = r * n + ((i + 1) % n);
        indices.push(a, b + n, b, a, a + n, b + n);
      }
    positions.push(rings[0][0], 0, 0, rings.at(-1)![0], 0, 0);
    for (let i = 0; i < n; i++) {
      indices.push(n * 4, i, (i + 1) % n);
      indices.push(n * 4 + 1, n * 3 + ((i + 1) % n), n * 3 + i);
    }
    const normals: number[] = [];
    VertexData.ComputeNormals(positions, indices, normals);
    const data = new VertexData();
    data.positions = positions;
    data.indices = indices;
    data.normals = normals;
    data.uvs = positions.flatMap((_, i) =>
      i % 3 === 0 ? [positions[i + 2] / width + 0.5, positions[i + 1] / height + 0.5] : [],
    );
    const mesh = new Mesh(name, c.scene);
    data.applyToMesh(mesh);
    c.finish(mesh, parent, [0, 0, 0], material);
  }
}
