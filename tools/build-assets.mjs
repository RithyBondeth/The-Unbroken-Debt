#!/usr/bin/env node
// Optimises every .glb in art-export/ into public/assets/ (same sub-folders).
// Steps follow the Technical Design Document, section 8. KTX2 needs KTX-Software (toktx).
// Usage: npm run assets            (all files)
//        npm run assets -- ep1     (only files under art-export/ep1/)

import { execFileSync } from "node:child_process";
import { mkdirSync, readdirSync, statSync } from "node:fs";
import { dirname, join, relative } from "node:path";

const SRC = "art-export";
const OUT = "public/assets";
const filter = process.argv[2] ?? "";

function findGlbs(dir) {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return findGlbs(path);
    return name.endsWith(".glb") ? [path] : [];
  });
}

// Hero assets and player items get 4K textures; everything else 2K (Art Bible, section 6).
function maxTextureSize(file) {
  return /(^|\/)(shared_|hero_)/.test(file) ? 4096 : 2048;
}

function gltf(...args) {
  execFileSync("npx", ["gltf-transform", ...args], { stdio: "inherit" });
}

try {
  execFileSync("toktx", ["--version"], { stdio: "ignore" });
} catch {
  console.error(
    "toktx not found. Install KTX-Software: https://github.com/KhronosGroup/KTX-Software",
  );
  process.exit(1);
}

const files = findGlbs(SRC).filter((f) => relative(SRC, f).startsWith(filter));
if (files.length === 0) {
  console.log(`No .glb files found in ${SRC}/${filter}`);
  process.exit(0);
}

for (const input of files) {
  const output = join(OUT, relative(SRC, input));
  const size = String(maxTextureSize(relative(SRC, input)));
  mkdirSync(dirname(output), { recursive: true });
  console.log(`\n▶ ${input} → ${output} (max ${size}px)`);

  gltf("dedup", input, output);
  gltf("prune", output, output);
  gltf("weld", output, output);
  gltf("resize", output, output, "--width", size, "--height", size);
  gltf("etc1s", output, output, "--slots", "{baseColorTexture,emissiveTexture}");
  gltf(
    "uastc",
    output,
    output,
    "--slots",
    "{normalTexture,occlusionTexture,metallicRoughnessTexture}",
  );
  gltf("meshopt", output, output);
}

console.log(`\nDone: ${files.length} file(s).`);
