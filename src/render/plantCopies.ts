import type { Material } from "@babylonjs/core/Materials/material";
import { Matrix, Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { VertexData } from "@babylonjs/core/Meshes/mesh.vertexData";
import type { Node } from "@babylonjs/core/node";
import type { Scene } from "@babylonjs/core/scene";
import { foliageKind } from "./FoliageWind";
import { plantPhase } from "./plantHeights";

/** One material's geometry from an authored plant, its foot at the origin. */
export interface PlantPart {
  material: Material;
  positions: Float32Array;
  normals: Float32Array;
  uvs: Float32Array | null;
  indices: Uint32Array;
}

/** An authored plant copied out of a loaded file, to be planted again elsewhere. */
export interface PlantTemplate {
  name: string;
  parts: PlantPart[];
  /** Height above its foot. */
  height: number;
}

/** A copy to plant: where, turned how far, how large, and how readily it bends. */
export interface PlantCopy {
  template: PlantTemplate;
  x: number;
  y: number;
  z: number;
  yaw: number;
  scale: number;
  flex: number;
}

/** The meshes with geometry at or under `node`. */
function meshesOf(node: Node): Mesh[] {
  const own = node instanceof Mesh && node.getTotalVertices() > 0 ? [node] : [];
  return [
    ...own,
    ...node
      .getChildMeshes(false)
      .filter((m): m is Mesh => m instanceof Mesh && m.getTotalVertices() > 0),
  ];
}

/** World-space copy of a mesh's geometry relative to `foot`, winding fixed for mirrored nodes. */
function bakePart(mesh: Mesh, foot: Vector3): PlantPart {
  const world = mesh.computeWorldMatrix(true);
  const normalMatrix = world.clone().invert().transpose();
  const positions = Float32Array.from(mesh.getVerticesData("position") ?? []);
  const normals = Float32Array.from(
    mesh.getVerticesData("normal") ?? new Float32Array(positions.length),
  );
  const uv = mesh.getVerticesData("uv");
  const indices = Uint32Array.from(mesh.getIndices() ?? []);
  const p = new Vector3();
  for (let i = 0; i < positions.length; i += 3) {
    Vector3.TransformCoordinatesFromFloatsToRef(
      positions[i],
      positions[i + 1],
      positions[i + 2],
      world,
      p,
    );
    positions[i] = p.x - foot.x;
    positions[i + 1] = p.y - foot.y;
    positions[i + 2] = p.z - foot.z;
    Vector3.TransformNormalFromFloatsToRef(
      normals[i],
      normals[i + 1],
      normals[i + 2],
      normalMatrix,
      p,
    );
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
  };
}

/**
 * Copies an authored plant (a node and everything under it) out of a loaded file before
 * batching merges it away. Its foot is the centre of its footprint at its lowest point,
 * so each copy stands on the ground it is planted on.
 */
export function capturePlant(node: Node): PlantTemplate | null {
  const meshes = meshesOf(node).filter((m) => m.material);
  if (meshes.length === 0) return null;
  const min = new Vector3(Infinity, Infinity, Infinity);
  const max = new Vector3(-Infinity, -Infinity, -Infinity);
  for (const mesh of meshes) {
    mesh.computeWorldMatrix(true);
    const box = mesh.getBoundingInfo().boundingBox;
    min.minimizeInPlace(box.minimumWorld);
    max.maximizeInPlace(box.maximumWorld);
  }
  const foot = new Vector3((min.x + max.x) / 2, min.y, (min.z + max.z) / 2);
  return { name: node.name, parts: meshes.map((m) => bakePart(m, foot)), height: max.y - min.y };
}

interface Bucket {
  material: Material;
  hasUv: boolean;
  sways: boolean;
  items: { part: PlantPart; m: Float32Array; r: Float32Array; reach: number; phase: number }[];
  verts: number;
  indices: number;
}

/**
 * Plants every copy and merges them per material per `cell` metres, so a whole forest
 * costs a draw call per material per cell. Copies of swaying materials carry their height
 * above the foot and their own phase in uv6 (FoliageWind), so each tree moves on its own.
 * Cells further than `hideBeyond` from the camera are not drawn.
 */
export function plantCopies(
  scene: Scene,
  name: string,
  copies: readonly PlantCopy[],
  cell: number,
  hideBeyond: number | null,
): Mesh[] {
  const buckets = new Map<string, Bucket>();
  for (const copy of copies) {
    const rotation = Matrix.RotationY(copy.yaw);
    const matrix = Matrix.Scaling(copy.scale, copy.scale, copy.scale)
      .multiply(rotation)
      .multiply(Matrix.Translation(copy.x, copy.y, copy.z));
    const key = `${Math.floor(copy.x / cell)},${Math.floor(copy.z / cell)}`;
    const phase = plantPhase(copy.x, copy.z);
    for (const part of copy.template.parts) {
      const id = `${part.material.uniqueId}|${key}|${part.uvs ? 1 : 0}`;
      let bucket = buckets.get(id);
      if (!bucket) {
        bucket = {
          material: part.material,
          hasUv: part.uvs !== null,
          sways: foliageKind(part.material.name) !== null,
          items: [],
          verts: 0,
          indices: 0,
        };
        buckets.set(id, bucket);
      }
      bucket.items.push({
        part,
        m: Float32Array.from(matrix.m),
        r: Float32Array.from(rotation.m),
        reach: copy.scale * copy.flex,
        phase,
      });
      bucket.verts += part.positions.length / 3;
      bucket.indices += part.indices.length;
    }
  }
  const meshes: Mesh[] = [];
  for (const [id, bucket] of buckets) {
    const positions = new Float32Array(bucket.verts * 3);
    const normals = new Float32Array(bucket.verts * 3);
    const uvs = bucket.hasUv ? new Float32Array(bucket.verts * 2) : null;
    const heights = bucket.sways ? new Float32Array(bucket.verts * 2) : null;
    const indices = new Uint32Array(bucket.indices);
    let vo = 0,
      io = 0;
    for (const { part, m, r, reach, phase } of bucket.items) {
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
        if (heights) {
          heights[(vo + i) * 2] = Math.max(0, y) * reach;
          heights[(vo + i) * 2 + 1] = phase;
        }
      }
      if (uvs && part.uvs) uvs.set(part.uvs, vo * 2);
      for (let k = 0; k < part.indices.length; k++) indices[io + k] = part.indices[k] + vo;
      vo += count;
      io += part.indices.length;
    }
    const mesh = new Mesh(`${name}_${id}`, scene);
    const data = new VertexData();
    data.positions = positions;
    data.normals = normals;
    if (uvs) data.uvs = uvs;
    data.indices = indices;
    data.applyToMesh(mesh, false);
    if (heights) mesh.setVerticesData("uv6", heights, false, 2);
    mesh.material = bucket.material;
    mesh.isPickable = false;
    mesh.receiveShadows = false;
    mesh.freezeWorldMatrix();
    mesh.doNotSyncBoundingInfo = true;
    if (hideBeyond !== null) mesh.addLODLevel(hideBeyond, null);
    meshes.push(mesh);
  }
  return meshes;
}
