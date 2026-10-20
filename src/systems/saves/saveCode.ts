import { SaveError, type SaveData } from "./SaveData";
import { migrate } from "./migrations";

/**
 * Save codes (Technical Design Document, section 13):
 * `"BS1." + base64url(deflate(JSON)) + "." + checksum`. A code carries a whole
 * save between devices and browsers and into the next episode. The checksum
 * makes it tamper-evident (a typo or an edit is caught), not secret.
 */
const PREFIX = "BS1";

let crcTable: Uint32Array | null = null;

/** CRC-32 (IEEE), as zip and PNG use it. */
export function crc32(bytes: Uint8Array): number {
  if (!crcTable) {
    crcTable = new Uint32Array(256);
    for (let n = 0; n < 256; n++) {
      let c = n;
      for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
      crcTable[n] = c >>> 0;
    }
  }
  let crc = 0xffffffff;
  for (const b of bytes) crc = crcTable[(crc ^ b) & 0xff] ^ (crc >>> 8);
  return (crc ^ 0xffffffff) >>> 0;
}

function toBase64Url(bytes: Uint8Array): string {
  let binary = "";
  for (const b of bytes) binary += String.fromCharCode(b);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function fromBase64Url(text: string): Uint8Array {
  const base64 = text.replace(/-/g, "+").replace(/_/g, "/");
  const binary = atob(base64 + "=".repeat((4 - (base64.length % 4)) % 4));
  return Uint8Array.from(binary, (c) => c.charCodeAt(0));
}

async function transform(
  bytes: Uint8Array,
  stream: CompressionStream | DecompressionStream,
): Promise<Uint8Array> {
  const out = new Blob([bytes as Uint8Array<ArrayBuffer>]).stream().pipeThrough(stream);
  return new Uint8Array(await new Response(out).arrayBuffer());
}

export async function encodeSaveCode(save: SaveData): Promise<string> {
  const json = new TextEncoder().encode(JSON.stringify(save));
  const payload = toBase64Url(await transform(json, new CompressionStream("deflate-raw")));
  const checksum = crc32(new TextEncoder().encode(payload)).toString(36);
  return `${PREFIX}.${payload}.${checksum}`;
}

/**
 * Reads a pasted code back into a checked, upgraded save. Spaces and line
 * breaks from copying are ignored.
 */
export async function decodeSaveCode(code: string): Promise<SaveData> {
  const parts = code.replace(/\s+/g, "").split(".");
  if (parts.length !== 3 || parts[0] !== PREFIX || !/^[\w-]+$/.test(parts[1])) {
    throw new SaveError("format", "This doesn't look like a save code");
  }
  const [, payload, checksum] = parts;
  if (crc32(new TextEncoder().encode(payload)).toString(36) !== checksum) {
    throw new SaveError("checksum", "This save code has been changed or mistyped");
  }
  let json: string;
  try {
    json = new TextDecoder().decode(
      await transform(fromBase64Url(payload), new DecompressionStream("deflate-raw")),
    );
  } catch {
    throw new SaveError("format", "This save code is damaged");
  }
  let raw: unknown;
  try {
    raw = JSON.parse(json);
  } catch {
    throw new SaveError("data", "This save code is damaged");
  }
  return migrate(raw);
}
