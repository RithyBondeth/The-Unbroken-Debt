#!/usr/bin/env node
// Optimises every .glb in art-export/ into public/assets/ (same sub-folders).
// Steps follow the Technical Design Document, section 8. KTX2 needs KTX-Software 4.4+ (ktx).
// Usage: npm run assets            (all files)
//        npm run assets -- ep1     (only files under art-export/ep1/)

import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readdirSync, statSync } from "node:fs";
import { dirname, join, relative } from "node:path";

const SRC = "art-export";
const OUT = "public/assets";
const filter = process.argv[2] ?? "";

function findGlbs(dir) {
  if (!existsSync(dir)) return [];
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

// gltf-transform 4 calls KTX-Software's `ktx create` (the older `toktx` is not used).
try {
  execFileSync("ktx", ["--version"], { stdio: "ignore" });
} catch {
  console.error(
    "ktx not found. Install KTX-Software 4.4+: https://github.com/KhronosGroup/KTX-Software/releases",
  );
  process.exit(1);
}

const kb = (bytes) => `${(bytes / 1024).toFixed(0)} KB`;
let totalIn = 0;
let totalOut = 0;

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
  // Keep empty leaf nodes: spawn_ and patrol_ markers are empties (TDD section 7.1).
  gltf("prune", output, output, "--keep-leaves", "true");
  gltf("weld", output, output);
  gltf("resize", output, output, "--width", size, "--height", size);
  // Slot globs use @(a|b): the CLI's argument parser splits {a,b} into separate arguments.
  gltf("etc1s", output, output, "--slots", "@(baseColorTexture|emissiveTexture)");
  gltf(
    "uastc",
    output,
    output,
    "--slots",
    "@(normalTexture|occlusionTexture|metallicRoughnessTexture)",
  );
  gltf("meshopt", output, output);

  const before = statSync(input).size;
  const after = statSync(output).size;
  totalIn += before;
  totalOut += after;
  console.log(`✔ ${kb(before)} → ${kb(after)} (${((after / before) * 100).toFixed(0)}%)`);
}

console.log(`\nDone: ${files.length} file(s), ${kb(totalIn)} → ${kb(totalOut)}.`);
