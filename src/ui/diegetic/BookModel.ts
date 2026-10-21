import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import { Texture } from "@babylonjs/core/Materials/Textures/texture";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { VertexData } from "@babylonjs/core/Meshes/mesh.vertexData";
import { CreateBox } from "@babylonjs/core/Meshes/Builders/boxBuilder";
import { CreateGround } from "@babylonjs/core/Meshes/Builders/groundBuilder";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import type { Scene } from "@babylonjs/core/scene";
import { leafProfile } from "./leafCurve";

/** Page size in metres (A5 portrait) and the stack heights either side of the spine. */
const W = 0.148;
const H = 0.21;
const BLOCK = 0.006;
const PAGE_Y = 0.0004;
const COVER_Y = -(BLOCK + 0.0015);
const LEAF_SEGMENTS = 28;

export type PageSlot = "left" | "right" | "leafFront" | "leafBack";

/**
 * Sora's sketchbook as a 3D object: leather covers, two page blocks, a page
 * on each side and a leaf that curls over when a page is turned. Pages are
 * dynamic textures painted by `PagePainter`. Local axes: x across the book
 * (spine at 0, right-hand page at +x), y up off the paper, z up the page.
 */
export class BookModel {
  readonly root: TransformNode;
  readonly textures: Record<PageSlot, DynamicTexture>;
  readonly meshes: Mesh[] = [];
  private readonly leftHinge: TransformNode;
  private readonly leafFront: Mesh;
  private readonly leafBack: Mesh;
  private readonly paperMaterials: PBRMaterial[] = [];
  private readonly positions: Float32Array;

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
      // Pages are read at an angle: keep text sharp along the slope.
      texture.anisotropicFilteringLevel = 8;
      texture.wrapU = Texture.CLAMP_ADDRESSMODE;
      texture.wrapV = Texture.CLAMP_ADDRESSMODE;
      return texture;
    };
    this.textures = {
      left: make("left"),
      right: make("right"),
      leafFront: make("leafFront"),
      leafBack: make("leafBack"),
    };

    const leather = new PBRMaterial("M_sketchbook_leather", scene);
    leather.albedoColor = new Color3(0.13, 0.07, 0.04);
    leather.roughness = 0.7;
    leather.metallic = 0;
    const edges = new PBRMaterial("M_sketchbook_edges", scene);
    edges.albedoColor = new Color3(0.78, 0.71, 0.58);
    edges.roughness = 0.95;
    edges.metallic = 0;

    // Right-hand side: back cover, page block, page.
    this.box("cover_back", W + 0.006, 0.003, H + 0.008, W / 2, COVER_Y, this.root, leather);
    this.box("block_right", W, BLOCK, H, W / 2, -BLOCK / 2, this.root, edges);
    this.page("page_right", "right", W / 2, this.root);
    // Left-hand side hangs on the hinge, so the book opens by turning it.
    this.box("cover_front", W + 0.006, 0.003, H + 0.008, -W / 2, COVER_Y, this.leftHinge, leather);
    this.box("block_left", W, BLOCK, H, -W / 2, -BLOCK / 2, this.leftHinge, edges);
    this.page("page_left", "left", -W / 2, this.leftHinge);

    // The turning leaf: two meshes back to back, sharing one curled shape.
    const count = (LEAF_SEGMENTS + 1) * 2;
    this.positions = new Float32Array(count * 3);
    this.leafFront = this.leafMesh(scene, "leaf_front", this.textures.leafFront, false);
    this.leafBack = this.leafMesh(scene, "leaf_back", this.textures.leafBack, true);
    this.setFlip(null);
  }

  /** 0 = closed (left half folded over), 1 = open flat. */
  setOpen(amount: number): void {
    const a = Math.min(1, Math.max(0, amount));
    const eased = a * a * (3 - 2 * a);
    this.leftHinge.rotation.z = -Math.PI * (1 - eased);
  }

  /**
   * Shows the leaf mid-turn: `t` 0–1 from right to left (turning forward).
   * Turning back runs the same shape from 1 to 0. `null` hides the leaf.
   */
  setFlip(t: number | null): void {
    const visible = t !== null;
    this.leafFront.setEnabled(visible);
    this.leafBack.setEnabled(visible);
    if (t === null) return;
    const profile = leafProfile(t, W, LEAF_SEGMENTS);
    const lift = 0.0009;
    profile.forEach(([x, y], i) => {
      for (let row = 0; row < 2; row++) {
        const v = (i * 2 + row) * 3;
        this.positions[v] = x;
        this.positions[v + 1] = y + lift;
        this.positions[v + 2] = row === 0 ? -H / 2 : H / 2;
      }
    });
    for (const mesh of [this.leafFront, this.leafBack]) {
      mesh.updateVerticesData("position", this.positions);
      const normals = new Float32Array(this.positions.length);
      VertexData.ComputeNormals(this.positions, mesh.getIndices() ?? [], normals);
      mesh.updateVerticesData("normal", normals);
    }
  }

  /** A faint glow from the paper itself, so ink stays legible when the lamp is low. */
  setPaperGlow(amount: number): void {
    for (const m of this.paperMaterials)
      m.emissiveColor = new Color3(amount, amount * 0.95, amount * 0.85);
  }

  /** Corners of the right-hand page (bottom and top of its spine edge), in world space. */
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

  private box(
    name: string,
    w: number,
    h: number,
    d: number,
    x: number,
    y: number,
    parent: TransformNode,
    material: PBRMaterial,
  ): void {
    const mesh = CreateBox(
      `sketchbook_${name}`,
      { width: w, height: h, depth: d },
      this.root.getScene(),
    );
    mesh.position.set(x, y, 0);
    mesh.parent = parent;
    mesh.material = material;
    this.add(mesh);
  }

  private page(name: string, slot: PageSlot, x: number, parent: TransformNode): void {
    const scene = this.root.getScene();
    const mesh = CreateGround(`sketchbook_${name}`, { width: W, height: H }, scene);
    mesh.position.set(x, PAGE_Y, 0);
    mesh.parent = parent;
    mesh.material = this.paperMaterial(name, this.textures[slot]);
    this.add(mesh);
  }

  private paperMaterial(name: string, texture: DynamicTexture): PBRMaterial {
    const material = new PBRMaterial(`M_sketchbook_${name}`, this.root.getScene());
    material.albedoTexture = texture;
    material.emissiveTexture = texture;
    material.emissiveColor = Color3.Black();
    material.roughness = 0.88;
    material.metallic = 0;
    this.paperMaterials.push(material);
    return material;
  }

  private leafMesh(scene: Scene, name: string, texture: DynamicTexture, back: boolean): Mesh {
    const mesh = new Mesh(`sketchbook_${name}`, scene);
    const uvs: number[] = [];
    const indices: number[] = [];
    for (let i = 0; i <= LEAF_SEGMENTS; i++) {
      const u = i / LEAF_SEGMENTS;
      // Front: the right-hand page (spine at u = 0). Back: the next left-hand page (spine at u = 1).
      const pu = back ? 1 - u : u;
      uvs.push(pu, 0, pu, 1);
      if (i < LEAF_SEGMENTS) {
        const a = i * 2;
        // Front faces up off the right-hand page; the back faces the other way.
        if (back) indices.push(a, a + 1, a + 2, a + 1, a + 3, a + 2);
        else indices.push(a, a + 2, a + 1, a + 1, a + 2, a + 3);
      }
    }
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

  private add(mesh: Mesh): void {
    mesh.isPickable = false;
    mesh.receiveShadows = false;
    this.meshes.push(mesh);
  }
}
