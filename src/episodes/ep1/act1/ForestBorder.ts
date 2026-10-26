import type { AssetContainer } from "@babylonjs/core/assetContainer";
import type { Material } from "@babylonjs/core/Materials/material";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import { Texture } from "@babylonjs/core/Materials/Textures/texture";
import { Matrix, Quaternion, Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { VertexData } from "@babylonjs/core/Meshes/mesh.vertexData";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { CreateTube } from "@babylonjs/core/Meshes/Builders/tubeBuilder";
import type { Node } from "@babylonjs/core/node";
import { PhysicsBody } from "@babylonjs/core/Physics/v2/physicsBody";
import { PhysicsMotionType } from "@babylonjs/core/Physics/v2/IPhysicsEnginePlugin";
import { PhysicsShapeBox, PhysicsShapeContainer } from "@babylonjs/core/Physics/v2/physicsShape";
import type { Scene } from "@babylonjs/core/scene";
import { seededRandom } from "../../../audio/synth";
import type { QualityPreset } from "../../../render/QualityPresets";
import {
  GROUND_TILE,
  PLAY,
  ROAD_Z,
  TERRAIN,
  borderHeight,
  inBelt,
  inBund,
  layoutBorder,
  onOuterRoad,
  openGround,
  outside,
  type Card,
  type Layer,
  type Plant,
  type Species,
} from "../data/forestBorder";
import { CARD_COLUMNS, CARD_ROWS, paintForestCards } from "./forestCards";

/** One material's geometry from a village plant, its foot at the origin. */
interface Part {
  material: Material;
  positions: Float32Array;
  normals: Float32Array;
  uvs: Float32Array | null;
  indices: Uint32Array;
  receiveShadows: boolean;
}

interface Template {
  name: string;
  parts: Part[];
  /** Local bounds: x/z extents and top, for logs and colliders. */
  size: Vector3;
}

/**
 * Village nodes copied as templates before batching merges them. The broadleaf
 * trees are the forest's own authored trees; each placement gets its own turn
 * and size, so no copy reads as a repeat. Foot points come from their colliders.
 */
const TEMPLATES: Record<Species, string[][]> = {
  broadleaf: [["tree_0"], ["tree_3"], ["tree_12"], ["tree_301"], ["tree_305"], ["tree_311"]],
  young: [["tree_10"], ["tree_11"], ["tree_317"]],
  sugarPalm: [["palm_0"], ["palm_3"], ["palm_6"]],
  coconut: [["coco_0"], ["coco_3"]],
  bamboo: [["bamboo_0"], ["bamboo_3"], ["bamboo_7"]],
  banana: [["banana_1"], ["banana_5"], ["banana_13"]],
  dead: [["dead_3"], ["dead_6"]],
  pachira: ["a", "c", "d"].map((v) => [
    `pachira_aquatica_01_bark_${v}.001`,
    `pachira_aquatica_01_leaves_${v}.001`,
  ]),
  shrub: [
    ["shrub_02_a.001"],
    ["shrub_02_c.001"],
    ["shrub_03_a.001"],
    ["shrub_03_c.001"],
    ["shrub_03_d.001"],
  ],
  fern: [["fern_02_a.001"], ["fern_02_b.001"], ["fern_02_c.001"], ["fern_02_d.001"]],
};
const LOG = ["dead_tree_trunk.001"];
const POLE = ["telegraph_2"];

/** Trunk half-widths for colliders near where Sora walks (× the plant's scale, palms aside). */
const TRUNK: Partial<Record<Species, number>> = {
  broadleaf: 0.4,
  young: 0.4,
  sugarPalm: 0.22,
  coconut: 0.18,
  bamboo: 0.65,
  dead: 0.22,
  pachira: 0.1,
};

/** Cell sizes (m) and distances past which a layer is not drawn. */
const CELLS: Record<Layer, { group: string; size: number; lod: number | null }> = {
  canopy: { group: "canopy", size: 48, lod: null },
  mid: { group: "under", size: 32, lod: 42 },
  under: { group: "under", size: 32, lod: 42 },
};

interface Bucket {
  name: string;
  material: Material;
  receiveShadows: boolean;
  lod: number | null;
  hasUv: boolean;
  items: { part: Part; m: Float32Array; r: Float32Array }[];
  verts: number;
  indices: number;
}

interface Box {
  minX: number;
  maxX: number;
  minZ: number;
  maxZ: number;
}

/**
 * The forest round the village and the end of Sora's walk (data/forestBorder):
 * ground and road carried on past the authored terrain, the walls' thicket and
 * outer forest modelled from the village's own plants, painted far trees to
 * the storm sky, the compound's belt filled out with a layered understory and
 * puddles, and the walls themselves. Geometry is merged per material in cells,
 * as the area's own plants are, so the forest costs few draw calls and culls.
 */
export class ForestBorder {
  readonly meshes: Mesh[] = [];
  private readonly templates = new Map<Species, Template[]>();
  private log: Template | null = null;
  private pole: Template | null = null;
  private readonly obstacles: Box[] = [];
  private readonly wireEnds: { x: number; ends: Vector3[] }[] = [];
  private heights: Float32Array | null = null;
  private materials = new Map<string, Material>();
  private groundShadows = true;
  private body: PhysicsBody | null = null;
  private anchor: TransformNode | null = null;
  private atlas: DynamicTexture | null = null;
  private cardMaterial: PBRMaterial | null = null;
  readonly stats = { plants: 0, cards: 0, triangles: 0, colliders: 0, meshes: 0 };

  constructor(
    private readonly scene: Scene,
    private readonly preset: QualityPreset,
  ) {}

  /** Copies templates, ground heights and obstacles out of the area before it is batched. */
  capture(container: AssetContainer): void {
    const byName = new Map<string, Node>();
    for (const node of [...container.transformNodes, ...container.meshes])
      if (!byName.has(node.name)) byName.set(node.name, node);
    for (const material of container.materials) this.materials.set(material.name, material);

    for (const mesh of container.meshes) {
      if (!mesh.name.startsWith("col_") || mesh.name === "col_ground") continue;
      mesh.computeWorldMatrix(true);
      const box = mesh.getBoundingInfo().boundingBox;
      this.obstacles.push({
        minX: box.minimumWorld.x,
        maxX: box.maximumWorld.x,
        minZ: box.minimumWorld.z,
        maxZ: box.maximumWorld.z,
      });
    }
    this.sampleTerrain(container);

    for (const [species, lists] of Object.entries(TEMPLATES) as [Species, string[][]][]) {
      const found = lists
        .map((names) => this.template(byName, names))
        .filter((t): t is Template => t !== null);
      if (found.length === 0) console.warn(`[ForestBorder] no templates for ${species}`);
      this.templates.set(species, found);
    }
    this.log = this.template(byName, LOG);
    this.pole = this.template(byName, POLE);
    // Where the existing line's end poles hold their wires.
    for (const name of ["telegraph_0", "telegraph_3"]) {
      const node = byName.get(name);
      const glass = node && this.meshesOf(node).find((m) => m.material?.name.startsWith("M_glass"));
      if (glass) this.wireEnds.push({ x: glass.getBoundingInfo().boundingBox.centerWorld.x, ends: this.insulators(glass) });
    }
  }

  /** Builds everything; call once the area is loaded. */
  build(): void {
    const low = this.preset.name === "low";
    const options = {
      nearDepth: low ? 8 : this.preset.name === "medium" ? 14 : 16,
      farDepth: low ? 24 : 44,
      density: low ? 0.55 : this.preset.name === "medium" ? 0.85 : 1,
      clear: (x: number, z: number, r: number) => this.clear(x, z, r),
    };
    const layout = layoutBorder(options);
    this.buildGround(options.farDepth + 6);
    const buckets = new Map<string, Bucket>();
    const trunks: Box[] = [];
    for (const plant of layout.plants) this.place(plant, buckets, trunks);
    this.placeRoadblocks(buckets, trunks);
    this.placeTelegraph(buckets, options.farDepth);
    for (const bucket of buckets.values()) this.bake(bucket);
    this.buildCards(layout.cards);
    this.buildPuddles();
    this.buildColliders(trunks);
    this.stats.plants = layout.plants.length;
    this.stats.cards = layout.cards.length;
    this.stats.meshes = this.meshes.length;
    console.info(
      `[ForestBorder] ${this.stats.plants} plants, ${this.stats.cards} far trees, ` +
        `${(this.stats.triangles / 1e6).toFixed(2)} M triangles in ${this.stats.meshes} meshes, ` +
        `${this.stats.colliders} colliders`,
    );
  }

  /** Height of the ground (authored or extended) at a point. */
  groundAt(x: number, z: number): number {
    if (outside(TERRAIN, x, z) < 0 && !inBund(x, z)) return this.terrainAt(x, z);
    return borderHeight(x, z, (a, b) => this.terrainAt(a, b));
  }

  dispose(): void {
    for (const mesh of this.meshes) mesh.dispose();
    this.meshes.length = 0;
    this.body?.dispose();
    this.anchor?.dispose();
    this.atlas?.dispose();
    this.cardMaterial?.dispose();
  }

  // ------------------------------------------------------------- capture

  private meshesOf(node: Node): Mesh[] {
    const all = node instanceof Mesh ? [node] : [];
    for (const child of node.getChildMeshes(false)) if (child instanceof Mesh) all.push(child);
    return all.filter((m) => m.getTotalVertices() > 0 && m.material);
  }

  /** The authored terrain's 1 m height grid, read from its mesh. */
  private sampleTerrain(container: AssetContainer): void {
    const nx = TERRAIN.maxX - TERRAIN.minX + 1;
    const nz = TERRAIN.maxZ - TERRAIN.minZ + 1;
    const heights = new Float32Array(nx * nz).fill(Number.NaN);
    for (const mesh of container.meshes) {
      if (mesh.name !== "ground" && !mesh.name.startsWith("ground_primitive")) continue;
      if (mesh.material?.name === "M_wet_forest_floor") this.groundShadows = mesh.receiveShadows;
      const world = mesh.computeWorldMatrix(true);
      const positions = mesh.getVerticesData("position");
      if (!positions) continue;
      const p = new Vector3();
      for (let i = 0; i < positions.length; i += 3) {
        Vector3.TransformCoordinatesFromFloatsToRef(positions[i], positions[i + 1], positions[i + 2], world, p);
        const ix = Math.round(p.x - TERRAIN.minX);
        const iz = Math.round(p.z - TERRAIN.minZ);
        if (ix >= 0 && ix < nx && iz >= 0 && iz < nz) heights[ix + iz * nx] = p.y;
      }
    }
    let missing = 0;
    for (let i = 0; i < heights.length; i++)
      if (Number.isNaN(heights[i])) {
        heights[i] = 0;
        missing++;
      }
    if (missing) console.warn(`[ForestBorder] ${missing} terrain heights missing`);
    this.heights = heights;
  }

  terrainAt(x: number, z: number): number {
    const h = this.heights;
    if (!h) return 0;
    const nx = TERRAIN.maxX - TERRAIN.minX + 1;
    const fx = Math.max(0, Math.min(nx - 1.0001, x - TERRAIN.minX));
    const fz = Math.max(0, Math.min(TERRAIN.maxZ - TERRAIN.minZ - 0.0001, z - TERRAIN.minZ));
    const ix = Math.floor(fx),
      iz = Math.floor(fz);
    const tx = fx - ix,
      tz = fz - iz;
    const at = (i: number, j: number) => h[i + j * nx];
    return (
      (at(ix, iz) * (1 - tx) + at(ix + 1, iz) * tx) * (1 - tz) +
      (at(ix, iz + 1) * (1 - tx) + at(ix + 1, iz + 1) * tx) * tz
    );
  }

  private template(byName: Map<string, Node>, names: string[]): Template | null {
    const nodes = names.map((n) => byName.get(n));
    if (nodes.some((n) => !n)) return null;
    const meshes = nodes.flatMap((n) => this.meshesOf(n!));
    if (meshes.length === 0) return null;
    // The foot: the trunk's collider if it has one, else the base of its bounds.
    const min = new Vector3(Infinity, Infinity, Infinity);
    const max = new Vector3(-Infinity, -Infinity, -Infinity);
    for (const mesh of meshes) {
      mesh.computeWorldMatrix(true);
      const box = mesh.getBoundingInfo().boundingBox;
      min.minimizeInPlace(box.minimumWorld);
      max.maximizeInPlace(box.maximumWorld);
    }
    const collider = byName.get(`col_${names[0]}`);
    const foot = new Vector3((min.x + max.x) / 2, 0, (min.z + max.z) / 2);
    if (collider instanceof Mesh) {
      collider.computeWorldMatrix(true);
      const c = collider.getBoundingInfo().boundingBox.centerWorld;
      foot.set(c.x, 0, c.z);
    }
    const parts = meshes.map((mesh) => this.bakePart(mesh, foot));
    const size = new Vector3(max.x - min.x, max.y - foot.y, max.z - min.z);
    return { name: names[0], parts, size };
  }

  /** World-space copy of a mesh's geometry relative to `foot`, winding fixed for mirrored nodes. */
  private bakePart(mesh: Mesh, foot: Vector3): Part {
    const world = mesh.computeWorldMatrix(true);
    const normalMatrix = world.clone().invert().transpose();
    const positions = Float32Array.from(mesh.getVerticesData("position") ?? []);
    const normals = Float32Array.from(mesh.getVerticesData("normal") ?? new Float32Array(positions.length));
    const uv = mesh.getVerticesData("uv");
    const source = mesh.getIndices() ?? [];
    const indices = Uint32Array.from(source);
    const p = new Vector3();
    for (let i = 0; i < positions.length; i += 3) {
      Vector3.TransformCoordinatesFromFloatsToRef(positions[i], positions[i + 1], positions[i + 2], world, p);
      positions[i] = p.x - foot.x;
      positions[i + 1] = p.y - foot.y;
      positions[i + 2] = p.z - foot.z;
      Vector3.TransformNormalFromFloatsToRef(normals[i], normals[i + 1], normals[i + 2], normalMatrix, p);
      p.normalize();
      normals[i] = p.x;
      normals[i + 1] = p.y;
      normals[i + 2] = p.z;
    }
    if (world.determinant() < 0)
      for (let i = 0; i < indices.length; i += 3) {
        const t = indices[i + 1];
        indices[i + 1] = indices[i + 2];
        indices[i + 2] = t;
      }
    return {
      material: mesh.material!,
      positions,
      normals,
      uvs: uv ? Float32Array.from(uv) : null,
      indices,
      receiveShadows: mesh.receiveShadows,
    };
  }

  /** The two wire points of a crossarm: the ends of its insulators' long axis. */
  private insulators(glass: Mesh): Vector3[] {
    glass.computeWorldMatrix(true);
    const box = glass.getBoundingInfo().boundingBox;
    const c = box.centerWorld;
    const e = box.extendSizeWorld;
    const alongX = e.x > e.z;
    const reach = Math.max(e.x, e.z) - 0.04;
    return [-1, 1].map(
      (s) => new Vector3(c.x + (alongX ? s * reach : 0), box.maximumWorld.y - 0.02, c.z + (alongX ? 0 : s * reach)),
    );
  }

  // ------------------------------------------------------------- layout

  private clear(x: number, z: number, r: number): boolean {
    for (const o of this.obstacles)
      if (x > o.minX - r && x < o.maxX + r && z > o.minZ - r && z < o.maxZ + r) return false;
    return true;
  }

  private place(plant: Plant, buckets: Map<string, Bucket>, trunks: Box[]): void {
    const list = this.templates.get(plant.species);
    if (!list?.length) return;
    const template = list[Math.min(list.length - 1, Math.floor(plant.pick * list.length))];
    const y = this.groundAt(plant.x, plant.z) - 0.03;
    this.add(buckets, template, plant.layer, plant.x, y, plant.z, plant.yaw, plant.scale);
    const half = TRUNK[plant.species];
    if (half && plant.layer !== "under" && outside(PLAY, plant.x, plant.z) < 1.5) {
      const fixed = plant.species === "sugarPalm" || plant.species === "coconut" || plant.species === "dead";
      const w = half * (fixed ? 1 : plant.scale);
      trunks.push({ minX: plant.x - w, maxX: plant.x + w, minZ: plant.z - w, maxZ: plant.z + w });
    }
  }

  private add(
    buckets: Map<string, Bucket>,
    template: Template,
    layer: Layer,
    x: number,
    y: number,
    z: number,
    yaw: number,
    scale: number,
  ): void {
    const rotation = Matrix.RotationY(yaw);
    const matrix = Matrix.Scaling(scale, scale, scale)
      .multiply(rotation)
      .multiply(Matrix.Translation(x, y, z));
    const cell = CELLS[layer];
    const key = `${Math.floor(x / cell.size)},${Math.floor(z / cell.size)}`;
    for (const part of template.parts) {
      const id = `${cell.group}|${part.material.uniqueId}|${key}|${part.uvs ? 1 : 0}`;
      let bucket = buckets.get(id);
      if (!bucket) {
        bucket = {
          name: `forest_border_${cell.group}_${part.material.name}_${key}`,
          material: part.material,
          receiveShadows: part.receiveShadows,
          lod: cell.lod,
          hasUv: part.uvs !== null,
          items: [],
          verts: 0,
          indices: 0,
        };
        buckets.set(id, bucket);
      }
      bucket.items.push({ part, m: Float32Array.from(matrix.m), r: Float32Array.from(rotation.m) });
      bucket.verts += part.positions.length / 3;
      bucket.indices += part.indices.length;
    }
  }

  /**
   * The road at both ends of the walk is blocked by a tree the storm brought
   * down, in brush, so the road can run on into the fog behind it.
   */
  private placeRoadblocks(buckets: Map<string, Bucket>, trunks: Box[]): void {
    const log = this.log;
    if (!log) return;
    const alongX = log.size.x > log.size.z;
    const length = Math.max(log.size.x, log.size.z);
    const scale = Math.min(2.2, Math.max(1, 8 / length));
    const random = seededRandom(6242031);
    for (const side of [-1, 1]) {
      const x = side * (PLAY.maxX - 1.4);
      const yaw = (alongX ? Math.PI / 2 : 0) + (random() - 0.5) * 0.3;
      this.add(buckets, log, "canopy", x, this.groundAt(x, ROAD_Z) - 0.05, ROAD_Z, yaw, scale);
      const half = (length * scale) / 2;
      trunks.push({ minX: x - 0.7, maxX: x + 0.7, minZ: ROAD_Z - half, maxZ: ROAD_Z + half });
      // Its broken crown and the brush grown up round it.
      const brush: [Species, number, number, number][] = [
        ["broadleaf", 2.6, 4.2, 0.55],
        ["shrub", 1.2, 1.6, 1.5],
        ["shrub", 2, -1.8, 1.8],
        ["fern", 0.6, -0.4, 1.3],
        ["shrub", 3.2, 0.8, 1.6],
        ["bamboo", 3.6, -3.8, 0.9],
      ];
      for (const [species, dx, dz, s] of brush) {
        const list = this.templates.get(species);
        if (!list?.length) continue;
        const bx = x + side * dx,
          bz = ROAD_Z + dz;
        this.add(buckets, list[Math.floor(random() * list.length)], species === "broadleaf" || species === "bamboo" ? "canopy" : "under", bx, this.groundAt(bx, bz) - 0.03, bz, random() * Math.PI * 2, s);
      }
    }
  }

  /** The telegraph line runs on along the road, as far as can be seen. */
  private placeTelegraph(buckets: Map<string, Bucket>, depth: number): void {
    const pole = this.pole;
    if (!pole) return;
    const glass = pole.parts.find((p) => p.material.name.startsWith("M_glass"));
    const reach = (() => {
      if (!glass) return null;
      let minX = Infinity, maxX = -Infinity, minZ = Infinity, maxZ = -Infinity, top = -Infinity;
      for (let i = 0; i < glass.positions.length; i += 3) {
        minX = Math.min(minX, glass.positions[i]);
        maxX = Math.max(maxX, glass.positions[i]);
        top = Math.max(top, glass.positions[i + 1]);
        minZ = Math.min(minZ, glass.positions[i + 2]);
        maxZ = Math.max(maxZ, glass.positions[i + 2]);
      }
      const alongX = maxX - minX > maxZ - minZ;
      const r = Math.max(maxX - minX, maxZ - minZ) / 2 - 0.04;
      const c = new Vector3((minX + maxX) / 2, top - 0.02, (minZ + maxZ) / 2);
      return [-1, 1].map((s) => c.add(new Vector3(alongX ? s * r : 0, 0, alongX ? 0 : s * r)));
    })();
    const wires: Vector3[][] = [];
    for (const start of this.wireEnds) {
      const dir = Math.sign(start.x);
      let previous = start.ends;
      for (let x = start.x + dir * 22; Math.abs(x) < TERRAIN.maxX + depth; x += dir * 22) {
        const z = 61;
        const y = this.groundAt(x, z) - 0.05;
        this.add(buckets, pole, "canopy", x, y, z, 0, 1);
        if (!reach) continue;
        const ends = reach.map((p) => p.add(new Vector3(x, y, z)));
        for (let k = 0; k < 2; k++) wires.push(this.sag(previous[k], ends[k]));
        previous = ends;
      }
    }
    const iron = this.materials.get("M_iron");
    if (!wires.length || !iron) return;
    const tubes = wires.map((path, i) =>
      CreateTube(`forest_border_wire_${i}`, { path, radius: 0.007, tessellation: 4 }, this.scene),
    );
    const merged = Mesh.MergeMeshes(tubes, true, true);
    if (!merged) return;
    merged.name = "forest_border_wires";
    merged.material = iron;
    merged.isPickable = false;
    merged.freezeWorldMatrix();
    this.stats.triangles += merged.getTotalIndices() / 3;
    this.meshes.push(merged);
  }

  private sag(a: Vector3, b: Vector3): Vector3[] {
    const points: Vector3[] = [];
    for (let i = 0; i <= 12; i++) {
      const t = i / 12;
      points.push(Vector3.Lerp(a, b, t).addInPlaceFromFloats(0, -4 * 0.45 * t * (1 - t), 0));
    }
    return points;
  }

  // ------------------------------------------------------------- geometry

  private bake(bucket: Bucket): void {
    const positions = new Float32Array(bucket.verts * 3);
    const normals = new Float32Array(bucket.verts * 3);
    const uvs = bucket.hasUv ? new Float32Array(bucket.verts * 2) : null;
    const indices = new Uint32Array(bucket.indices);
    let vo = 0,
      io = 0;
    for (const { part, m, r } of bucket.items) {
      const p = part.positions,
        n = part.normals;
      const count = p.length / 3;
      for (let i = 0; i < count; i++) {
        const x = p[i * 3],
          y = p[i * 3 + 1],
          z = p[i * 3 + 2];
        const o = (vo + i) * 3;
        positions[o] = x * m[0] + y * m[4] + z * m[8] + m[12];
        positions[o + 1] = x * m[1] + y * m[5] + z * m[9] + m[13];
        positions[o + 2] = x * m[2] + y * m[6] + z * m[10] + m[14];
        const nx = n[i * 3],
          ny = n[i * 3 + 1],
          nz = n[i * 3 + 2];
        normals[o] = nx * r[0] + ny * r[4] + nz * r[8];
        normals[o + 1] = nx * r[1] + ny * r[5] + nz * r[9];
        normals[o + 2] = nx * r[2] + ny * r[6] + nz * r[10];
      }
      if (uvs && part.uvs) uvs.set(part.uvs, vo * 2);
      for (let k = 0; k < part.indices.length; k++) indices[io + k] = part.indices[k] + vo;
      vo += count;
      io += part.indices.length;
    }
    const mesh = this.mesh(bucket.name, bucket.material, positions, normals, uvs, indices);
    mesh.receiveShadows = bucket.receiveShadows;
    if (bucket.lod !== null) mesh.addLODLevel(bucket.lod, null);
  }

  private mesh(
    name: string,
    material: Material,
    positions: Float32Array,
    normals: Float32Array,
    uvs: Float32Array | null,
    indices: Uint32Array,
  ): Mesh {
    const mesh = new Mesh(name, this.scene);
    const data = new VertexData();
    data.positions = positions;
    data.normals = normals;
    if (uvs) data.uvs = uvs;
    data.indices = indices;
    data.applyToMesh(mesh, false);
    mesh.material = material;
    mesh.isPickable = false;
    mesh.freezeWorldMatrix();
    mesh.doNotSyncBoundingInfo = true;
    this.stats.triangles += indices.length / 3;
    this.meshes.push(mesh);
    return mesh;
  }

  /**
   * Forest floor beyond the terrain (and up the paddies' bunds), meeting the
   * authored ground exactly at its edge; the road continues as mud. Floor UVs
   * use the terrain's own world mapping, so the textures run on unbroken.
   */
  private buildGround(depth: number): void {
    const floor = this.materials.get("M_wet_forest_floor");
    const mud = this.materials.get("M_wet_mud");
    if (!floor || !mud) return;
    const steps = (lo: number, hi: number, fineLo: number, fineHi: number) => {
      const out: number[] = [];
      for (let v = lo; v < fineLo; v += 3) out.push(v);
      for (let v = fineLo; v < fineHi; v += 1) out.push(v);
      for (let v = fineHi; v < hi; v += 3) out.push(v);
      out.push(hi);
      return out;
    };
    const height = (x: number, z: number) => borderHeight(x, z, (a, b) => this.terrainAt(a, b));
    const xs = steps(TERRAIN.minX - depth, TERRAIN.maxX + depth, TERRAIN.minX - 6, TERRAIN.maxX + 6);
    const zs = steps(TERRAIN.minZ - depth, TERRAIN.maxZ + depth, TERRAIN.minZ - 6, TERRAIN.maxZ + 6);
    const drawn = (cx: number, cz: number) =>
      (outside(TERRAIN, cx, cz) > 0 || (inBund(cx, cz) && Math.abs(cz - ROAD_Z) > 2.7)) &&
      !onOuterRoad(cx, cz);
    this.grid("forest_border_ground", floor, xs, zs, height, drawn);
    const road: number[] = [];
    for (let z = ROAD_Z - 2.5; z <= ROAD_Z + 2.5 + 1e-6; z += 0.25) road.push(z);
    const outer = (cx: number) => Math.abs(cx) > TERRAIN.maxX;
    this.grid("forest_border_road", mud, xs, road, height, (cx) => outer(cx));
  }

  private grid(
    name: string,
    material: Material,
    xs: number[],
    zs: number[],
    height: (x: number, z: number) => number,
    drawn: (cx: number, cz: number) => boolean,
  ): void {
    const nx = xs.length;
    const positions: number[] = [];
    const uvs: number[] = [];
    for (const z of zs)
      for (const x of xs) {
        positions.push(x, height(x, z), z);
        uvs.push(-x / GROUND_TILE, z / GROUND_TILE + 1);
      }
    const indices: number[] = [];
    for (let j = 0; j + 1 < zs.length; j++)
      for (let i = 0; i + 1 < nx; i++) {
        if (!drawn((xs[i] + xs[i + 1]) / 2, (zs[j] + zs[j + 1]) / 2)) continue;
        const a = i + j * nx,
          b = i + (j + 1) * nx,
          c = i + 1 + (j + 1) * nx,
          d = i + 1 + j * nx;
        indices.push(a, c, b, a, d, c);
      }
    const normals: number[] = [];
    VertexData.ComputeNormals(positions, indices, normals);
    const mesh = this.mesh(
      name,
      material,
      Float32Array.from(positions),
      Float32Array.from(normals),
      Float32Array.from(uvs),
      Uint32Array.from(indices),
    );
    mesh.receiveShadows = this.groundShadows;
  }

  /** Far trees: two crossed painted cards each, merged in large cells. */
  private buildCards(cards: Card[]): void {
    const cell = 256;
    const texture = new DynamicTexture(
      "T_forest_far_cards",
      { width: cell * CARD_COLUMNS, height: cell * CARD_ROWS },
      this.scene,
      true,
      Texture.TRILINEAR_SAMPLINGMODE,
    );
    paintForestCards(texture.getContext() as unknown as CanvasRenderingContext2D, cell, seededRandom(6242040));
    texture.hasAlpha = true;
    texture.update();
    this.atlas = texture;
    const material = new PBRMaterial("M_forest_far_cards", this.scene);
    material.albedoTexture = texture;
    material.useAlphaFromAlbedoTexture = true;
    material.transparencyMode = PBRMaterial.PBRMATERIAL_ALPHATEST;
    material.alphaCutOff = 0.45;
    material.metallic = 0;
    material.roughness = 1;
    material.backFaceCulling = false;
    const leaf = this.materials.get("M_forest_leaf");
    if (leaf instanceof PBRMaterial) {
      material.environmentIntensity = leaf.environmentIntensity;
      material.directIntensity = leaf.directIntensity;
    }
    this.cardMaterial = material;

    const cells = new Map<string, Card[]>();
    for (const card of cards) {
      const key = `${Math.floor(card.x / 48)},${Math.floor(card.z / 48)}`;
      let list = cells.get(key);
      if (!list) cells.set(key, (list = []));
      list.push(card);
    }
    for (const [key, list] of cells) {
      const positions = new Float32Array(list.length * 8 * 3);
      const normals = new Float32Array(list.length * 8 * 3);
      const uvs = new Float32Array(list.length * 8 * 2);
      const indices = new Uint32Array(list.length * 12);
      list.forEach((card, k) => {
        const y = this.groundAt(card.x, card.z) - 0.25;
        const col = card.variant % CARD_COLUMNS;
        const row = Math.floor(card.variant / CARD_COLUMNS);
        const u0 = col / CARD_COLUMNS,
          u1 = (col + 1) / CARD_COLUMNS;
        const vTop = 1 - row / CARD_ROWS,
          vBottom = 1 - (row + 1) / CARD_ROWS;
        for (let q = 0; q < 2; q++) {
          const a = card.yaw + (q * Math.PI) / 2;
          const dx = Math.cos(a) * (card.width / 2),
            dz = Math.sin(a) * (card.width / 2);
          const v = k * 8 + q * 4;
          const corners = [
            [-1, 0, u0, vBottom],
            [1, 0, u1, vBottom],
            [1, 1, u1, vTop],
            [-1, 1, u0, vTop],
          ];
          corners.forEach(([side, up, u, vv], c) => {
            const o = (v + c) * 3;
            positions[o] = card.x + side * dx;
            positions[o + 1] = y + up * card.height;
            positions[o + 2] = card.z + side * dz;
            // Rounded normals: the card shades like a crown, not a board.
            const n = new Vector3(side * Math.cos(a) * 0.7, 0.35 + 0.65 * up, side * Math.sin(a) * 0.7).normalize();
            normals[o] = n.x;
            normals[o + 1] = n.y;
            normals[o + 2] = n.z;
            uvs[(v + c) * 2] = u;
            uvs[(v + c) * 2 + 1] = vv;
          });
          indices.set([v, v + 2, v + 1, v, v + 3, v + 2], k * 12 + q * 6);
        }
      });
      const mesh = this.mesh(`forest_border_far_${key}`, material, positions, normals, uvs, indices);
      mesh.receiveShadows = false;
    }
  }

  /** Standing water in hollows of the belt round the compound: the ground reads wet. */
  private buildPuddles(): void {
    const material = this.materials.get("M_puddle");
    if (!material) return;
    const random = seededRandom(6242050);
    const positions: number[] = [];
    const indices: number[] = [];
    let made = 0;
    for (let tries = 0; tries < 4000 && made < 18; tries++) {
      const x = (random() - 0.5) * 70;
      const z = -36 + random() * 42;
      const r = 0.45 + random() * 0.8;
      if (!inBelt(x, z) || !openGround(x, z, r) || !this.clear(x, z, r + 0.5)) continue;
      // Water finds the lowest ground: level with the hollow, the rest under the bank.
      let level = Infinity;
      for (let k = 0; k < 8; k++) {
        const a = (k / 8) * Math.PI * 2;
        level = Math.min(level, this.terrainAt(x + Math.cos(a) * r * 0.6, z + Math.sin(a) * r * 0.6));
      }
      level = Math.min(level, this.terrainAt(x, z)) + 0.035;
      const base = positions.length / 3;
      positions.push(x, level, z);
      const n = 16;
      for (let i = 0; i < n; i++) {
        const a = (i / n) * Math.PI * 2;
        const k = r * (0.7 + 0.35 * random());
        positions.push(x + Math.cos(a) * k, level, z + Math.sin(a) * k * (0.6 + 0.3 * random()));
        indices.push(base, base + 1 + ((i + 1) % n), base + 1 + i);
      }
      made++;
    }
    if (!made) return;
    const normals: number[] = [];
    VertexData.ComputeNormals(positions, indices, normals);
    const uvs = [];
    for (let i = 0; i < positions.length; i += 3) uvs.push(positions[i] / 2, positions[i + 2] / 2);
    this.mesh(
      "forest_border_puddles",
      material,
      Float32Array.from(positions),
      Float32Array.from(normals),
      Float32Array.from(uvs),
      Uint32Array.from(indices),
    ).receiveShadows = true;
  }

  /**
   * Trunks near the walk, and the walls: deep in the thicket, past the last
   * place the forest could plausibly be pushed through, and beyond the felled
   * trees across the road.
   */
  private buildColliders(trunks: Box[]): void {
    const anchor = new TransformNode("forest_border_body", this.scene);
    anchor.metadata = { surface: "leaves" };
    const body = new PhysicsBody(anchor, PhysicsMotionType.STATIC, false, this.scene);
    const shape = new PhysicsShapeContainer(this.scene);
    const box = (minX: number, maxX: number, minY: number, maxY: number, minZ: number, maxZ: number) => {
      const child = new PhysicsShapeBox(
        new Vector3((minX + maxX) / 2, (minY + maxY) / 2, (minZ + maxZ) / 2),
        Quaternion.Identity(),
        new Vector3(maxX - minX, maxY - minY, maxZ - minZ),
        this.scene,
      );
      child.material = { friction: 0.8 };
      shape.addChild(child);
      this.stats.colliders++;
    };
    for (const t of trunks) box(t.minX, t.maxX, -1, 3, t.minZ, t.maxZ);
    const wall = 1;
    const reach = 12;
    box(PLAY.maxX, PLAY.maxX + wall, -4, 9, PLAY.minZ - reach, PLAY.maxZ + reach);
    box(PLAY.minX - wall, PLAY.minX, -4, 9, PLAY.minZ - reach, PLAY.maxZ + reach);
    box(PLAY.minX - reach, PLAY.maxX + reach, -4, 9, PLAY.maxZ, PLAY.maxZ + wall);
    box(PLAY.minX - reach, PLAY.maxX + reach, -4, 9, PLAY.minZ - wall, PLAY.minZ);
    body.shape = shape;
    this.body = body;
    this.anchor = anchor;
  }
}
