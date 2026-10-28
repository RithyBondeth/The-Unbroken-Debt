export const HAND_GRIPS = [
  "relaxed",
  "lamp",
  "phone",
  "journal",
  "pinch",
  "reach",
  "drawing",
] as const;
export type HandGrip = (typeof HAND_GRIPS)[number];
export interface HandPose {
  positions: Float32Array;
  normals: Float32Array;
}
export interface HandAsset {
  indices: Uint32Array;
  uvs: Float32Array;
  poses: Record<HandGrip, HandPose>;
  vertexCount: number;
}
/** Versioned Blender export: anatomical geometry, UV seams and complete rigged poses. */
export function decodeHandAsset(buffer: ArrayBuffer): HandAsset {
  if (buffer.byteLength < 12 || new TextDecoder().decode(new Uint8Array(buffer, 0, 4)) !== "SORA")
    throw new Error("Invalid Sora hand mesh");
  const size = new DataView(buffer).getUint32(4, true);
  if (size > 16384 || size % 4 || 8 + size > buffer.byteLength)
    throw new Error("Invalid hand header");
  const header = JSON.parse(new TextDecoder().decode(new Uint8Array(buffer, 8, size))) as {
    version: number;
    vertexCount: number;
    indexCount: number;
    poses: string[];
  };
  const { vertexCount, indexCount } = header;
  if (
    header.version !== 1 ||
    !Number.isInteger(vertexCount) ||
    vertexCount < 1000 ||
    vertexCount > 100000 ||
    !Number.isInteger(indexCount) ||
    indexCount < 3 ||
    indexCount % 3 ||
    header.poses?.join(",") !== HAND_GRIPS.join(",")
  )
    throw new Error("Unsupported hand mesh");
  const expected =
    8 + size + indexCount * 4 + vertexCount * 8 + HAND_GRIPS.length * vertexCount * 24;
  if (buffer.byteLength !== expected) throw new Error("Truncated hand mesh");
  let at = 8 + size;
  const indices = new Uint32Array(buffer, at, indexCount);
  at += indexCount * 4;
  if (indices.some((i) => i >= vertexCount)) throw new Error("Invalid hand indices");
  const uvs = new Float32Array(buffer, at, vertexCount * 2);
  at += vertexCount * 8;
  const poses = {} as Record<HandGrip, HandPose>;
  for (const name of HAND_GRIPS) {
    const packed = new Float32Array(buffer, at, vertexCount * 6);
    at += packed.byteLength;
    const positions = new Float32Array(vertexCount * 3),
      normals = new Float32Array(vertexCount * 3);
    for (let i = 0; i < vertexCount; i++)
      for (let j = 0; j < 3; j++) {
        positions[i * 3 + j] = packed[i * 6 + j];
        normals[i * 3 + j] = packed[i * 6 + 3 + j];
      }
    poses[name] = { positions, normals };
  }
  return { indices, uvs, poses, vertexCount };
}
