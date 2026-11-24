import type { Scene } from "@babylonjs/core/scene";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { VertexData } from "@babylonjs/core/Meshes/mesh.vertexData";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { Matrix, Quaternion, Vector3 } from "@babylonjs/core/Maths/math.vector";
import { BoundingInfo } from "@babylonjs/core/Culling/boundingInfo";
import { seededRandom } from "@/audio/synth";
import { FoliageWind } from "@/render/FoliageWind";
import type { QualityPreset } from "@/render/qualityPresets";
import type { WindState } from "@/render/wind";
import { layoutGrass } from "../data/grass";
import type { Part } from "./ForestBorder";

/** Grass is batched in square cells this wide (m), each one draw call. */
const CELL = 12;
/** Within this of Sora (m, to a cell's middle) the scanned clump is drawn, past it the drawn blades. */
const NEAR = 12;

/** Linear colours up a blade: wet earth-dark at the root, green, a paler tip; straw when dry. */
const ROOT = [0.026, 0.028, 0.012];
const BLADE = [0.08, 0.105, 0.032];
const TIP = [0.13, 0.15, 0.052];
const STRAW = [0.27, 0.205, 0.095];

/**
 * One clump of blades, its foot at the origin and about 1 m tall: each blade
 * a tapering strip that leans out from the root and droops at the tip, a few
 * of them gone to straw. Heights stay in local y for FoliageWind.
 */
export function grassClumpData(random: () => number, blades = 16, segments = 4): VertexData {
  const positions: number[] = [];
  const normals: number[] = [];
  const colors: number[] = [];
  const indices: number[] = [];
  for (let b = 0; b < blades; b++) {
    const yaw = random() * Math.PI * 2;
    const ox = Math.cos(yaw),
      oz = Math.sin(yaw);
    const r0 = random() * 0.09;
    const height = 0.55 + 0.45 * random();
    const lean = 0.08 + 0.3 * random();
    const droop = 0.1 + 0.35 * random();
    const width = 0.015 + 0.016 * random();
    const twist = (random() - 0.5) * 0.9;
    const dry = random() < 0.18 ? 0.6 + 0.4 * random() : random() * 0.2;
    const n = new Vector3(ox * 0.55, 0.8, oz * 0.55).normalize();
    const base = positions.length / 3;
    for (let s = 0; s <= segments; s++) {
      const t = s / segments;
      const out = (lean * t + droop * t * t) * height;
      const y = height * (t - 0.35 * droop * t * t * t);
      const cx = ox * r0 + ox * out,
        cz = oz * r0 + oz * out;
      const side = yaw + Math.PI / 2 + twist * t;
      const w = width * (1 - 0.92 * t);
      const sx = Math.cos(side) * w,
        sz = Math.sin(side) * w;
      positions.push(cx - sx, y, cz - sz, cx + sx, y, cz + sz);
      normals.push(n.x, n.y, n.z, n.x, n.y, n.z);
      const green = t < 0.5 ? t * 2 : 1;
      const tip = Math.max(0, t - 0.5) * 2;
      const c = [0, 1, 2].map((i) => {
        const living = ROOT[i] + (BLADE[i] - ROOT[i]) * green + (TIP[i] - BLADE[i]) * tip;
        return living + (STRAW[i] - living) * dry * Math.min(1, t * 1.6);
      });
      colors.push(c[0], c[1], c[2], 1, c[0], c[1], c[2], 1);
    }
    for (let s = 0; s < segments; s++) {
      const a = base + s * 2;
      indices.push(a, a + 1, a + 3, a, a + 3, a + 2);
    }
  }
  const data = new VertexData();
  data.positions = positions;
  data.normals = normals;
  data.colors = colors;
  data.indices = indices;
  return data;
}

/** The scanned clump as thin-instance geometry: white vertex colours, so instance tints show. */
function scannedClumpData(part: Part): VertexData {
  const data = new VertexData();
  data.positions = part.positions;
  data.normals = part.normals;
  if (part.uvs) data.uvs = part.uvs;
  data.indices = part.indices;
  data.colors = new Float32Array((part.positions.length / 3) * 4).fill(1);
  return data;
}

/**
 * Tall grass along the path, the road bank and the bunds (data/grass): thin
 * instances of a few clumps, one draw call per cell, culled by distance. It
 * bends with the wind and parts round Sora as she wades through it.
 */
export class TallGrass {
  readonly meshes: Mesh[] = [];
  /** Each cell's drawn-blade stand-in, shown past NEAR. */
  private readonly farMeshes = new Map<Mesh, Mesh>();
  private farMaterial: PBRMaterial | null = null;
  readonly material: PBRMaterial;
  readonly count: number;
  private readonly range: number;
  private nextCull = 0;

  constructor(
    scene: Scene,
    preset: QualityPreset,
    wind: WindState,
    groundAt: (x: number, z: number) => number,
    clear: (x: number, z: number, radius: number) => boolean,
    /** The scanned grass clump (ForestBorder.grassClump); the drawn blades when absent. */
    scanned: Part | null = null,
  ) {
    const low = preset.name === "low";
    const clumps = layoutGrass({
      spacing: low ? 0.62 : preset.name === "medium" ? 0.52 : 0.44,
      clear,
    });
    this.range = low ? 24 : preset.name === "medium" ? 34 : 44;
    this.count = clumps.length;
    const material = new PBRMaterial("M_grass_tall", scene);
    material.metallic = 0;
    material.roughness = 0.52;
    material.backFaceCulling = false;
    material.twoSidedLighting = true;
    material.maxSimultaneousLights = 8;
    const carpet = scene.getMaterialByName("M_forest_grass");
    if (carpet instanceof PBRMaterial) {
      material.environmentIntensity = carpet.environmentIntensity;
      material.directIntensity = carpet.directIntensity;
    }
    const scan = scanned?.material instanceof PBRMaterial ? scanned.material : null;
    if (scan?.albedoTexture) {
      // The scanned blades: their own photograph, cut out by its alpha.
      material.albedoTexture = scan.albedoTexture;
      material.bumpTexture = scan.bumpTexture;
      material.useAlphaFromAlbedoTexture = true;
      material.transparencyMode = PBRMaterial.PBRMATERIAL_ALPHATEST;
      material.alphaCutOff = 0.5;
      material.albedoColor.copyFrom(scan.albedoColor);
      material.roughness = 0.62;
    }
    new FoliageWind(material, wind, "grass", true);
    this.material = material;

    const shape =
      scan && scanned ? scannedClumpData(scanned) : grassClumpData(seededRandom(6242071));
    // Past NEAR, the scanned clump (2,400 triangles) gives way to drawn blades (72): the
    // farm is grown over as the previews are (19,000 clumps on Medium, Nov 22, 2026), and
    // only what is round Sora's feet pays for the scan.
    const far = scan ? grassClumpData(seededRandom(6242072), 12, 3) : null;
    const farMaterial = far ? new PBRMaterial("M_grass_tall_far", scene) : null;
    if (farMaterial) {
      farMaterial.metallic = 0;
      farMaterial.roughness = 0.6;
      farMaterial.backFaceCulling = false;
      farMaterial.twoSidedLighting = true;
      farMaterial.maxSimultaneousLights = 8;
      farMaterial.environmentIntensity = material.environmentIntensity;
      farMaterial.directIntensity = material.directIntensity;
      new FoliageWind(farMaterial, wind, "grass", true);
      this.farMaterial = farMaterial;
    }
    const cells = new Map<string, typeof clumps>();
    for (const clump of clumps) {
      const key = `${Math.floor(clump.x / CELL)},${Math.floor(clump.z / CELL)}`;
      let list = cells.get(key);
      if (!list) cells.set(key, (list = []));
      list.push(clump);
    }
    const m = new Matrix(),
      q = new Quaternion(),
      s = new Vector3(),
      p = new Vector3();
    for (const [key, list] of cells) {
      const mesh = new Mesh(`grass_tall_${key}`, scene);
      shape.applyToMesh(mesh, false);
      mesh.material = material;
      mesh.isPickable = false;
      mesh.receiveShadows = true;
      // The cell's own box (the clumps' feet and a metre and a half over them): the
      // thin instances' bounds were not kept, and every cell sat at the world's origin
      // for the frustum and the distance cull.
      const lo = new Vector3(Infinity, Infinity, Infinity),
        hi = new Vector3(-Infinity, -Infinity, -Infinity);
      for (const clump of list) {
        const y = groundAt(clump.x, clump.z);
        lo.minimizeInPlace(new Vector3(clump.x - 1, y - 0.1, clump.z - 1));
        hi.maximizeInPlace(new Vector3(clump.x + 1, y + 1.6, clump.z + 1));
      }
      const bounds = new BoundingInfo(lo, hi);
      const matrices = new Float32Array(list.length * 16);
      const tints = new Float32Array(list.length * 4);
      const farTints = new Float32Array(list.length * 4);
      list.forEach((clump, i) => {
        Quaternion.RotationYawPitchRollToRef(clump.yaw, 0, 0, q);
        s.set(clump.scale * (0.9 + 0.2 * ((i * 0.618) % 1)), clump.scale, clump.scale);
        p.set(clump.x, groundAt(clump.x, clump.z) - 0.02, clump.z);
        Matrix.ComposeToRef(s, q, p, m);
        m.copyToArray(matrices, i * 16);
        // Dry clumps bleach towards straw; green ones vary a little in shade.
        const dry = clump.variant === 2;
        const shade = clump.variant === 1 ? 0.85 : 1;
        if (scan) tints.set(dry ? [1.35, 1.12, 0.72, 1] : [shade, shade, shade * 0.96, 1], i * 4);
        else tints.set(dry ? [2.1, 1.55, 1.45, 1] : [shade, shade, shade * 0.95, 1], i * 4);
        farTints.set(dry ? [2.1, 1.55, 1.45, 1] : [shade, shade, shade * 0.95, 1], i * 4);
      });
      mesh.thinInstanceSetBuffer("matrix", matrices, 16, true);
      mesh.thinInstanceSetBuffer("color", tints, 4, true);
      mesh.setBoundingInfo(bounds);
      mesh.doNotSyncBoundingInfo = true;
      mesh.freezeWorldMatrix();
      this.meshes.push(mesh);
      if (far && farMaterial) {
        const lod = new Mesh(`grass_tall_far_${key}`, scene);
        far.applyToMesh(lod, false);
        lod.material = farMaterial;
        lod.isPickable = false;
        lod.receiveShadows = true;
        lod.thinInstanceSetBuffer("matrix", matrices, 16, true);
        lod.thinInstanceSetBuffer("color", farTints, 4, true);
        lod.setBoundingInfo(new BoundingInfo(lo, hi));
        lod.doNotSyncBoundingInfo = true;
        lod.freezeWorldMatrix();
        lod.setEnabled(false);
        this.farMeshes.set(mesh, lod);
      }
    }
    console.info(`[TallGrass] ${clumps.length} clumps in ${this.meshes.length} cells`);
  }

  /** Cells beyond the preset's range are not drawn (checked a few times a second). */
  update(dt: number, eye: Vector3): void {
    this.nextCull -= dt;
    if (this.nextCull > 0) return;
    this.nextCull = 0.3;
    for (const mesh of this.meshes) {
      const c = mesh.getBoundingInfo().boundingSphere.centerWorld;
      const d = Math.hypot(c.x - eye.x, c.z - eye.z);
      const lod = this.farMeshes.get(mesh);
      const shown = d < this.range + CELL * 0.7;
      const scanned = shown && (!lod || d < NEAR + CELL * 0.7);
      if (scanned !== mesh.isEnabled()) mesh.setEnabled(scanned);
      const blades = shown && !scanned;
      if (lod && blades !== lod.isEnabled()) lod.setEnabled(blades);
    }
  }

  dispose(): void {
    for (const mesh of this.meshes) mesh.dispose();
    for (const lod of this.farMeshes.values()) lod.dispose();
    this.material.dispose();
    this.farMaterial?.dispose();
  }
}
