import type { Scene } from "@babylonjs/core/scene";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import type { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { VertexData } from "@babylonjs/core/Meshes/mesh.vertexData";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { Matrix, Quaternion, Vector3 } from "@babylonjs/core/Maths/math.vector";
import { BoundingInfo } from "@babylonjs/core/Culling/boundingInfo";
import { seededRandom } from "@/audio/synth";
import { FoliageWind } from "@/render/FoliageWind";
import type { WindState } from "@/render/wind";
import { TAXI_FOREST_START, TAXI_GROUND_DROP, TAXI_PADDY_END, taxiRoadPoint } from "./taxiMotion";

/** Chunk span along the road (m): 1 thin-instanced draw call per chunk, culled by route distance. */
const CHUNK_LEN = 26;

/** Shop and poster-board exclusion zones (lateral sign, z, half-length along road) so grass never blocks storefronts. */
const CLEAR_ZONES: readonly [number, number, number][] = [
  [-1, 12.5, 6.2],
  [1, 17.5, 3.2],
  [1, 26.0, 6.2],
  [-1, 35.0, 3.2],
  [-1, 44.0, 6.5],
  [1, 54.0, 3.2],
  [1, 64.0, 6.0],
  [-1, 73.0, 3.2],
  [-1, 82.0, 6.4],
  [1, 91.0, 3.2],
  [1, 100.0, 6.4],
  [-1, 109.0, 3.2],
  [-1, 118.0, 6.2],
  [1, 127.0, 3.2],
  [1, 136.0, 6.0],
];

/** Deep wet Cambodian monsoon sword-grass palette matching ep1-refine's TallGrass / farmstead renders. */
const ROOT = [0.012, 0.018, 0.008];
const BLADE = [0.036, 0.062, 0.022];
const TIP = [0.062, 0.095, 0.036];
const STRAW = [0.14, 0.11, 0.052];

/** Broad-bladed tropical Cambodian sword-grass clump (smau), foot at origin, 0.85–1.35 m tall. */
function tropicalSwordClumpData(random: () => number, blades = 18, segments = 4): VertexData {
  const positions: number[] = [];
  const normals: number[] = [];
  const colors: number[] = [];
  const indices: number[] = [];
  for (let b = 0; b < blades; b++) {
    const yaw = (b / blades) * Math.PI * 2 + (random() - 0.5) * 0.35;
    const ox = Math.cos(yaw);
    const oz = Math.sin(yaw);
    const r0 = random() * 0.11;
    const height = 0.68 + 0.54 * random();
    const lean = 0.14 + 0.34 * random();
    const droop = 0.14 + 0.42 * random();
    const width = 0.022 + 0.022 * random();
    const twist = (random() - 0.5) * 0.85;
    const dry = random() < 0.14 ? 0.55 + 0.35 * random() : random() * 0.15;
    const n = new Vector3(ox * 0.52, 0.84, oz * 0.52).normalize();
    const base = positions.length / 3;
    for (let s = 0; s <= segments; s++) {
      const t = s / segments;
      const out = (lean * t + droop * t * t) * height;
      const y = height * (t - 0.36 * droop * t * t * t);
      const cx = ox * r0 + ox * out;
      const cz = oz * r0 + oz * out;
      const side = yaw + Math.PI / 2 + twist * t;
      const w = width * (1 - 0.88 * t * t);
      const sx = Math.cos(side) * w;
      const sz = Math.sin(side) * w;
      positions.push(cx - sx, y, cz - sz, cx + sx, y, cz + sz);
      normals.push(n.x, n.y, n.z, n.x, n.y, n.z);
      const green = t < 0.5 ? t * 2 : 1;
      const tip = Math.max(0, t - 0.5) * 2;
      const c = [0, 1, 2].map((i) => {
        const living = ROOT[i] + (BLADE[i] - ROOT[i]) * green + (TIP[i] - BLADE[i]) * tip;
        return living + (STRAW[i] - living) * dry * Math.min(1, t * 1.5);
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

interface ClumpPlacement {
  x: number;
  y: number;
  z: number;
  yaw: number;
  scaleX: number;
  scaleY: number;
  shade: number;
  dry: boolean;
}

function isShopClear(side: number, z: number): boolean {
  for (const [s, cz, half] of CLEAR_ZONES) {
    if (s === side && Math.abs(z - cz) < half) return true;
  }
  return false;
}

/**
 * Dense chest-high wind-swaying roadside tropical sword-grass banks lining both shoulders
 * of the muddy track (matching ep1-refine's farmstead TallGrass look at zero GLB cost).
 */
export class TaxiTallGrass {
  readonly chunks: { mesh: Mesh; minZ: number; maxZ: number; active: boolean }[] = [];
  readonly material: PBRMaterial;

  constructor(scene: Scene, route: TransformNode, wind: WindState, lowQuality: boolean) {
    const mat = new PBRMaterial("M_taxi_tall_grass", scene);
    mat.metallic = 0;
    mat.roughness = 0.42;
    mat.specularIntensity = 0.24;
    mat.directIntensity = 0.52;
    mat.environmentIntensity = 0.45;
    mat.backFaceCulling = false;
    mat.twoSidedLighting = true;
    mat.maxSimultaneousLights = 8;
    new FoliageWind(mat, wind, "grass", true);
    this.material = mat;

    const random = seededRandom(193309);
    const shape = tropicalSwordClumpData(seededRandom(193310), lowQuality ? 12 : 18, 4);
    const buckets = new Map<number, ClumpPlacement[]>();
    const stepZ = lowQuality ? 1.05 : 0.72;

    for (let z = -20; z < 508; z += stepZ) {
      const inForest = z >= TAXI_FOREST_START - 8;
      const inTransition = z >= TAXI_PADDY_END - 4 && z < TAXI_FOREST_START;
      const chunkIdx = Math.floor((z + 24) / CHUNK_LEN);
      let list = buckets.get(chunkIdx);
      if (!list) buckets.set(chunkIdx, (list = []));

      for (const side of [-1, 1]) {
        if (!inForest && isShopClear(side, z)) continue;
        // Dense thick banks in the jungle (2–3 rows deep per shoulder), lighter embankment verge grass along paddies!
        const rows = inForest ? (lowQuality ? 2 : 3) : inTransition ? 2 : 1;
        for (let r = 0; r < rows; r++) {
          if (!inForest && random() < 0.25) continue;
          const zz = z + (random() - 0.5) * stepZ;
          const latMin = inForest ? 3.22 + r * 1.15 : 3.35 + r * 0.75;
          const latMax = latMin + (inForest ? 1.25 : 0.95);
          const lat = side * (latMin + random() * (latMax - latMin));
          const pt = taxiRoadPoint(lat, zz);
          // Match embankment slope across paddies vs forest bank height
          const absLat = Math.abs(lat);
          let groundY: number;
          if (zz < TAXI_PADDY_END) {
            const t = Math.min(1, Math.max(0, (absLat - 3.3) / 2.3));
            groundY = -0.2 + (-0.98 + 0.2) * (0.5 - 0.5 * Math.cos(t * Math.PI));
          } else {
            const ditch = 0.17 * Math.exp(-(((absLat - 3.3) / 0.34) ** 2));
            groundY = -0.22 - ditch;
          }
          const scaleY = inForest ? 0.85 + random() * 0.62 + r * 0.14 : 0.55 + random() * 0.42;
          list.push({
            x: pt.x,
            y: groundY + TAXI_GROUND_DROP - 0.04,
            z: pt.z,
            yaw: random() * Math.PI * 2,
            scaleX: (0.85 + random() * 0.45) * (inForest ? 1.15 : 0.92),
            scaleY,
            shade: 0.72 + random() * 0.38,
            dry: random() < 0.12,
          });
        }
      }
    }

    const m = new Matrix();
    const q = new Quaternion();
    const s = new Vector3();
    const p = new Vector3();

    for (const [idx, list] of buckets) {
      if (!list.length) continue;
      const mesh = new Mesh(`taxi_tall_grass_${idx}`, scene);
      shape.applyToMesh(mesh, false);
      mesh.material = mat;
      mesh.parent = route;
      mesh.isPickable = false;
      mesh.receiveShadows = true;

      const lo = new Vector3(Infinity, Infinity, Infinity);
      const hi = new Vector3(-Infinity, -Infinity, -Infinity);
      const matrices = new Float32Array(list.length * 16);
      const tints = new Float32Array(list.length * 4);

      list.forEach((c, i) => {
        Quaternion.RotationYawPitchRollToRef(c.yaw, 0, 0, q);
        s.set(c.scaleX, c.scaleY, c.scaleX);
        p.set(c.x, c.y, c.z);
        Matrix.ComposeToRef(s, q, p, m);
        m.copyToArray(matrices, i * 16);
        tints.set(
          c.dry
            ? [1.28 * c.shade, 1.05 * c.shade, 0.72 * c.shade, 1]
            : [c.shade, c.shade, c.shade * 0.96, 1],
          i * 4,
        );
        lo.minimizeInPlace(new Vector3(c.x - 1.2, c.y - 0.1, c.z - 1.2));
        hi.maximizeInPlace(new Vector3(c.x + 1.2, c.y + 1.9, c.z + 1.2));
      });

      mesh.thinInstanceSetBuffer("matrix", matrices, 16, true);
      mesh.thinInstanceSetBuffer("color", tints, 4, true);
      mesh.setBoundingInfo(new BoundingInfo(lo, hi));
      mesh.doNotSyncBoundingInfo = true;
      mesh.setEnabled(false);

      const minZ = idx * CHUNK_LEN - 26;
      const maxZ = minZ + CHUNK_LEN + 4;
      this.chunks.push({ mesh, minZ, maxZ, active: false });
    }
  }

  update(distance: number): void {
    for (const chunk of this.chunks) {
      const active = chunk.maxZ > distance - 12 && chunk.minZ < distance + 68;
      if (active !== chunk.active) {
        chunk.mesh.setEnabled(active);
        chunk.active = active;
      }
    }
  }

  dispose(): void {
    for (const chunk of this.chunks) chunk.mesh.dispose();
    this.material.dispose();
  }
}
