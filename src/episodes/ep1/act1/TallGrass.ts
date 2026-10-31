import type { Scene } from "@babylonjs/core/scene";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { VertexData } from "@babylonjs/core/Meshes/mesh.vertexData";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { Matrix, Quaternion, Vector3 } from "@babylonjs/core/Maths/math.vector";
import { seededRandom } from "../../../audio/synth";
import { FoliageWind } from "../../../render/FoliageWind";
import type { QualityPreset } from "../../../render/QualityPresets";
import type { WindState } from "../../../render/wind";
import { layoutGrass } from "../data/grass";

/** Grass is batched in square cells this wide (m), each one draw call. */
const CELL = 12;

/** Linear colours up a blade: dark at the root, dead olive-brown, a bleached tip; straw when dry. */
const ROOT = [0.03, 0.026, 0.016];
const BLADE = [0.11, 0.095, 0.055];
const TIP = [0.2, 0.17, 0.11];
const STRAW = [0.3, 0.24, 0.14];

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

/**
 * Tall grass along the path, the road bank and the bunds (data/grass): thin
 * instances of a few clumps, one draw call per cell, culled by distance. It
 * bends with the wind and parts round Sora as she wades through it.
 */
export class TallGrass {
  readonly meshes: Mesh[] = [];
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
    new FoliageWind(material, wind, "grass", true);
    this.material = material;

    const shape = grassClumpData(seededRandom(6242071));
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
      const matrices = new Float32Array(list.length * 16);
      const tints = new Float32Array(list.length * 4);
      list.forEach((clump, i) => {
        Quaternion.RotationYawPitchRollToRef(clump.yaw, 0, 0, q);
        s.set(clump.scale * (0.9 + 0.2 * ((i * 0.618) % 1)), clump.scale, clump.scale);
        p.set(clump.x, groundAt(clump.x, clump.z) - 0.02, clump.z);
        Matrix.ComposeToRef(s, q, p, m);
        m.copyToArray(matrices, i * 16);
        // Dry clumps bleach towards straw; green ones vary a little in shade.
        const dry = clump.variant === 2;
        const shade = clump.variant === 1 ? 0.85 : 1;
        tints.set(dry ? [2.1, 1.55, 1.45, 1] : [shade, shade, shade * 0.95, 1], i * 4);
      });
      mesh.thinInstanceSetBuffer("matrix", matrices, 16, true);
      mesh.thinInstanceSetBuffer("color", tints, 4, true);
      mesh.thinInstanceRefreshBoundingInfo();
      mesh.freezeWorldMatrix();
      this.meshes.push(mesh);
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
      const near = Math.hypot(c.x - eye.x, c.z - eye.z) < this.range + CELL * 0.7;
      if (near !== mesh.isEnabled()) mesh.setEnabled(near);
    }
  }

  dispose(): void {
    for (const mesh of this.meshes) mesh.dispose();
    this.material.dispose();
  }
}
