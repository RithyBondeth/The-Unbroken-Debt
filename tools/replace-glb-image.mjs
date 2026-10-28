// Replace one embedded image without re-exporting geometry or recompressing other textures.
// node tools/replace-glb-image.mjs file.glb image-name replacement.png
import { readFileSync, writeFileSync, renameSync } from "node:fs";
const [file, name, replacement] = process.argv.slice(2);
if (!file || !name || !replacement) throw new Error("Expected glb, image name, replacement PNG");
const data = readFileSync(file);
if (data.readUInt32LE(0) !== 0x46546c67 || data.readUInt32LE(4) !== 2)
  throw new Error("Expected GLB 2");
const jsonLength = data.readUInt32LE(12);
const model = JSON.parse(data.subarray(20, 20 + jsonLength).toString());
const binHeader = 20 + jsonLength;
if (data.readUInt32LE(binHeader + 4) !== 0x004e4942) throw new Error("Expected BIN chunk");
const bin = data.subarray(binHeader + 8, binHeader + 8 + data.readUInt32LE(binHeader));
const index = model.images.findIndex((image) => image.name === name);
if (index < 0) throw new Error(`Missing image ${name}`);
const image = model.images[index],
  view = model.bufferViews[image.bufferView];
if ((view.buffer ?? 0) !== 0) throw new Error("Expected image in first buffer");
const start = view.byteOffset ?? 0,
  oldLength = view.byteLength;
const oldPadded = Math.ceil(oldLength / 4) * 4;
for (const other of model.bufferViews) {
  if (other === view || (other.buffer ?? 0) !== 0) continue;
  const offset = other.byteOffset ?? 0;
  if (offset < start + oldLength && offset + other.byteLength > start)
    throw new Error("Overlapping image view");
}
const png = readFileSync(replacement),
  padded = Buffer.alloc(Math.ceil(png.length / 4) * 4);
png.copy(padded);
const delta = padded.length - oldPadded;
const bytes = Buffer.concat([bin.subarray(0, start), padded, bin.subarray(start + oldPadded)]);
view.byteLength = png.length;
for (const other of model.bufferViews) {
  if (other !== view && (other.buffer ?? 0) === 0 && (other.byteOffset ?? 0) >= start + oldPadded)
    other.byteOffset += delta;
  // Meshopt compressed ranges have separate offsets into the same BIN chunk.
  const compressed = other.extensions?.EXT_meshopt_compression;
  if (compressed?.buffer === 0 && compressed.byteOffset >= start + oldPadded)
    compressed.byteOffset += delta;
}
image.mimeType = "image/png";
for (const texture of model.textures ?? []) {
  if (texture.extensions?.KHR_texture_basisu?.source === index) {
    delete texture.extensions.KHR_texture_basisu;
    if (!Object.keys(texture.extensions).length) delete texture.extensions;
    texture.source = index;
  }
}
model.buffers[0].byteLength = bytes.length;
const json = Buffer.from(JSON.stringify(model));
const paddedJson = Buffer.alloc(Math.ceil(json.length / 4) * 4, 0x20);
json.copy(paddedJson);
const header = Buffer.alloc(20);
header.writeUInt32LE(0x46546c67, 0);
header.writeUInt32LE(2, 4);
header.writeUInt32LE(28 + paddedJson.length + bytes.length, 8);
header.writeUInt32LE(paddedJson.length, 12);
header.writeUInt32LE(0x4e4f534a, 16);
const binaryHeader = Buffer.alloc(8);
binaryHeader.writeUInt32LE(bytes.length, 0);
binaryHeader.writeUInt32LE(0x004e4942, 4);
writeFileSync(`${file}.tmp`, Buffer.concat([header, paddedJson, binaryHeader, bytes]));
renameSync(`${file}.tmp`, file);
console.log(`Replaced ${name}; geometry and other image payloads retained.`);
