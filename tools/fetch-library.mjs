#!/usr/bin/env node
// Downloads the library assets listed in art-source/library/polyhaven.json
// (CC0, from the Poly Haven API, and archive photographs from Wikimedia
// Commons) into art-source/library/ (git-ignored).
// Usage: npm run fetch-library        (skips files already downloaded)

import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";

const ROOT = "art-source/library";
const manifest = JSON.parse(readFileSync(join(ROOT, "polyhaven.json"), "utf8"));
const API = "https://api.polyhaven.com";
const headers = { "User-Agent": "BoonSop-asset-fetch" };

async function json(url) {
  const res = await fetch(url, { headers });
  if (!res.ok) throw new Error(`${res.status} ${url}`);
  return res.json();
}

async function download(url, path) {
  if (existsSync(path)) return 0;
  mkdirSync(dirname(path), { recursive: true });
  const res = await fetch(url, { headers });
  if (!res.ok) throw new Error(`${res.status} ${url}`);
  const bytes = new Uint8Array(await res.arrayBuffer());
  writeFileSync(path, bytes);
  return bytes.length;
}

let total = 0;
for (const [id, { resolution }] of Object.entries(manifest.models)) {
  const files = await json(`${API}/files/${id}`);
  const gltf = files.gltf[resolution].gltf;
  const dir = join(ROOT, "models", id);
  total += await download(gltf.url, join(dir, `${id}.gltf`));
  for (const [rel, file] of Object.entries(gltf.include ?? {}))
    total += await download(file.url, join(dir, rel));
  console.log(`model ${id}`);
}
for (const [id, { resolution, maps }] of Object.entries(manifest.materials)) {
  const files = await json(`${API}/files/${id}`);
  for (const [label, key] of Object.entries(maps)) {
    const file = files[key]?.[resolution]?.jpg;
    if (!file) throw new Error(`${id}: no ${key} at ${resolution}`);
    total += await download(file.url, join(ROOT, "materials", id, `${id}_${label}.jpg`));
  }
  console.log(`material ${id}`);
}
for (const [id, entry] of Object.entries(manifest.archive ?? {})) {
  if (id.startsWith("_")) continue;
  total += await download(entry.url, join(ROOT, "archive", entry.file));
  console.log(`photo ${id}`);
}
console.log(`Done: ${(total / 1e6).toFixed(1)} MB downloaded.`);
