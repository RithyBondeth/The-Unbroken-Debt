import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import { Texture } from "@babylonjs/core/Materials/Textures/texture";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { VertexData } from "@babylonjs/core/Meshes/mesh.vertexData";
import { CreateCylinder } from "@babylonjs/core/Meshes/Builders/cylinderBuilder";
import { CreateTube } from "@babylonjs/core/Meshes/Builders/tubeBuilder";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import type { Scene } from "@babylonjs/core/scene";
import { leafProfile } from "./leafCurve";
import { BOOK, paperHeight, roundedOutline } from "./bookGeometry";
import { bookMaterials } from "./bookMaterials";
import { SECTIONS } from "./sketchbookContent";

const { width: W, height: H, block: BLOCK, pageY: PAGE_Y } = BOOK;
const LEAF_SEGMENTS = 28;
const PAGE_ROWS = 8;
export type PageSlot = "left" | "right" | "leafFront" | "leafBack";

/** A sewn A5 sketchbook: rounded leather, layered paper, a recessed gutter and flexible leaves. */
export class BookModel {
  readonly root: TransformNode;
  readonly textures: Record<PageSlot, DynamicTexture>;
  readonly meshes: Mesh[] = [];
  private readonly leftHinge: TransformNode;
  private readonly leafFront: Mesh;
  private readonly leafBack: Mesh;
  private readonly paperMaterials: PBRMaterial[] = [];
  private readonly positions = new Float32Array((LEAF_SEGMENTS + 1) * (PAGE_ROWS + 1) * 3);
  private readonly normals = new Float32Array(this.positions.length);

  constructor(scene: Scene, textureWidth: number, textureHeight: number) {
    this.root = new TransformNode("sketchbook", scene);
    this.leftHinge = new TransformNode("sketchbook_hinge", scene);
    this.leftHinge.parent = this.root;
    const make = (slot: PageSlot) => {
      const texture = new DynamicTexture(
        `sketchbook_${slot}`,
        { width: textureWidth, height: textureHeight },
        scene,
        true,
        Texture.TRILINEAR_SAMPLINGMODE,
      );
      texture.anisotropicFilteringLevel = 8;
      texture.wrapU = texture.wrapV = Texture.CLAMP_ADDRESSMODE;
      return texture;
    };
    this.textures = {
      left: make("left"),
      right: make("right"),
      leafFront: make("leafFront"),
      leafBack: make("leafBack"),
    };
    const { leather, edges, linen, ribbon } = bookMaterials(scene);
    for (const side of [-1, 1] as const) {
      const parent = side < 0 ? this.leftHinge : this.root;
      this.slab(
        `cover_${side}`,
        W + 0.008,
        H + 0.01,
        0.003,
        (side * W) / 2,
        -BLOCK - 0.002,
        0.007,
        leather,
        parent,
      );
      this.slab(
        `paper_block_${side}`,
        W - 0.001,
        H - 0.001,
        BLOCK,
        (side * W) / 2,
        -BLOCK / 2,
        0.004,
        edges,
        parent,
        true,
      );
      this.page(side, parent);
    }
    const spine = CreateCylinder(
      "sketchbook_rounded_spine",
      { height: H + 0.007, diameter: 0.014, tessellation: 24 },
      scene,
    );
    spine.rotation.x = Math.PI / 2;
    spine.position.y = -BLOCK - 0.001;
    spine.material = leather;
    spine.parent = this.root;
    this.add(spine);
    // The cloth joint remains visible at the foot and head of the sewn book.
    for (const z of [-H / 2 + 0.001, H / 2 - 0.001]) {
      const binding = CreateTube(
        "sketchbook_headband",
        {
          path: [
            new Vector3(-0.008, -0.001, z),
            new Vector3(0, -0.003, z),
            new Vector3(0.008, -0.001, z),
          ],
          radius: 0.0011,
          tessellation: 8,
        },
        scene,
      );
      binding.parent = this.root;
      binding.material = linen;
      this.add(binding);
    }
    // A fabric bookmark drapes from the gutter, with a slightly curled tip.
    const bookmark = new Mesh("sketchbook_bookmark", scene);
    const ribbonData = new VertexData();
    ribbonData.positions = [
      -0.002,
      PAGE_Y + 0.0002,
      -0.045,
      0.003,
      PAGE_Y + 0.0002,
      -0.045,
      -0.002,
      PAGE_Y,
      -H / 2,
      0.003,
      PAGE_Y,
      -H / 2,
      -0.005,
      -0.011,
      -H / 2 - 0.031,
      0.001,
      -0.01,
      -H / 2 - 0.031,
    ];
    ribbonData.indices = [0, 2, 1, 1, 2, 3, 2, 4, 3, 3, 4, 5];
    ribbonData.normals = [];
    VertexData.ComputeNormals(ribbonData.positions, ribbonData.indices, ribbonData.normals);
    ribbonData.applyToMesh(bookmark);
    bookmark.parent = this.root;
    bookmark.material = ribbon;
    ribbon.backFaceCulling = false;
    this.add(bookmark);
    // Fabric index tabs project past the paper instead of looking like buttons printed on it.
    for (const [i, section] of SECTIONS.entries()) {
      const label = new DynamicTexture(
        `T_book_tab_${section.id}`,
        { width: 192, height: 96 },
        scene,
        true,
      );
      const ctx = label.getContext();
      ctx.fillStyle = ["#ac9973", "#b8a17a", "#9b9275", "#a09172", "#ae9570"][i];
      ctx.fillRect(0, 0, 192, 96);
      ctx.fillStyle = "#362b20";
      ctx.font = '32px "Patrick Hand"';
      ctx.fillText(`${i + 1} ${section.label}`, 14, 61);
      label.update();
      const cloth = new PBRMaterial(`M_book_tab_${section.id}`, scene);
      cloth.albedoTexture = label;
      cloth.roughness = 1;
      cloth.metallic = 0;
      cloth.maxSimultaneousLights = 4;
      this.slab(
        `tab_${section.id}`,
        0.027,
        0.022,
        0.0007,
        W + 0.008,
        -0.003,
        0.0025,
        cloth,
        this.root,
      );
      const tab = this.meshes.at(-1) as Mesh;
      tab.position.z = H / 2 - 0.024 - i * 0.035;
    }
    this.leafFront = this.leafMesh(scene, "leaf_front", this.textures.leafFront, false);
    this.leafBack = this.leafMesh(scene, "leaf_back", this.textures.leafBack, true);
    this.setFlip(null);
  }

  setOpen(amount: number): void {
    const a = Math.min(1, Math.max(0, amount));
    this.leftHinge.rotation.z = -Math.PI * (1 - a * a * (3 - 2 * a));
  }

  setFlip(t: number | null): void {
    this.leafFront.setEnabled(t !== null);
    this.leafBack.setEnabled(t !== null);
    if (t === null) return;
    const profile = leafProfile(t, W, LEAF_SEGMENTS);
    const motion = Math.sin(t * Math.PI);
    profile.forEach(([x, y], i) => {
      const u = i / LEAF_SEGMENTS;
      for (let row = 0; row <= PAGE_ROWS; row++) {
        const v = row / PAGE_ROWS;
        const z = (v - 0.5) * H;
        const offset = (i * (PAGE_ROWS + 1) + row) * 3;
        this.positions[offset] = x;
        this.positions[offset + 1] =
          y +
          paperHeight(Math.abs(x), z) * (1 - motion) +
          0.00025 +
          0.003 * motion * u * u * (v - 0.5);
        this.positions[offset + 2] = z;
      }
    });
    for (const mesh of [this.leafFront, this.leafBack]) {
      mesh.updateVerticesData("position", this.positions);
      VertexData.ComputeNormals(this.positions, mesh.getIndices() ?? [], this.normals);
      mesh.updateVerticesData("normal", this.normals);
    }
  }

  setPaperGlow(amount: number): void {
    for (const m of this.paperMaterials) m.emissiveColor.set(amount, amount * 0.95, amount * 0.85);
  }

  rightPageEdge(): [Vector3, Vector3] {
    const world = this.root.getWorldMatrix();
    return [
      Vector3.TransformCoordinates(new Vector3(0, PAGE_Y, -H / 2), world),
      Vector3.TransformCoordinates(new Vector3(0, PAGE_Y, H / 2), world),
    ];
  }

  setRenderingGroup(group: number): void {
    for (const mesh of this.meshes) mesh.renderingGroupId = group;
  }

  /** Bevelled rounded cover, or a page block whose top follows the arched paper. */
  private slab(
    name: string,
    width: number,
    depth: number,
    height: number,
    cx: number,
    cy: number,
    radius: number,
    material: PBRMaterial,
    parent: TransformNode,
    paper = false,
  ): void {
    const outline = roundedOutline(width, depth, radius);
    const positions: number[] = [],
      uvs: number[] = [],
      indices: number[] = [];
    const bevel = Math.min(height * 0.25, 0.0007);
    const rings = [
      [0.0006, -height / 2],
      [0, -height / 2 + bevel],
      [0, height / 2 - bevel],
      [0.0006, height / 2],
    ];
    for (const [inset, y] of rings)
      for (const [x, z] of outline) {
        const px = x * (1 - inset / (width / 2)) + cx;
        const pz = z * (1 - inset / (depth / 2));
        const py = cy + y + (paper ? paperHeight(Math.abs(px), pz) - PAGE_Y : 0);
        positions.push(px, py, pz);
        uvs.push(x / width + 0.5, paper ? y / height + 0.5 : z / depth + 0.5);
      }
    const n = outline.length;
    for (let ring = 0; ring < 3; ring++)
      for (let k = 0; k < n; k++) {
        const a = ring * n + k,
          b = ring * n + ((k + 1) % n);
        indices.push(a, b, a + n, b, b + n, a + n);
      }
    for (let k = 1; k < n - 1; k++) {
      indices.push(0, k + 1, k);
      indices.push(3 * n, 3 * n + k, 3 * n + k + 1);
    }
    const mesh = this.mesh(`sketchbook_${name}`, positions, indices, uvs);
    mesh.material = material;
    mesh.parent = parent;
  }

  private page(side: -1 | 1, parent: TransformNode): void {
    const positions: number[] = [],
      indices: number[] = [],
      uvs: number[] = [];
    const columns = 24,
      rows = 12;
    for (let i = 0; i <= columns; i++)
      for (let row = 0; row <= rows; row++) {
        const u = i / columns,
          v = row / rows,
          z = (v - 0.5) * H;
        const x = side < 0 ? -W + u * W : u * W;
        positions.push(x, paperHeight(Math.abs(x), z), z);
        uvs.push(u, v);
        if (i < columns && row < rows) {
          const a = i * (rows + 1) + row,
            b = a + rows + 1;
          indices.push(a, b, a + 1, a + 1, b, b + 1);
        }
      }
    const mesh = this.mesh(`sketchbook_page_${side}`, positions, indices, uvs);
    mesh.material = this.paperMaterial(
      side < 0 ? "left" : "right",
      this.textures[side < 0 ? "left" : "right"],
    );
    mesh.parent = parent;
  }

  private paperMaterial(name: string, texture: DynamicTexture): PBRMaterial {
    const material = new PBRMaterial(`M_sketchbook_${name}`, this.root.getScene());
    material.albedoTexture = material.emissiveTexture = texture;
    material.emissiveColor = Color3.Black();
    material.roughness = 0.97;
    material.metallic = 0;
    material.maxSimultaneousLights = 4;
    this.paperMaterials.push(material);
    return material;
  }

  private leafMesh(scene: Scene, name: string, texture: DynamicTexture, back: boolean): Mesh {
    const uvs: number[] = [],
      indices: number[] = [];
    for (let i = 0; i <= LEAF_SEGMENTS; i++)
      for (let row = 0; row <= PAGE_ROWS; row++) {
        const u = i / LEAF_SEGMENTS,
          v = row / PAGE_ROWS;
        uvs.push(back ? 1 - u : u, v);
        if (i < LEAF_SEGMENTS && row < PAGE_ROWS) {
          const a = i * (PAGE_ROWS + 1) + row,
            b = a + PAGE_ROWS + 1;
          if (back) indices.push(a, a + 1, b, a + 1, b + 1, b);
          else indices.push(a, b, a + 1, a + 1, b, b + 1);
        }
      }
    const mesh = new Mesh(`sketchbook_${name}`, scene);
    const data = new VertexData();
    data.positions = this.positions;
    data.indices = indices;
    data.uvs = uvs;
    data.normals = new Float32Array(this.positions.length);
    data.applyToMesh(mesh, true);
    mesh.parent = this.root;
    mesh.material = this.paperMaterial(name, texture);
    this.add(mesh);
    return mesh;
  }

  private mesh(name: string, positions: number[], indices: number[], uvs: number[]): Mesh {
    const mesh = new Mesh(name, this.root.getScene());
    const data = new VertexData();
    data.positions = positions;
    data.indices = indices;
    data.uvs = uvs;
    data.normals = [];
    VertexData.ComputeNormals(positions, indices, data.normals);
    data.applyToMesh(mesh);
    this.add(mesh);
    return mesh;
  }

  private add(mesh: Mesh): void {
    mesh.isPickable = false;
    mesh.receiveShadows = false;
    this.meshes.push(mesh);
  }
}
