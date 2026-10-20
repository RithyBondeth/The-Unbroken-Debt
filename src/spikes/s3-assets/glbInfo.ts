/** What the spike reports about a .glb before Babylon loads it. */
export interface GlbInfo {
  extensionsUsed: string[];
  /** Distinct image MIME types, e.g. "image/ktx2". */
  imageTypes: string[];
  meshes: number;
  nodes: number;
}

const GLB_MAGIC = 0x46546c67; // "glTF"
const JSON_CHUNK = 0x4e4f534a; // "JSON"

/** Reads the JSON chunk of a binary glTF (glTF 2.0 specification, section 4.4). */
export function readGlbInfo(bytes: Uint8Array): GlbInfo {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  if (bytes.byteLength < 20 || view.getUint32(0, true) !== GLB_MAGIC) {
    throw new Error("Not a binary glTF (.glb) file");
  }
  const length = view.getUint32(12, true);
  if (view.getUint32(16, true) !== JSON_CHUNK) throw new Error("First GLB chunk is not JSON");
  const json = JSON.parse(new TextDecoder().decode(bytes.subarray(20, 20 + length))) as {
    extensionsUsed?: string[];
    images?: { mimeType?: string }[];
    meshes?: unknown[];
    nodes?: unknown[];
  };
  return {
    extensionsUsed: json.extensionsUsed ?? [],
    imageTypes: [...new Set((json.images ?? []).map((i) => i.mimeType ?? "uri"))],
    meshes: json.meshes?.length ?? 0,
    nodes: json.nodes?.length ?? 0,
  };
}

/**
 * Names the GPU block-compression family of a texture format (Babylon's
 * TEXTUREFORMAT_COMPRESSED_* constants, which use the WebGL enum values).
 */
export function textureFormatName(format: number | undefined): string {
  if (format === undefined) return "unknown";
  if ((format >= 33776 && format <= 33779) || (format >= 35916 && format <= 35919)) return "BC1-3";
  if (format >= 36492 && format <= 36495) return "BC7";
  if (format >= 37808 && format <= 37853) return "ASTC";
  if (format === 36196 || (format >= 37492 && format <= 37497)) return "ETC";
  return "uncompressed";
}
